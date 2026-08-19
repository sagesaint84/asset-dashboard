from __future__ import annotations

import csv
import io
import json
import re
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT_DIR / "data" / "portfolio.json"
_LOCK = threading.Lock()

EMPTY_PORTFOLIO: dict[str, Any] = {
    "settings": {"fx_rates": {"KRW": 1.0}, "fx_info": {}, "daily_snapshot": {}, "cash_balances": {}},
    "accounts": [],
    "holdings": [],
    "updated_at": None,
}

FIELD_ALIASES = {
    "broker": ("증권사", "broker", "brokerage"),
    "account": ("계좌명", "계좌번호", "계좌", "account", "account_name"),
    "code": ("종목코드", "종목번호", "단축코드", "code", "symbol", "ticker"),
    "name": ("종목명", "종목", "name", "security_name"),
    "quantity": ("보유수량", "수량", "잔고수량", "quantity", "shares"),
    "avg_price": ("평균매입가", "매입단가", "매입평균가", "buy_price", "avg_price"),
    "current_price": ("현재가", "평가단가", "price", "current_price", "last_price"),
    "currency": ("통화", "currency", "화폐"),
    "market": ("거래소", "시장", "market", "exchange"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps(EMPTY_PORTFOLIO, ensure_ascii=False, indent=2), encoding="utf-8")


def read_portfolio() -> dict[str, Any]:
    with _LOCK:
        _ensure_data_file()
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = deepcopy(EMPTY_PORTFOLIO)
        data.setdefault("settings", deepcopy(EMPTY_PORTFOLIO["settings"]))
        data["settings"].setdefault("fx_rates", {"KRW": 1.0})
        data["settings"]["fx_rates"].setdefault("KRW", 1.0)
        data["settings"].setdefault("fx_info", {})
        data["settings"].setdefault("daily_snapshot", {})
        data["settings"].setdefault("cash_balances", {})
        data.setdefault("accounts", [])
        data.setdefault("holdings", [])
        data.setdefault("updated_at", None)
        previous_date = str(data.get("updated_at") or "")[:10]
        today = datetime.now().astimezone().date().isoformat()
        if previous_date and previous_date != today and data["settings"].get("daily_snapshot", {}).get("date") != previous_date:
            previous_value = 0.0
            for holding in data["holdings"]:
                currency = normalize_currency(holding.get("currency"))
                rate = to_number(data["settings"]["fx_rates"].get(currency), 1.0 if currency == "KRW" else 0.0)
                previous_value += to_number(holding.get("quantity")) * to_number(holding.get("current_price")) * rate
            data["settings"]["daily_snapshot"] = {"date": previous_date, "value_krw": previous_value}
        return data


def write_portfolio(data: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        _ensure_data_file()
        data["updated_at"] = now_iso()
        temp_file = DATA_FILE.with_suffix(".json.tmp")
        temp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_file.replace(DATA_FILE)
        return data


def to_number(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
    try:
        return float(cleaned) if cleaned not in {"", "-", "."} else default
    except ValueError:
        return default


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_currency(value: Any) -> str:
    value = clean_text(value).upper()
    return {"원": "KRW", "₩": "KRW", "달러": "USD", "미국달러": "USD", "$": "USD", "US$": "USD"}.get(value, value or "KRW")


def normalize_market(value: Any, code: str, currency: str) -> str:
    value = clean_text(value).upper().replace(" ", "")
    aliases = {"코스피": "KRX", "코스닥": "KRX", "국내": "KRX", "NASDAQ": "NAS", "나스닥": "NAS", "NYSE": "NYS", "뉴욕": "NYS", "AMEX": "AMX", "아멕스": "AMX"}
    if value in aliases:
        return aliases[value]
    if value:
        return value
    return "KRX" if currency == "KRW" and code.isdigit() else ""


def get_or_add_account(data: dict[str, Any], broker: str, account_name: str, source: str = "import") -> str:
    broker = broker or "기타 증권사"
    account_name = account_name or f"{broker} 계좌"
    for account in data["accounts"]:
        if account["broker"] == broker and account["name"] == account_name:
            return account["id"]
    account_id = str(uuid.uuid4())
    data["accounts"].append({"id": account_id, "broker": broker, "name": account_name, "source": source})
    return account_id


def normalize_holding(raw: dict[str, Any], account_id: str, broker: str, account_name: str, source: str = "manual") -> dict[str, Any]:
    code = clean_text(raw.get("code")).upper()
    name = clean_text(raw.get("name")) or code
    currency = normalize_currency(raw.get("currency"))
    return {
        "id": clean_text(raw.get("id")) or str(uuid.uuid4()),
        "account_id": account_id,
        "broker": broker,
        "account_name": account_name,
        "code": code,
        "name": name,
        "quantity": to_number(raw.get("quantity")),
        "avg_price": to_number(raw.get("avg_price")),
        "current_price": to_number(raw.get("current_price")),
        "currency": currency,
        "market": normalize_market(raw.get("market"), code, currency),
        "source": source,
        "price_updated_at": raw.get("price_updated_at"),
    }


def upsert_holdings(data: dict[str, Any], holdings: Iterable[dict[str, Any]], replace_source: str | None = None) -> int:
    if replace_source:
        data["holdings"] = [h for h in data["holdings"] if h.get("source") != replace_source]
    index = {(h["account_id"], h["code"]): position for position, h in enumerate(data["holdings"])}
    count = 0
    for holding in holdings:
        key = (holding["account_id"], holding["code"])
        if not holding["code"] or holding["quantity"] <= 0:
            continue
        if key in index:
            holding["id"] = data["holdings"][index[key]]["id"]
            data["holdings"][index[key]] = holding
        else:
            index[key] = len(data["holdings"])
            data["holdings"].append(holding)
        count += 1
    return count


def get_dashboard() -> dict[str, Any]:
    data = read_portfolio()
    fx_rates = {key.upper(): to_number(value, 1.0) for key, value in data["settings"]["fx_rates"].items()}
    fx_rates.setdefault("KRW", 1.0)
    usd_rate = fx_rates.get("USD", 1.0)

    cash_balances = data["settings"].get("cash_balances", {})
    toss_cash = data["settings"].get("toss_cash", {})

    accounts: dict[str, dict[str, Any]] = {}
    for a in data["accounts"]:
        acc_id = a["id"]
        acc_cash = cash_balances.get(acc_id)
        if not acc_cash and a.get("broker") == "토스증권" and toss_cash:
            for seq_val in toss_cash.values():
                if isinstance(seq_val, dict):
                    acc_cash = seq_val
                    break
        acc_cash = acc_cash or {}
        cash_krw = to_number(acc_cash.get("KRW"))
        cash_usd = to_number(acc_cash.get("USD"))
        cash_total_krw = cash_krw + (cash_usd * usd_rate)

        accounts[acc_id] = {
            **a,
            "stock_value_krw": 0.0,
            "cash_krw": cash_krw,
            "cash_usd": cash_usd,
            "cash_total_krw": cash_total_krw,
            "market_value_krw": cash_total_krw,
            "cost_value_krw": 0.0,
            "profit_krw": 0.0,
            "holding_count": 0,
        }

    enriched: list[dict[str, Any]] = []
    total_stock_value = total_stock_cost = 0.0
    for holding in data["holdings"]:
        item = deepcopy(holding)
        rate = fx_rates.get(item["currency"], 1.0 if item["currency"] == "KRW" else 0.0)
        item["fx_rate"] = rate
        item["market_value_krw"] = item["quantity"] * item["current_price"] * rate
        item["cost_value_krw"] = item["quantity"] * item["avg_price"] * rate
        item["profit_krw"] = item["market_value_krw"] - item["cost_value_krw"]
        item["return_rate"] = item["profit_krw"] / item["cost_value_krw"] * 100 if item["cost_value_krw"] else 0
        enriched.append(item)
        total_stock_value += item["market_value_krw"]
        total_stock_cost += item["cost_value_krw"]
        account = accounts.get(item["account_id"])
        if account:
            account["stock_value_krw"] += item["market_value_krw"]
            account["market_value_krw"] += item["market_value_krw"]
            account["cost_value_krw"] += item["cost_value_krw"]
            account["profit_krw"] += item["profit_krw"]
            account["holding_count"] += 1

    enriched.sort(key=lambda h: h["market_value_krw"], reverse=True)

    total_cash_krw = sum(a["cash_krw"] for a in accounts.values())
    total_cash_usd = sum(a["cash_usd"] for a in accounts.values())
    total_cash_krw_combined = total_cash_krw + (total_cash_usd * usd_rate)

    total_value = total_stock_value + total_cash_krw_combined
    profit = total_stock_value - total_stock_cost

    account_list = sorted(accounts.values(), key=lambda a: a["market_value_krw"], reverse=True)
    for account in account_list:
        account["weight"] = account["market_value_krw"] / total_value * 100 if total_value else 0

    daily_snapshot = data["settings"].get("daily_snapshot", {})
    previous_value = to_number(daily_snapshot.get("value_krw"))
    day_change = total_value - previous_value if previous_value else None

    currency_summary: dict[str, dict[str, float]] = {
        "KRW": {
            "market_value": total_cash_krw,
            "market_value_krw": total_cash_krw,
            "stock_value_krw": 0.0,
            "cost_value_krw": 0.0,
            "cash": total_cash_krw,
        },
        "USD": {
            "market_value": total_cash_usd,
            "market_value_krw": total_cash_usd * usd_rate,
            "stock_value": 0.0,
            "stock_value_krw": 0.0,
            "cost_value_krw": 0.0,
            "cash": total_cash_usd,
        },
    }

    classifications: dict[str, dict[str, Any]] = {}
    etf_prefixes = ("KODEX", "TIGER", "ACE", "SOL", "PLUS", "RISE", "HANARO", "KOSEF", "ARIRANG", "KOACT", "WON")
    for item in enriched:
        currency = item["currency"]
        bucket = currency_summary.setdefault(currency, {
            "market_value": 0.0, "market_value_krw": 0.0, "cost_value_krw": 0.0, "stock_value_krw": 0.0, "stock_value": 0.0, "cash": 0.0,
        })
        bucket["market_value"] += item["quantity"] * item["current_price"]
        bucket["market_value_krw"] += item["market_value_krw"]
        bucket["stock_value_krw"] = bucket.get("stock_value_krw", 0.0) + item["market_value_krw"]
        if currency == "USD":
            bucket["stock_value"] = bucket.get("stock_value", 0.0) + (item["quantity"] * item["current_price"])
        bucket["cost_value_krw"] += item["cost_value_krw"]

        name = item["name"].strip()
        name_upper = name.upper()
        market = str(item.get("market", ""))
        if item["currency"] == "KRW" and any(name_upper.startswith(p) for p in etf_prefixes):
            group = "국내 ETF"
        elif item["currency"] == "KRW":
            group = "국내 주식"
        elif market.startswith("NH_") and market != "NH_US":
            group = "기타 해외자산"
        else:
            group = "미국 주식·ETF"
        classification = classifications.setdefault(group, {"name": group, "market_value_krw": 0.0, "cost_value_krw": 0.0, "holding_count": 0})
        classification["market_value_krw"] += item["market_value_krw"]
        classification["cost_value_krw"] += item["cost_value_krw"]
        classification["holding_count"] += 1

    if total_cash_krw_combined > 0:
        classifications["현금·예수금"] = {
            "name": "현금·예수금",
            "market_value_krw": total_cash_krw_combined,
            "cost_value_krw": total_cash_krw_combined,
            "profit_krw": 0.0,
            "return_rate": 0.0,
            "holding_count": 0,
            "weight": total_cash_krw_combined / total_value * 100 if total_value else 0.0,
        }

    classification_list = []
    for classification in classifications.values():
        classification.setdefault("profit_krw", classification["market_value_krw"] - classification["cost_value_krw"])
        classification.setdefault("return_rate", classification["profit_krw"] / classification["cost_value_krw"] * 100 if classification["cost_value_krw"] else 0.0)
        classification["weight"] = classification["market_value_krw"] / total_value * 100 if total_value else 0.0
        classification_list.append(classification)
    classification_list.sort(key=lambda item: item["market_value_krw"], reverse=True)

    return {
        "summary": {
            "total_value_krw": total_value,
            "total_stock_value_krw": total_stock_value,
            "total_cash_krw": total_cash_krw_combined,
            "cash_krw": total_cash_krw,
            "cash_usd": total_cash_usd,
            "total_cost_krw": total_stock_cost,
            "profit_krw": profit,
            "return_rate": profit / total_stock_cost * 100 if total_stock_cost else 0,
            "holding_count": len(enriched),
            "account_count": len(account_list),
        },
        "day_change": {
            "date": daily_snapshot.get("date"),
            "value_krw": previous_value,
            "change_krw": day_change,
            "change_rate": day_change / previous_value * 100 if day_change is not None and previous_value else None,
        },
        "accounts": account_list,
        "holdings": enriched,
        "fx_rates": fx_rates,
        "fx_info": data["settings"].get("fx_info", {}),
        "currency_summary": currency_summary,
        "classifications": classification_list,
        "updated_at": data["updated_at"],
    }


def find_column(row: dict[str, Any], field: str) -> Any:
    normalized = {clean_text(key).lower(): value for key, value in row.items() if key is not None}
    for alias in FIELD_ALIASES[field]:
        if alias.lower() in normalized:
            return normalized[alias.lower()]
    return None


def rows_from_upload(filename: str, contents: bytes) -> list[dict[str, Any]]:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        workbook = load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
        sheet = workbook.active
        values = list(sheet.iter_rows(values_only=True))
        if not values:
            return []
        headers = [clean_text(value) for value in values[0]]
        return [dict(zip(headers, row)) for row in values[1:] if any(value is not None for value in row)]
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return list(csv.DictReader(io.StringIO(contents.decode(encoding))))
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 인코딩을 읽을 수 없습니다. UTF-8 또는 CP949 파일을 사용하세요.")


def import_rows(filename: str, contents: bytes, default_broker: str = "기타 증권사") -> tuple[int, list[str]]:
    rows = rows_from_upload(filename, contents)
    data = read_portfolio()
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    for number, row in enumerate(rows, start=2):
        code = clean_text(find_column(row, "code"))
        quantity = to_number(find_column(row, "quantity"))
        if not code or quantity <= 0:
            errors.append(f"{number}행: 종목코드 또는 보유수량이 없어 건너뛰었습니다.")
            continue
        broker = clean_text(find_column(row, "broker")) or default_broker
        account_name = clean_text(find_column(row, "account")) or f"{broker} 가져온 계좌"
        account_id = get_or_add_account(data, broker, account_name, "import")
        normalized.append(normalize_holding({
            "code": code, "name": find_column(row, "name"), "quantity": quantity,
            "avg_price": find_column(row, "avg_price"), "current_price": find_column(row, "current_price"),
            "currency": find_column(row, "currency"), "market": find_column(row, "market"),
        }, account_id, broker, account_name, "import"))
    count = upsert_holdings(data, normalized)
    write_portfolio(data)
    return count, errors[:10]


def seed_demo() -> None:
    data = deepcopy(EMPTY_PORTFOLIO)
    data["settings"]["fx_rates"]["USD"] = 1350.0
    data["settings"]["fx_info"] = {"source": "예시 데이터", "valid_until": None}
    kb = get_or_add_account(data, "KB증권", "KB 국내 주식", "demo")
    toss = get_or_add_account(data, "토스증권", "토스 해외 주식", "demo")
    namoo = get_or_add_account(data, "NH투자증권(나무)", "나무 국내 주식", "demo")
    data["settings"]["cash_balances"] = {
        toss: {"KRW": 5000000.0, "USD": 2500.0},
        namoo: {"KRW": 1200000.0, "USD": 0.0},
    }
    examples = [
        {"code": "005930", "name": "삼성전자", "quantity": 12, "avg_price": 70200, "current_price": 72400, "currency": "KRW", "market": "KRX", "account_id": kb, "broker": "KB증권", "account_name": "KB 국내 주식"},
        {"code": "000660", "name": "SK하이닉스", "quantity": 4, "avg_price": 178000, "current_price": 198700, "currency": "KRW", "market": "KRX", "account_id": namoo, "broker": "NH투자증권(나무)", "account_name": "나무 국내 주식"},
        {"code": "AAPL", "name": "Apple", "quantity": 6, "avg_price": 195, "current_price": 214, "currency": "USD", "market": "NAS", "account_id": toss, "broker": "토스증권", "account_name": "토스 해외 주식"},
        {"code": "NVDA", "name": "NVIDIA", "quantity": 5, "avg_price": 118, "current_price": 128, "currency": "USD", "market": "NAS", "account_id": toss, "broker": "토스증권", "account_name": "토스 해외 주식"},
    ]
    upsert_holdings(data, [normalize_holding(item, item["account_id"], item["broker"], item["account_name"], "demo") for item in examples])
    write_portfolio(data)


def clear_portfolio() -> None:
    write_portfolio(deepcopy(EMPTY_PORTFOLIO))
