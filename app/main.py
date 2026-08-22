from __future__ import annotations

import asyncio
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, Field

from app.services.kb_openapi import KBOpenAPI, KBOpenAPIError
from app.services.nhplug_openapi import NhPlugOpenAPI, NhPlugOpenAPIError
from app.services.toss_openapi import TossOpenAPI, TossOpenAPIError
from app.services.portfolio import (
    clear_portfolio, get_dashboard, get_or_add_account, import_rows, normalize_holding,
    read_portfolio, seed_demo, upsert_holdings, write_portfolio, to_number
)
from app.services.asset_records import delete_asset_record, list_asset_records, upsert_asset_record
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT_DIR / "app" / "static"


def load_env_file() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env_file()
app = FastAPI(title="내 자산 대시보드", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
@app.on_event("startup")
async def ensure_data_dir():
    data_dir = ROOT_DIR / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created data directory at %s", data_dir)
    else:
        logger.info("Data directory exists at %s", data_dir)


# ---------------------------------------------------------------------------
# 로그인 / 인증
# ---------------------------------------------------------------------------

AUTH_USERNAME = os.getenv("DASHBOARD_USERNAME", "")
AUTH_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "")
SESSION_MAX_AGE = 60 * 60 * 24 * 14  # 14일 동안 로그인 유지
COOKIE_NAME = "dashboard_session_v2"

_serializer = URLSafeTimedSerializer(SECRET_KEY) if SECRET_KEY else None
AUTH_CONFIGURED = bool(AUTH_USERNAME and AUTH_PASSWORD and SECRET_KEY)

PUBLIC_PATHS = {"/login"}

LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>로그인 - 내 자산 대시보드</title>
<style>
  body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#0f1115; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
  .card { background:#181b22; padding:36px 32px; border-radius:14px; width:320px;
          box-shadow:0 10px 30px rgba(0,0,0,0.4); }
  h1 { color:#f5f6f8; font-size:20px; margin:0 0 24px; text-align:center; }
  label { display:block; color:#9aa1ac; font-size:13px; margin:14px 0 6px; }
  input { width:100%; box-sizing:border-box; padding:10px 12px; border-radius:8px;
          border:1px solid #2a2f3a; background:#0f1115; color:#f5f6f8; font-size:14px; }
  input:focus { outline:none; border-color:#5b8cff; }
  button { width:100%; margin-top:22px; padding:11px; border:none; border-radius:8px;
           background:#5b8cff; color:white; font-size:15px; font-weight:600; cursor:pointer; }
  button:hover { background:#4a7bef; }
  .error { color:#ff6b6b; font-size:13px; margin-top:14px; text-align:center; }
  .notice { color:#e0a742; font-size:13px; margin-top:14px; text-align:center; line-height:1.5; }
</style>
</head>
<body>
  <div class="card">
    <h1>내 자산 대시보드</h1>
    <form method="post" action="/login">
      <label>아이디</label>
      <input type="text" name="username" autocomplete="username" required autofocus />
      <label>비밀번호</label>
      <input type="password" name="password" autocomplete="current-password" required />
      <button type="submit">로그인</button>
    </form>
    {{message}}
  </div>
</body>
</html>"""


def _is_authenticated(request: Request) -> bool:
    if not AUTH_CONFIGURED:
        return False
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return data.get("user") == AUTH_USERNAME


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/static/") or path == "/favicon.ico":
        return await call_next(request)
    if not _is_authenticated(request):
        if path.startswith("/api/"):
            return JSONResponse({"detail": "로그인이 필요합니다."}, status_code=401)
        return RedirectResponse("/login")
    return await call_next(request)


@app.get("/login", include_in_schema=False)
async def login_page(error: str | None = None) -> HTMLResponse:
    if not AUTH_CONFIGURED:
        message = (
            "<p class='notice'>로그인 정보가 설정되지 않았습니다.<br>"
            "서버의 .env 파일에 DASHBOARD_USERNAME, DASHBOARD_PASSWORD, "
            "DASHBOARD_SECRET_KEY를 입력한 뒤 다시 시작하세요.</p>"
        )
    elif error:
        message = "<p class='error'>아이디 또는 비밀번호가 올바르지 않습니다.</p>"
    else:
        message = ""
    return HTMLResponse(LOGIN_PAGE_HTML.replace("{{message}}", message))


@app.post("/login", include_in_schema=False)
async def login_submit(username: str = Form(...), password: str = Form(...)):
    if not AUTH_CONFIGURED:
        return RedirectResponse("/login", status_code=303)
    ok_user = secrets.compare_digest(username, AUTH_USERNAME)
    ok_pass = secrets.compare_digest(password, AUTH_PASSWORD)
    if ok_user and ok_pass:
        token = _serializer.dumps({"user": AUTH_USERNAME})
        response = RedirectResponse("/dashboard", status_code=303)
        response.set_cookie(
            COOKIE_NAME, token, httponly=True, samesite="lax", max_age=SESSION_MAX_AGE
        )
        return response
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/logout", include_in_schema=False)
async def logout() -> RedirectResponse:
    response = RedirectResponse("/login")
    response.delete_cookie(COOKIE_NAME)
    return response


# ---------------------------------------------------------------------------
# 기존 기능
# ---------------------------------------------------------------------------


class HoldingCreate(BaseModel):
    broker: str = Field(min_length=1, max_length=60)
    account_name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    quantity: float = Field(gt=0)
    avg_price: float = Field(ge=0)
    current_price: float = Field(ge=0)
    currency: str = "KRW"
    market: str = ""


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> HTMLResponse:
    return HTMLResponse(status_code=204)


@app.get("/api/dashboard")
async def dashboard() -> dict:
    data = get_dashboard()
    day = data.get("day_change") or {}
    today = datetime.now().astimezone().date().isoformat()
    if data["summary"]["holding_count"]:
        snapshot = {
            "date": today,
            "total_value_krw": data["summary"]["total_value_krw"],
            "total_cost_krw": data["summary"]["total_cost_krw"],
            "profit_krw": data["summary"]["profit_krw"],
            "return_rate": data["summary"]["return_rate"],
            "day_profit_krw": day.get("change_krw") or 0,
            "krw_value_krw": data.get("currency_summary", {}).get("KRW", {}).get("market_value_krw", 0),
            "usd_value_krw": data.get("currency_summary", {}).get("USD", {}).get("market_value_krw", 0),
            "holding_count": data["summary"]["holding_count"],
            "currency": "KRW",
            "source": "auto",
            "memo": "자동 기록",
        }
        upsert_asset_record(snapshot, by_date=True)
    return data


@app.get("/api/status")
async def status() -> dict:
    return {
        "kb_configured": KBOpenAPI().configured,
        "toss_configured": TossOpenAPI().configured,
        "namoo_configured": NhPlugOpenAPI().configured,
        "storage": "local",
    }


@app.on_event("startup")
async def startup_event() -> None:
    toss = TossOpenAPI()
    if toss.configured:
        data = read_portfolio()
        syms = list({str(h.get("code", "")).upper() for h in data.get("holdings", []) if h.get("code")})
        if syms:
            asyncio.create_task(toss.get_multi_period_changes(syms))


@app.get("/api/market-overview")
async def market_overview() -> dict:
    client = TossOpenAPI()
    try:
        markets = await client.get_market_overview()
        exchange_rate = await client.get_usd_krw_rate()
    except TossOpenAPIError as exc:
        raise HTTPException(400, str(exc)) from exc
    data = read_portfolio()

    # 백그라운드에서 다중 기간(1W/1M/YTD/1Y) 수익률 캐시 갱신 (15분 이상 지났거나 파일 없을 때)
    cache_file = ROOT_DIR / "data" / "period_rates.json"
    cache_age = (time.time() - cache_file.stat().st_mtime) if cache_file.exists() else 999999
    if cache_age > 900 and client.configured:
        unique_symbols = list({str(h.get("code", "")).upper() for h in data.get("holdings", []) if h.get("code")})
        if unique_symbols:
            asyncio.create_task(client.get_multi_period_changes(unique_symbols))
    rate = float(exchange_rate["rate"])
    mid_rate = float(exchange_rate.get("mid_rate") or rate)

    history = data["settings"].setdefault("fx_history", [])
    if not history or abs(float(history[-1].get("rate", 0)) - rate) > 0.0001:
        history.append({"at": datetime.now().astimezone().isoformat(timespec="seconds"), "rate": rate})
        data["settings"]["fx_history"] = history[-60:]
        write_portfolio(data)

    prev_rate = None
    if len(history) >= 2:
        for item in reversed(history[:-1]):
            r_val = float(item.get("rate", 0))
            if abs(r_val - rate) > 0.001:
                prev_rate = r_val
                break
    if prev_rate is None and mid_rate > 0 and abs(rate - mid_rate) > 0.001:
        prev_rate = mid_rate

    if prev_rate and prev_rate > 0:
        fx_change = rate - prev_rate
        fx_change_rate = fx_change / prev_rate * 100
    else:
        fx_change = 0.0
        fx_change_rate = 0.0

    fx_series = [float(item["rate"]) for item in data["settings"]["fx_history"]]
    if len(fx_series) < 3:
        if mid_rate > 0 and abs(mid_rate - rate) > 0.001:
            fx_series = [mid_rate, (mid_rate + rate) / 2, rate]
        else:
            fx_series = [rate * 0.999, rate * 1.0005, rate]

    exchange_rate["change"] = fx_change
    exchange_rate["change_rate"] = fx_change_rate
    exchange_rate["series"] = fx_series
    return {"markets": markets, "exchange_rate": exchange_rate, "source": "토스증권 OpenAPI"}


@app.post("/api/holdings", status_code=201)
async def create_holding(payload: HoldingCreate) -> dict:
    data = read_portfolio()
    account_id = get_or_add_account(data, payload.broker.strip(), payload.account_name.strip(), "manual")
    item = normalize_holding(payload.model_dump(), account_id, payload.broker.strip(), payload.account_name.strip(), "manual")
    upsert_holdings(data, [item])
    write_portfolio(data)
    return {"message": "보유종목을 저장했습니다.", "dashboard": get_dashboard()}


@app.delete("/api/holdings/{holding_id}")
async def delete_holding(holding_id: str) -> dict:
    data = read_portfolio()
    before = len(data["holdings"])
    data["holdings"] = [holding for holding in data["holdings"] if holding["id"] != holding_id]
    if before == len(data["holdings"]):
        raise HTTPException(404, "보유종목을 찾지 못했습니다.")
    used_accounts = {holding["account_id"] for holding in data["holdings"]}
    data["accounts"] = [account for account in data["accounts"] if account["id"] in used_accounts]
    write_portfolio(data)
    return {"message": "보유종목을 삭제했습니다."}


@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: str) -> dict:
    data = read_portfolio()
    if not any(account.get("id") == account_id for account in data["accounts"]):
        raise HTTPException(404, "계좌를 찾지 못했습니다.")
    data["accounts"] = [account for account in data["accounts"] if account.get("id") != account_id]
    data["holdings"] = [holding for holding in data["holdings"] if holding.get("account_id") != account_id]
    if "cash_balances" in data["settings"] and account_id in data["settings"]["cash_balances"]:
        del data["settings"]["cash_balances"][account_id]
    write_portfolio(data)
    return {"message": "증권사 계좌와 연결된 보유종목을 삭제했습니다."}


@app.put("/api/accounts/{account_id}")
async def rename_account(account_id: str, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    broker = str(payload.get("broker") or "").strip()
    if not name:
        raise HTTPException(400, "계좌 이름을 입력해 주세요.")
    data = read_portfolio()
    account = next((item for item in data["accounts"] if item.get("id") == account_id), None)
    if account is None:
        raise HTTPException(404, "계좌를 찾지 못했습니다.")
    account["name"] = name
    if broker:
        account["broker"] = broker
    for holding in data["holdings"]:
        if holding.get("account_id") == account_id:
            holding["account_name"] = name
            if broker:
                holding["broker"] = broker
    write_portfolio(data)
    return {"message": "증권사 및 계좌 정보를 수정했습니다."}


@app.put("/api/accounts/{account_id}/cash")
async def update_account_cash(account_id: str, payload: dict) -> dict:
    data = read_portfolio()
    if not any(account.get("id") == account_id for account in data["accounts"]):
        raise HTTPException(404, "계좌를 찾지 못했습니다.")
    cash_krw = float(to_number(payload.get("cash_krw") or payload.get("KRW")))
    cash_usd = float(to_number(payload.get("cash_usd") or payload.get("USD")))
    cash_balances = data["settings"].setdefault("cash_balances", {})
    cash_balances[account_id] = {"KRW": cash_krw, "USD": cash_usd}
    write_portfolio(data)
    return {"message": "계좌 예수금을 수정했습니다.", "dashboard": get_dashboard()}


@app.put("/api/holdings/{holding_id}")
async def update_holding(holding_id: str, payload: HoldingCreate) -> dict:
    data = read_portfolio()
    current = next((item for item in data["holdings"] if item["id"] == holding_id), None)
    if current is None:
        raise HTTPException(404, "보유종목을 찾지 못했습니다.")
    broker = payload.broker.strip()
    account_name = payload.account_name.strip()
    account_id = get_or_add_account(data, broker, account_name, current.get("source", "manual"))
    item = normalize_holding(payload.model_dump(), account_id, broker, account_name, current.get("source", "manual"))
    item["id"] = holding_id
    data["holdings"] = [item if holding["id"] == holding_id else holding for holding in data["holdings"]]
    write_portfolio(data)
    return {"message": "보유종목을 수정했습니다.", "dashboard": get_dashboard()}


@app.post("/api/import")
async def import_portfolio(file: UploadFile = File(...), broker: str = "기타 증권사") -> dict:
    if Path(file.filename or "").suffix.lower() not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(400, "CSV 또는 XLSX 파일만 가져올 수 있습니다.")
    try:
        count, warnings = import_rows(file.filename or "portfolio.csv", await file.read(), broker)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"message": f"{count}개 보유종목을 반영했습니다.", "count": count, "warnings": warnings}


@app.post("/api/demo")
async def load_demo() -> dict:
    seed_demo()
    return {"message": "예시 데이터를 불러왔습니다."}


@app.post("/api/clear")
async def clear_all() -> dict:
    clear_portfolio()
    return {"message": "저장된 보유내역을 모두 지웠습니다."}


@app.get("/api/asset-records")
async def get_asset_records() -> dict:
    return {"records": list_asset_records()}


@app.post("/api/asset-records")
async def create_asset_record(payload: dict) -> dict:
    record = upsert_asset_record(payload, by_date=bool(payload.get("date")))
    return {"message": "자산기록을 저장했습니다.", "record": record}


@app.put("/api/asset-records/{record_id}")
async def update_asset_record(record_id: str, payload: dict) -> dict:
    payload["id"] = record_id
    record = upsert_asset_record(payload)
    return {"message": "자산기록을 수정했습니다.", "record": record}


@app.delete("/api/asset-records/{record_id}")
async def remove_asset_record(record_id: str) -> dict:
    if not delete_asset_record(record_id):
        raise HTTPException(404, "자산기록을 찾지 못했습니다.")
    return {"message": "자산기록을 삭제했습니다."}


@app.post("/api/asset-records/snapshot")
async def snapshot_asset_record() -> dict:
    data = get_dashboard()
    if not data["summary"]["holding_count"]:
        raise HTTPException(400, "저장할 보유자산이 없습니다.")
    day = data.get("day_change") or {}
    record = upsert_asset_record(
        {
            "date": datetime.now().astimezone().date().isoformat(),
            "total_value_krw": data["summary"]["total_value_krw"],
            "total_cost_krw": data["summary"]["total_cost_krw"],
            "profit_krw": data["summary"]["profit_krw"],
            "return_rate": data["summary"]["return_rate"],
            "day_profit_krw": day.get("change_krw") or 0,
            "krw_value_krw": data.get("currency_summary", {}).get("KRW", {}).get("market_value_krw", 0),
            "usd_value_krw": data.get("currency_summary", {}).get("USD", {}).get("market_value_krw", 0),
            "holding_count": data["summary"]["holding_count"],
            "currency": "KRW",
            "source": "snapshot",
            "memo": "수동 스냅샷",
        },
        by_date=True,
    )
    return {"message": "오늘 자산을 기록했습니다.", "record": record}


@app.post("/api/sync/kb")
async def sync_kb() -> dict:
    client = KBOpenAPI()
    try:
        records = await client.sync_holdings()
    except KBOpenAPIError as exc:
        raise HTTPException(400, str(exc)) from exc
    data = read_portfolio()
    existing = next((a for a in data["accounts"] if a.get("broker") == "KB증권" and a.get("source") == "kb_api"), None)
    account_id = existing["id"] if existing else get_or_add_account(data, "KB증권", "KB OpenAPI 동기화 계좌", "kb_api")
    holdings = [normalize_holding(record, account_id, "KB증권", "KB OpenAPI 동기화 계좌", "kb_api") for record in records]
    prices, warnings = await client.refresh_prices(holdings)
    for holding in holdings:
        price = prices.get(holding["id"])
        if price:
            holding["current_price"] = price
            if holding["avg_price"] == 0:
                holding["avg_price"] = price
    upsert_holdings(data, holdings, replace_source="kb_api")
    write_portfolio(data)
    return {"message": f"KB증권 보유종목 {len(holdings)}개를 동기화했습니다.", "count": len(holdings), "warnings": warnings[:10]}


@app.post("/api/sync/toss")
async def sync_toss() -> dict:
    client = TossOpenAPI()
    try:
        records = await client.sync_holdings()
        toss_accounts = client.last_accounts
    except TossOpenAPIError as exc:
        raise HTTPException(400, str(exc)) from exc
    data = read_portfolio()
    cash = data["settings"].setdefault("toss_cash", {})
    cash_balances = data["settings"].setdefault("cash_balances", {})
    for account in toss_accounts:
        seq = account.get("accountSeq")
        account_no = str(account.get("accountNo", ""))
        account_name = f"토스증권 계좌 {account_no[-4:]}" if account_no else f"토스증권 계좌 {seq}"
        existing = next((a for a in data["accounts"] if a.get("broker") == "토스증권" and a.get("source") == "toss_api" and a.get("name") == account_name), None)
        existing = existing or next((a for a in data["accounts"] if a.get("broker") == "토스증권" and a.get("source") == "toss_api"), None)
        account_id = existing["id"] if existing else get_or_add_account(data, "토스증권", account_name, "toss_api")
        if seq is not None:
            try:
                bp = await client.get_buying_power(int(seq))
                cash[str(seq)] = bp
                cash_balances[account_id] = bp
            except TossOpenAPIError:
                pass
    data["settings"]["toss_cash"] = cash
    data["settings"]["cash_balances"] = cash_balances
    holdings = []
    for record in records:
        existing = next((a for a in data["accounts"] if a.get("broker") == "토스증권" and a.get("source") == "toss_api" and a.get("name") == record["account_name"]), None)
        existing = existing or next((a for a in data["accounts"] if a.get("broker") == "토스증권" and a.get("source") == "toss_api"), None)
        account_id = existing["id"] if existing else get_or_add_account(data, "토스증권", record["account_name"], "toss_api")
        holdings.append(normalize_holding(record, account_id, "토스증권", record["account_name"], "toss_api"))
    upsert_holdings(data, holdings, replace_source="toss_api")
    write_portfolio(data)
    return {"message": f"토스증권 보유종목 {len(holdings)}개 및 예수금을 동기화했습니다.", "count": len(holdings)}


@app.post("/api/sync/namoo")
async def sync_namoo() -> dict:
    client = NhPlugOpenAPI()
    try:
        records = await client.sync_holdings()
    except NhPlugOpenAPIError as exc:
        detail = str(exc)
        if "IGW42903" in detail or "거래건수를 초과" in detail:
            detail = "나무증권 API 호출 한도를 초과했습니다(IGW42903). 잠시 후 다시 시도하거나 나무 OpenAPI 포털에서 호출 한도·계정별 제한을 확인해 주세요. 인증키 오류가 아닙니다."
        raise HTTPException(429 if "IGW42903" in str(exc) else 400, detail) from exc
    data = read_portfolio()
    cash_balances = data["settings"].setdefault("cash_balances", {})
    for account in client.last_accounts:
        account_no = str(account.get("acct_no", ""))
        account_name = client._account_name(account)
        if account_no:
            existing = next((a for a in data["accounts"] if a.get("broker") == "NH투자증권(나무)" and a.get("source") == "nhplug_api" and a.get("name") == account_name), None)
            existing = existing or next((a for a in data["accounts"] if a.get("broker") == "NH투자증권(나무)" and a.get("source") == "nhplug_api"), None)
            account_id = existing["id"] if existing else get_or_add_account(data, "NH투자증권(나무)", account_name, "nhplug_api")
            if account_no in client.account_cash:
                cash_balances[account_id] = client.account_cash[account_no]
    holdings = []
    for record in records:
        existing = next((a for a in data["accounts"] if a.get("broker") == "NH투자증권(나무)" and a.get("source") == "nhplug_api" and a.get("name") == record["account_name"]), None)
        existing = existing or next((a for a in data["accounts"] if a.get("broker") == "NH투자증권(나무)" and a.get("source") == "nhplug_api"), None)
        account_id = existing["id"] if existing else get_or_add_account(data, "NH투자증권(나무)", record["account_name"], "nhplug_api")
        holdings.append(normalize_holding(record, account_id, "NH투자증권(나무)", record["account_name"], "nhplug_api"))
    upsert_holdings(data, holdings, replace_source="nhplug_api")
    data["settings"]["cash_balances"] = cash_balances
    write_portfolio(data)
    return {"message": f"나무증권 보유종목 {len(holdings)}개 및 예수금을 동기화했습니다.", "count": len(holdings)}


@app.post("/api/fx/refresh")
async def refresh_fx_rate() -> dict:
    client = TossOpenAPI()
    data = read_portfolio()
    currencies = sorted({str(holding.get("currency", "")).upper() for holding in data["holdings"] if holding.get("currency") not in {"", "KRW"}})
    if not currencies:
        currencies = ["USD"]
    quotes: dict[str, dict] = {}
    warnings: list[str] = []
    for currency in currencies:
        try:
            quotes[currency] = await client.get_exchange_rate(currency, "KRW")
        except TossOpenAPIError as exc:
            warnings.append(str(exc))
    if not quotes:
        raise HTTPException(400, " / ".join(warnings) or "토스증권 환율을 가져오지 못했습니다.")
    for currency, quote in quotes.items():
        data["settings"]["fx_rates"][currency] = quote["rate"]
    usd_quote = quotes.get("USD", {})
    data["settings"]["fx_info"] = {"source": "토스증권 OpenAPI", "quotes": quotes, **usd_quote}
    write_portfolio(data)
    updated = ", ".join(f"{currency}/KRW" for currency in quotes)
    return {"message": f"토스증권 실시간 환율({updated})을 반영했습니다.", "quotes": quotes, "warnings": warnings}


@app.post("/api/refresh-prices")
async def refresh_prices() -> dict:
    data = read_portfolio()
    if not data["holdings"]:
        raise HTTPException(400, "갱신할 보유종목이 없습니다.")
    kb_client = KBOpenAPI()
    toss_client = TossOpenAPI()
    namoo_client = NhPlugOpenAPI()
    if not kb_client.configured and not toss_client.configured and not namoo_client.configured:
        raise HTTPException(400, "KB·토스·나무증권 OpenAPI 키 중 하나를 .env에 설정하세요.")
    prices: dict[str, float] = {}
    warnings: list[str] = []
    if kb_client.configured:
        kb_holdings = [holding for holding in data["holdings"] if not str(holding.get("market", "")).startswith(("TOSS_", "NH_"))]
        try:
            kb_prices, kb_warnings = await kb_client.refresh_prices(kb_holdings)
            prices.update(kb_prices)
            warnings.extend(kb_warnings)
        except KBOpenAPIError as exc:
            warnings.append(str(exc))
    if toss_client.configured:
        try:
            toss_holdings = [holding for holding in data["holdings"] if holding.get("currency") in {"KRW", "USD"}]
            toss_prices, toss_warnings = await toss_client.refresh_prices(toss_holdings)
            prices.update(toss_prices)
            warnings.extend(toss_warnings)
            unique_symbols = list({str(h.get("code", "")).upper() for h in toss_holdings if h.get("code")})
            multi_changes = await toss_client.get_multi_period_changes(unique_symbols)
            daily_changes = {s: d["1D"] for s, d in multi_changes.items() if "1D" in d}
            data["settings"].setdefault("daily_price_changes", {}).update(daily_changes)
            data["settings"].setdefault("period_rates", {}).update(multi_changes)
        except TossOpenAPIError as exc:
            warnings.append(str(exc))
    if namoo_client.configured:
        warnings.append("나무증권 보유종목·시세는 '나무 계좌 동기화' 버튼으로 함께 갱신됩니다.")
    for holding in data["holdings"]:
        if holding["id"] in prices:
            holding["current_price"] = prices[holding["id"]]
            holding["price_updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    write_portfolio(data)
    return {"message": f"{len(prices)}개 종목의 시세를 갱신했습니다.", "count": len(prices), "warnings": warnings[:10]}
