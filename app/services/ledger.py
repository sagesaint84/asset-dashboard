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


def add_transaction(payload: dict[str, Any], username: str | None = None) -> dict[str, Any]:
    data = read_ledger(username=username)
    tx_id = payload.get("id") or str(uuid.uuid4())
    tx = {
        "id": tx_id,
        "date": str(payload.get("date") or date.today().isoformat()),
        "type": str(payload.get("type") or "expense"),
        "amount": max(0.0, float(payload.get("amount") or 0.0)),
        "category": str(payload.get("category") or "식비/외식"),
        "owner": str(payload.get("owner") or "모두"),
        "pay_method": str(payload.get("pay_method") or "신용/체크카드"),
        "account_id": str(payload.get("account_id") or ""),
        "account_name": str(payload.get("account_name") or ""),
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
            for k in ["date", "type", "category", "owner", "pay_method", "account_id", "account_name", "merchant", "memo", "is_recurring"]:
                if k in payload:
                    if k == "amount":
                        tx[k] = max(0.0, float(payload[k]))
                    elif k == "is_recurring":
                        tx[k] = bool(payload[k])
                    else:
                        tx[k] = payload[k]
            if "amount" in payload:
                tx["amount"] = max(0.0, float(payload["amount"]))
            tx["updated_at"] = datetime.now().isoformat()
            data["transactions"][idx] = tx
            write_ledger(data, username=username)
            return tx
    return None


def delete_transaction(tx_id: str, username: str | None = None) -> bool:
    data = read_ledger(username=username)
    before = len(data.get("transactions", []))
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
