"""Smart Family Household Ledger (가계부) Service.

Manages income, expense, transfer transactions, recurring payments, and monthly statistics.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Any

from app.services.user_manager import get_user_data_dir

DEFAULT_CATEGORIES = {
    "expense": [
        "식비/외식",
        "주거/통신",
        "교통/차량",
        "쇼핑/생활용품",
        "교육/학습",
        "의료/건강",
        "문화/여가",
        "경조사/선물",
        "금융/보험/이자",
        "기타지출",
    ],
    "income": [
        "급여/상여",
        "사업소득",
        "배당/금융수익",
        "용돈/이전소득",
        "부수입/기타수입",
    ],
    "transfer": [
        "계좌이체/저축",
        "투자이체",
        "카드대금결제",
    ],
}


def get_ledger_path(username: str | None = None) -> Path:
    user_dir = get_user_data_dir(username)
    return user_dir / "ledger.json"


def default_ledger_data() -> dict[str, Any]:
    return {
        "version": "1.0",
        "categories": DEFAULT_CATEGORIES,
        "transactions": [],
        "recurring": [],
        "budgets": {},
    }


def read_ledger(username: str | None = None) -> dict[str, Any]:
    path = get_ledger_path(username)
    if not os.path.exists(path):
        data = default_ledger_data()
        write_ledger(data, username=username)
        return data
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("version", "1.0")
        data.setdefault("categories", DEFAULT_CATEGORIES)
        data.setdefault("transactions", [])
        data.setdefault("recurring", [])
        data.setdefault("budgets", {})
        return data
    except Exception:
        data = default_ledger_data()
        write_ledger(data, username=username)
        return data


def write_ledger(data: dict[str, Any], username: str | None = None) -> None:
    path = get_ledger_path(username)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def get_ledger_summary(
    username: str | None = None,
    year: int | None = None,
    month: int | None = None,
    owner: str = "모두",
) -> dict[str, Any]:
    data = read_ledger(username=username)
    now = datetime.now()
    target_year = year or now.year
    target_month = month or now.month

    target_prefix = f"{target_year:04d}-{target_month:02d}"

    txs = data.get("transactions", [])
    # 소유자 필터
    if owner and owner != "모두":
        txs = [t for t in txs if t.get("owner") == owner or t.get("owner") == "모두"]

    # 당월 거래 필터링
    month_txs = [t for t in txs if str(t.get("date", "")).startswith(target_prefix)]

    total_income = 0.0
    total_expense = 0.0
    total_transfer = 0.0

    category_expense_map: dict[str, float] = {}
    category_income_map: dict[str, float] = {}

    for t in month_txs:
        amt = float(t.get("amount") or 0.0)
        t_type = t.get("type", "expense")
        cat = t.get("category") or "기타지출"

        if t_type == "income":
            total_income += amt
            category_income_map[cat] = category_income_map.get(cat, 0.0) + amt
        elif t_type == "expense":
            total_expense += amt
            category_expense_map[cat] = category_expense_map.get(cat, 0.0) + amt
        elif t_type == "transfer":
            total_transfer += amt

    net_savings = total_income - total_expense
    savings_rate = (net_savings / total_income * 100.0) if total_income > 0 else 0.0

    # 고정지출 집계
    recurring_list = data.get("recurring", [])
    if owner and owner != "모두":
        recurring_list = [r for r in recurring_list if r.get("owner") == owner or r.get("owner") == "모두"]
    recurring_expense_total = sum(
        float(r.get("amount") or 0.0)
        for r in recurring_list
        if r.get("active", True) and r.get("type", "expense") == "expense"
    )

    # 최근 6개월 추이 계산
    trend_months = []
    curr_y, curr_m = target_year, target_month
    for i in range(5, -1, -1):
        m_val = curr_m - i
        y_val = curr_y
        while m_val <= 0:
            m_val += 12
            y_val -= 1
        prefix = f"{y_val:04d}-{m_val:02d}"
        label = f"{m_val}월"

        m_inc = sum(float(t.get("amount") or 0.0) for t in txs if str(t.get("date", "")).startswith(prefix) and t.get("type") == "income")
        m_exp = sum(float(t.get("amount") or 0.0) for t in txs if str(t.get("date", "")).startswith(prefix) and t.get("type") == "expense")

        trend_months.append({
            "year": y_val,
            "month": m_val,
            "label": label,
            "income": m_inc,
            "expense": m_exp,
            "savings": m_inc - m_exp,
        })

    # 정렬: 날짜 내림차순
    month_txs_sorted = sorted(month_txs, key=lambda x: str(x.get("date", "")), reverse=True)

    return {
        "year": target_year,
        "month": target_month,
        "owner": owner,
        "total_income": total_income,
        "total_expense": total_expense,
        "total_transfer": total_transfer,
        "net_savings": net_savings,
        "savings_rate": round(savings_rate, 1),
        "recurring_expense_total": recurring_expense_total,
        "category_expenses": [
            {"category": k, "amount": v, "percent": round(v / total_expense * 100.0, 1) if total_expense > 0 else 0.0}
            for k, v in sorted(category_expense_map.items(), key=lambda x: x[1], reverse=True)
        ],
        "category_incomes": [
            {"category": k, "amount": v}
            for k, v in sorted(category_income_map.items(), key=lambda x: x[1], reverse=True)
        ],
        "monthly_trend": trend_months,
        "transactions": month_txs_sorted,
        "recurring": recurring_list,
        "categories": data.get("categories", DEFAULT_CATEGORIES),
    }


def _apply_account_balance_delta(
    acc_id: str | None,
    delta: float,
    username: str | None = None,
) -> bool:
    """Adjust balance of a linked bank account, savings account, or brokerage account."""
    if not acc_id or abs(delta) < 1e-6:
        return False
    try:
        from app.services.portfolio import read_portfolio, write_portfolio
        pf = read_portfolio(username)
        applied = False

        # 1. Bank accounts
        for b in pf.get("bank_accounts", []):
            if b.get("id") == acc_id:
                curr = float(b.get("balance") or 0.0)
                b["balance"] = max(0.0, curr + delta)
                b["updated_at"] = datetime.now().astimezone().isoformat()
                applied = True
                break

        # 2. Savings accounts
        if not applied:
            for s in pf.get("savings_accounts", []):
                if s.get("id") == acc_id:
                    curr = float(s.get("balance") or 0.0)
                    s["balance"] = max(0.0, curr + delta)
                    s["updated_at"] = datetime.now().astimezone().isoformat()
                    applied = True
                    break

        # 3. Brokerage accounts
        if not applied:
            for a in pf.get("accounts", []):
                if a.get("id") == acc_id:
                    curr = float(a.get("cash") or 0.0)
                    a["cash"] = max(0.0, curr + delta)
                    # Also update settings.cash_balances if exists
                    settings = pf.setdefault("settings", {})
                    cb = settings.setdefault("cash_balances", {})
                    if acc_id in cb and isinstance(cb[acc_id], dict):
                        cb[acc_id]["krw"] = max(0.0, float(cb[acc_id].get("krw") or 0.0) + delta)
                    applied = True
                    break

        if applied:
            write_portfolio(pf, username)
            return True
    except Exception as e:
        print(f"Error applying balance delta for account {acc_id}: {e}")
    return False


def add_transaction(payload: dict[str, Any], username: str | None = None) -> dict[str, Any]:
    data = read_ledger(username=username)
    tx_id = payload.get("id") or str(uuid.uuid4())
    tx_type = str(payload.get("type") or "expense")
    amount = max(0.0, float(payload.get("amount") or 0.0))
    linked_acc_id = str(payload.get("account_id") or "").strip()
    linked_acc_name = str(payload.get("account_name") or "").strip()
    apply_to_account = bool(payload.get("apply_to_account", False) or linked_acc_id)

    # Calculate delta for account balance
    # income -> +amount, expense -> -amount, transfer -> -amount
    applied_delta = 0.0
    if apply_to_account and linked_acc_id and amount > 0:
        applied_delta = amount if tx_type == "income" else -amount
        _apply_account_balance_delta(linked_acc_id, applied_delta, username=username)

    tx = {
        "id": tx_id,
        "date": str(payload.get("date") or date.today().isoformat()),
        "type": tx_type,
        "amount": amount,
        "category": str(payload.get("category") or "식비/외식"),
        "owner": str(payload.get("owner") or "모두"),
        "pay_method": str(payload.get("pay_method") or "신용/체크카드"),
        "account_id": linked_acc_id,
        "account_name": linked_acc_name,
        "applied_delta": applied_delta,
        "merchant": str(payload.get("merchant") or payload.get("description") or "").strip(),
        "memo": str(payload.get("memo") or "").strip(),
        "is_recurring": bool(payload.get("is_recurring", False)),
        "created_at": datetime.now().isoformat(),
    }
    data["transactions"].append(tx)
    write_ledger(data, username=username)
    return tx


def update_transaction(tx_id: str, payload: dict[str, Any], username: str | None = None) -> dict[str, Any] | None:
    data = read_ledger(username=username)
    for idx, tx in enumerate(data.get("transactions", [])):
        if tx.get("id") == tx_id:
            old_delta = float(tx.get("applied_delta") or 0.0)
            old_acc_id = tx.get("account_id")

            # 1. Rollback old balance delta if existed
            if old_acc_id and abs(old_delta) > 1e-6:
                _apply_account_balance_delta(old_acc_id, -old_delta, username=username)

            for k in ["date", "type", "category", "owner", "pay_method", "account_id", "account_name", "merchant", "memo", "is_recurring"]:
                if k in payload:
                    if k == "is_recurring":
                        tx[k] = bool(payload[k])
                    else:
                        tx[k] = str(payload[k]).strip() if payload[k] is not None else ""
            if "amount" in payload:
                tx["amount"] = max(0.0, float(payload["amount"]))

            # 2. Apply new delta
            new_acc_id = str(tx.get("account_id") or "").strip()
            new_amount = float(tx.get("amount") or 0.0)
            new_type = str(tx.get("type") or "expense")
            apply_to_account = bool(payload.get("apply_to_account", False) or new_acc_id)

            new_delta = 0.0
            if apply_to_account and new_acc_id and new_amount > 0:
                new_delta = new_amount if new_type == "income" else -new_amount
                _apply_account_balance_delta(new_acc_id, new_delta, username=username)

            tx["applied_delta"] = new_delta
            tx["updated_at"] = datetime.now().isoformat()
            data["transactions"][idx] = tx
            write_ledger(data, username=username)
            return tx
    return None


def delete_transaction(tx_id: str, username: str | None = None) -> bool:
    data = read_ledger(username=username)
    before = len(data.get("transactions", []))
    target_tx = next((t for t in data.get("transactions", []) if t.get("id") == tx_id), None)

    # Rollback account balance delta if existed
    if target_tx:
        old_delta = float(target_tx.get("applied_delta") or 0.0)
        old_acc_id = target_tx.get("account_id")
        if old_acc_id and abs(old_delta) > 1e-6:
            _apply_account_balance_delta(old_acc_id, -old_delta, username=username)

    data["transactions"] = [t for t in data.get("transactions", []) if t.get("id") != tx_id]
    after = len(data["transactions"])
    if before != after:
        write_ledger(data, username=username)
        return True
    return False


def add_recurring(payload: dict[str, Any], username: str | None = None) -> dict[str, Any]:
    data = read_ledger(username=username)
    rec_id = payload.get("id") or str(uuid.uuid4())
    rec = {
        "id": rec_id,
        "name": str(payload.get("name") or "고정지출").strip(),
        "type": str(payload.get("type") or "expense"),
        "amount": max(0.0, float(payload.get("amount") or 0.0)),
        "day_of_month": max(1, min(31, int(payload.get("day_of_month") or 1))),
        "category": str(payload.get("category") or "주거/통신"),
        "owner": str(payload.get("owner") or "모두"),
        "pay_method": str(payload.get("pay_method") or "자동이체"),
        "memo": str(payload.get("memo") or "").strip(),
        "active": bool(payload.get("active", True)),
    }
    data["recurring"].append(rec)
    write_ledger(data, username=username)
    return rec


def delete_recurring(rec_id: str, username: str | None = None) -> bool:
    data = read_ledger(username=username)
    before = len(data.get("recurring", []))
    data["recurring"] = [r for r in data.get("recurring", []) if r.get("id") != rec_id]
    after = len(data["recurring"])
    if before != after:
        write_ledger(data, username=username)
        return True
    return False


def import_ledger_from_file_bytes(
    file_bytes: bytes,
    filename: str,
    default_owner: str = "모두",
    username: str | None = None,
) -> int:
    """Parse Excel (.xlsx, .xls) or CSV files and append to transactions."""
    import io
    import csv
    import openpyxl

    rows: list[list[Any]] = []
    fname = filename.lower()

    if fname.endswith(".csv"):
        # UTF-8 or CP949 decoding
        decoded_text = ""
        for encoding in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
            try:
                decoded_text = file_bytes.decode(encoding)
                break
            except Exception:
                continue
        if not decoded_text:
            raise ValueError("CSV 파일 인코딩을 해석할 수 없습니다.")
        reader = csv.reader(io.StringIO(decoded_text))
        rows = [list(r) for r in reader if any(r)]
    else:
        # Excel
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            if any(row):
                rows.append(list(row))

    if not rows:
        raise ValueError("파일에 읽을 수 있는 데이터가 없습니다.")

    # 헤더 행 탐색 (최상위 5행 이내에서 일자, 가맹점/내용, 금액 매핑 검색)
    header_row_idx = -1
    col_map = {
        "date": -1,
        "merchant": -1,
        "amount": -1,
        "type": -1,
        "category": -1,
        "owner": -1,
        "pay_method": -1,
        "memo": -1,
    }

    for idx, r in enumerate(rows[:6]):
        str_row = [str(c or "").strip() for c in r]
        date_idx = next((i for i, c in enumerate(str_row) if any(k in c for k in ["일자", "거래일", "날짜", "date", "승인일"])), -1)
        amt_idx = next((i for i, c in enumerate(str_row) if any(k in c for k in ["금액", "amount", "이용금액", "승인금액", "출금액", "입금액"])), -1)
        merch_idx = next((i for i, c in enumerate(str_row) if any(k in c for k in ["가맹점", "내용", "적요", "상호", "merchant", "description", "거래내역"])), -1)

        if date_idx != -1 and (amt_idx != -1 or merch_idx != -1):
            header_row_idx = idx
            col_map["date"] = date_idx
            col_map["amount"] = amt_idx
            col_map["merchant"] = merch_idx
            col_map["type"] = next((i for i, c in enumerate(str_row) if any(k in c for k in ["구분", "type", "거래구분"])), -1)
            col_map["category"] = next((i for i, c in enumerate(str_row) if any(k in c for k in ["카테고리", "분류", "업종", "category"])), -1)
            col_map["owner"] = next((i for i, c in enumerate(str_row) if any(k in c for k in ["소유자", "이름", "작성자", "owner"])), -1)
            col_map["pay_method"] = next((i for i, c in enumerate(str_row) if any(k in c for k in ["결제", "카드", "수단", "출금처", "통장"])), -1)
            col_map["memo"] = next((i for i, c in enumerate(str_row) if any(k in c for k in ["메모", "비고", "memo", "note"])), -1)
            break

    if header_row_idx == -1:
        # 헤더가 없는 경우 위치 기반 폴백: [0:일자, 1:가맹점, 2:금액...]
        header_row_idx = 0
        col_map["date"] = 0
        col_map["merchant"] = 1
        col_map["amount"] = 2

    data_rows = rows[header_row_idx + 1 :]
    imported_count = 0
    tx_list_to_add = []

    for r in data_rows:
        if not r or all(c is None or str(c).strip() == "" for c in r):
            continue

        # 1. 일자 파싱
        raw_date = str(r[col_map["date"]] if col_map["date"] < len(r) and col_map["date"] != -1 else "").strip()
        if not raw_date:
            continue
        # 날짜 포맷 정리 (YYYYMMDD, YYYY.MM.DD, YYYY/MM/DD -> YYYY-MM-DD)
        clean_date = raw_date.replace(".", "-").replace("/", "-").replace(" ", "")
        if isinstance(r[col_map["date"]], (datetime, date)):
            clean_date = r[col_map["date"]].strftime("%Y-%m-%d")
        elif len(clean_date) == 8 and clean_date.isdigit():
            clean_date = f"{clean_date[:4]}-{clean_date[4:6]}-{clean_date[6:]}"
        elif len(clean_date) >= 10:
            clean_date = clean_date[:10]

        # 2. 내용/가맹점
        merchant = ""
        if col_map["merchant"] != -1 and col_map["merchant"] < len(r):
            merchant = str(r[col_map["merchant"]] or "").strip()

        # 3. 금액 파싱
        raw_amount = ""
        if col_map["amount"] != -1 and col_map["amount"] < len(r):
            raw_amount = str(r[col_map["amount"]] or "").replace(",", "").replace("₩", "").replace("원", "").replace(" ", "").strip()
        try:
            amount = abs(float(raw_amount)) if raw_amount else 0.0
        except ValueError:
            amount = 0.0

        if amount <= 0:
            continue

        # 4. 구분 및 카테고리
        raw_type = str(r[col_map["type"]] if col_map["type"] != -1 and col_map["type"] < len(r) else "").strip()
        is_income = "수입" in raw_type or "입금" in raw_type or "급여" in merchant or "배당" in merchant
        is_transfer = "이체" in raw_type or "저축" in raw_type or "환전" in raw_type
        tx_type = "income" if is_income else ("transfer" if is_transfer else "expense")

        category = ""
        if col_map["category"] != -1 and col_map["category"] < len(r):
            category = str(r[col_map["category"]] or "").strip()
        if not category:
            category = "급여/상여" if is_income else ("계좌이체/저축" if is_transfer else "식비/외식")

        # 5. 소유자
        owner = default_owner
        if col_map["owner"] != -1 and col_map["owner"] < len(r):
            val_owner = str(r[col_map["owner"]] or "").strip()
            if val_owner in ["아빠", "엄마", "자녀", "모두"]:
                owner = val_owner

        # 6. 결제수단 및 메모
        pay_method = "신용/체크카드"
        if col_map["pay_method"] != -1 and col_map["pay_method"] < len(r):
            pay_method = str(r[col_map["pay_method"]] or "").strip() or "신용/체크카드"

        memo = ""
        if col_map["memo"] != -1 and col_map["memo"] < len(r):
            memo = str(r[col_map["memo"]] or "").strip()

        tx = {
            "id": str(uuid.uuid4()),
            "date": clean_date,
            "type": tx_type,
            "amount": amount,
            "category": category,
            "owner": owner,
            "pay_method": pay_method,
            "account_id": "",
            "account_name": "",
            "merchant": merchant or "카드이용",
            "memo": memo,
            "is_recurring": False,
            "created_at": datetime.now().isoformat(),
        }
        tx_list_to_add.append(tx)
        imported_count += 1

    if tx_list_to_add:
        ledger_data = read_ledger(username=username)
        ledger_data["transactions"].extend(tx_list_to_add)
        write_ledger(ledger_data, username=username)

    return imported_count

