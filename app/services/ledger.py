"""Smart Family Household Ledger (가계부) Service.

Manages income, expense, transfer transactions, recurring payments, and monthly statistics.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, date
from copy import deepcopy
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
        "cards": [],
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
        data.setdefault("cards", [])
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
    process_recurring_deductions(username=username)
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
    cards_summary = get_cards(username=username, owner=owner)

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
        "cards": cards_summary,
        "categories": data.get("categories", DEFAULT_CATEGORIES),
    }


def _apply_account_balance_delta(
    acc_id: str | None,
    delta: float,
    username: str | None = None,
    overdraft_loan_id: Any = "__AUTO__",
) -> dict[str, Any] | None:
    """Adjust balance of a linked bank account (and its minus/overdraft loan), savings account, or brokerage account.
    Returns balance_effect dict: {bank_account_id, overdraft_loan_id, net_delta, bank_delta, loan_delta}.
    """
    if not acc_id or abs(delta) < 1e-6:
        return None

    from app.services.portfolio import read_portfolio, write_portfolio
    pf = read_portfolio(username)
    now_iso = datetime.now().astimezone().isoformat()
    applied = False
    effect: dict[str, Any] | None = None

    # 1. Look for matching bank account or minus loan in loan_accounts
    target_bank = next((b for b in pf.get("bank_accounts", []) if b.get("id") == acc_id), None)
    target_loan = next((l for l in pf.get("loan_accounts", []) if l.get("id") == acc_id), None)

    # Determine linked_loan based on overdraft_loan_id mode
    if overdraft_loan_id == "__AUTO__":
        if not target_bank and target_loan and target_loan.get("loan_type") == "minus":
            od_bank_id = target_loan.get("overdraft_bank_account_id")
            if od_bank_id:
                target_bank = next((b for b in pf.get("bank_accounts", []) if b.get("id") == od_bank_id), None)
            linked_loan = target_loan
        elif target_bank:
            target_bank_owner = (target_bank.get("owner") or "모두").strip()
            linked_loan = next(
                (
                    l for l in pf.get("loan_accounts", [])
                    if l.get("loan_type") == "minus"
                    and l.get("overdraft_bank_account_id") == target_bank.get("id")
                    and (l.get("owner") or "모두").strip() == target_bank_owner
                ),
                None
            )
        else:
            linked_loan = None
    elif overdraft_loan_id is None:
        linked_loan = None
    else:
        # Explicit overdraft loan ID (historical transaction rollback / restore)
        linked_loan = next((l for l in pf.get("loan_accounts", []) if l.get("id") == overdraft_loan_id), None)
        if not linked_loan:
            raise ValueError(f"거래에 연동되었던 마이너스통장 대출(ID: {overdraft_loan_id})을 찾을 수 없어 안전하게 수정/삭제할 수 없습니다.")
        if not target_bank and linked_loan.get("overdraft_bank_account_id"):
            target_bank = next((b for b in pf.get("bank_accounts", []) if b.get("id") == linked_loan.get("overdraft_bank_account_id")), None)
            if not target_bank:
                raise ValueError(f"거래에 연동되었던 은행 계좌(ID: {linked_loan.get('overdraft_bank_account_id')})가 삭제되어 안전하게 수정/삭제할 수 없습니다.")

    if target_bank and linked_loan:
        # Bank account with linked minus loan (loan_accounts)
        curr_bank_bal = float(target_bank.get("balance") or 0.0)
        loan_limit = float(linked_loan.get("limit_amount") or target_bank.get("limit_amount") or 0.0)
        loan_used = float(linked_loan.get("current_balance") or 0.0)

        if delta < 0:
            # Expense / Withdrawal
            expense = -delta
            avail_loan = max(0.0, loan_limit - loan_used)
            total_avail = max(0.0, curr_bank_bal) + avail_loan
            if expense > total_avail + 1e-6:
                raise ValueError(
                    f"출금 가능 금액(통장잔액 ₩{int(max(0.0, curr_bank_bal)):,} + 마이너스통장 한도 ₩{int(avail_loan):,})을 초과했습니다. "
                    f"(요청: ₩{int(expense):,}, 부족: ₩{int(expense - total_avail):,})"
                )
            if curr_bank_bal > 0:
                if expense <= curr_bank_bal:
                    new_bank_bal = curr_bank_bal - expense
                    new_loan_used = loan_used
                    bank_delta = -expense
                    loan_delta = 0.0
                else:
                    deficit = expense - curr_bank_bal
                    new_bank_bal = 0.0
                    new_loan_used = loan_used + deficit
                    bank_delta = -curr_bank_bal
                    loan_delta = deficit
            else:
                new_bank_bal = 0.0
                new_loan_used = loan_used + expense
                bank_delta = 0.0
                loan_delta = expense
        else:
            # Deposit / Income
            deposit = delta
            if loan_used > 0:
                repay = min(loan_used, deposit)
                new_loan_used = loan_used - repay
                rem_dep = deposit - repay
                new_bank_bal = max(0.0, curr_bank_bal) + rem_dep
                loan_delta = -repay
                bank_delta = rem_dep
            else:
                new_loan_used = 0.0
                new_bank_bal = max(0.0, curr_bank_bal) + deposit
                loan_delta = 0.0
                bank_delta = deposit

        target_bank["balance"] = round(new_bank_bal, 2)
        target_bank["updated_at"] = now_iso
        linked_loan["current_balance"] = round(new_loan_used, 2)
        linked_loan["updated_at"] = now_iso
        effect = {
            "bank_account_id": target_bank["id"],
            "overdraft_loan_id": linked_loan["id"],
            "net_delta": round(delta, 2),
            "bank_delta": round(bank_delta, 2),
            "loan_delta": round(loan_delta, 2),
        }
        applied = True

    elif target_bank:
        # Bank account without linked minus loan in loan_accounts
        curr_bank_bal = float(target_bank.get("balance") or 0.0)
        bank_limit = float(target_bank.get("limit_amount") or 0.0)

        if bank_limit > 0:
            # Overdraft facility configured directly on bank_accounts
            if curr_bank_bal >= 0:
                total_avail = curr_bank_bal + bank_limit
            else:
                total_avail = max(0.0, bank_limit + curr_bank_bal)

            if delta < 0:
                expense = -delta
                if expense > total_avail + 1e-6:
                    raise ValueError(
                        f"출금 가능 금액(통장잔액 및 마이너스 한도 ₩{int(total_avail):,})을 초과했습니다. "
                        f"(요청: ₩{int(expense):,})"
                    )
                new_bank_bal = curr_bank_bal - expense
            else:
                new_bank_bal = curr_bank_bal + delta
        else:
            # Ordinary bank account with no limit (clamping to 0)
            if delta < 0:
                expense = -delta
                if curr_bank_bal > 0:
                    if expense <= curr_bank_bal:
                        actual_bank_delta = -expense
                        new_bank_bal = curr_bank_bal - expense
                    else:
                        actual_bank_delta = -curr_bank_bal
                        new_bank_bal = 0.0
                else:
                    actual_bank_delta = 0.0
                    new_bank_bal = curr_bank_bal
            else:
                actual_bank_delta = delta
                new_bank_bal = curr_bank_bal + delta

            target_bank["balance"] = round(new_bank_bal, 2)
            target_bank["updated_at"] = now_iso
            effect = {
                "bank_account_id": target_bank["id"],
                "overdraft_loan_id": None,
                "net_delta": round(actual_bank_delta, 2),
                "bank_delta": round(actual_bank_delta, 2),
                "loan_delta": 0.0,
            }
            applied = True

    elif target_loan and target_loan.get("loan_type") == "minus":
        # Direct minus loan without bank link
        loan_limit = float(target_loan.get("limit_amount") or 0.0)
        loan_used = float(target_loan.get("current_balance") or 0.0)
        if delta < 0:
            expense = -delta
            avail_loan = max(0.0, loan_limit - loan_used)
            if expense > avail_loan + 1e-6:
                raise ValueError(
                    f"마이너스통장 잔여 한도(₩{int(avail_loan):,})를 초과했습니다. (요청: ₩{int(expense):,})"
                )
            target_loan["current_balance"] = round(loan_used + expense, 2)
        else:
            deposit = delta
            target_loan["current_balance"] = round(max(0.0, loan_used - deposit), 2)
        target_loan["updated_at"] = now_iso
        effect = {
            "bank_account_id": None,
            "overdraft_loan_id": target_loan["id"],
            "net_delta": round(delta, 2),
            "bank_delta": 0.0,
            "loan_delta": round(-delta, 2),
        }
        applied = True

    # 2. Savings accounts
    if not applied:
        for s in pf.get("savings_accounts", []):
            if s.get("id") == acc_id:
                curr = float(s.get("balance") or 0.0)
                if delta < 0 and curr + delta < -1e-6:
                    raise ValueError(f"예·적금 잔액이 부족합니다. (현재 잔액: ₩{int(curr):,}, 요청: ₩{int(-delta):,})")
                s["balance"] = round(curr + delta, 2)
                s["updated_at"] = now_iso
                effect = {
                    "bank_account_id": s["id"],
                    "overdraft_loan_id": None,
                    "net_delta": round(delta, 2),
                    "bank_delta": round(delta, 2),
                    "loan_delta": 0.0,
                }
                applied = True
                break

    # 3. Brokerage accounts
    if not applied:
        for a in pf.get("accounts", []):
            if a.get("id") == acc_id:
                curr = float(a.get("cash") or 0.0)
                if delta < 0 and curr + delta < -1e-6:
                    raise ValueError(f"증권사 예수금이 부족합니다. (현재 예수금: ₩{int(curr):,}, 요청: ₩{int(-delta):,})")
                a["cash"] = round(curr + delta, 2)
                settings = pf.setdefault("settings", {})
                cb = settings.setdefault("cash_balances", {})
                if acc_id in cb and isinstance(cb[acc_id], dict):
                    cb_krw = float(cb[acc_id].get("krw") or 0.0)
                    cb[acc_id]["krw"] = round(max(0.0, cb_krw + delta), 2)
                effect = {
                    "bank_account_id": a["id"],
                    "overdraft_loan_id": None,
                    "net_delta": round(delta, 2),
                    "bank_delta": round(delta, 2),
                    "loan_delta": 0.0,
                }
                applied = True
                break

    if applied:
        write_portfolio(pf, username)
        return effect
    else:
        raise ValueError(f"연동된 계좌(ID: {acc_id})를 포트폴리오에서 찾을 수 없습니다.")


def _rollback_balance_effect(
    effect: dict[str, Any] | None,
    username: str | None = None,
) -> bool:
    """Safely roll back a previously applied balance effect using net_delta and historical account IDs."""
    if not effect:
        return False
    net_delta = float(effect.get("net_delta") or 0.0)
    if abs(net_delta) < 1e-6:
        return False

    bank_id = effect.get("bank_account_id")
    loan_id = effect.get("overdraft_loan_id")
    target_id = bank_id or loan_id
    if not target_id:
        return False

    # The inverse economic delta to apply: -net_delta
    rollback_delta = -net_delta

    _apply_account_balance_delta(
        acc_id=target_id,
        delta=rollback_delta,
        username=username,
        overdraft_loan_id=loan_id,  # Target the exact historical loan (or None if no overdraft loan)
    )
    return True


def _rollback_transaction_effect_or_legacy(
    tx: dict[str, Any],
    username: str | None = None,
) -> bool:
    """Roll back a transaction's balance effect safely. If legacy, prevents unsafe ambiguous guesses."""
    effect = tx.get("balance_effect")
    if effect:
        return _rollback_balance_effect(effect, username=username)

    # Legacy transaction fallback
    old_acc_id = tx.get("account_id")
    old_delta = float(tx.get("applied_delta") or 0.0)
    if not old_acc_id or abs(old_delta) < 1e-6:
        return False

    from app.services.portfolio import read_portfolio
    pf = read_portfolio(username)
    target_bank = next((b for b in pf.get("bank_accounts", []) if b.get("id") == old_acc_id), None)
    if target_bank:
        # Check if there is any overdraft loan currently linked
        linked = next((l for l in pf.get("loan_accounts", []) if l.get("loan_type") == "minus" and l.get("overdraft_bank_account_id") == target_bank.get("id")), None)
        if linked:
            raise ValueError(
                "과거 거래에 마이너스통장 연결 기록(balance_effect)이 없고 현재 계좌에 마이너스통장이 연결되어 있어 안전하게 수정/삭제할 수 없습니다."
            )
        _apply_account_balance_delta(old_acc_id, -old_delta, username=username, overdraft_loan_id=None)
        return True

    # Savings, loan, or brokerage
    _apply_account_balance_delta(old_acc_id, -old_delta, username=username, overdraft_loan_id=None)
    return True



# ---------------------------------------------------------------------------
# Credit / Debit Cards Management & Billing Settlement
# ---------------------------------------------------------------------------

def get_cards(username: str | None = None, owner: str = "모두") -> list[dict[str, Any]]:
    data = read_ledger(username=username)
    cards = data.get("cards", [])
    if owner and owner != "모두":
        cards = [c for c in cards if c.get("owner") == owner or c.get("owner") == "모두"]

    txs = data.get("transactions", [])
    result = []
    for c in cards:
        cid = c.get("id")
        unpaid_txs = [
            t for t in txs
            if t.get("card_id") == cid and t.get("type") == "expense" and not t.get("is_settled", False)
        ]
        unpaid_amount = sum(float(t.get("amount") or 0.0) for t in unpaid_txs)
        c_copy = dict(c)
        c_copy["unpaid_amount"] = unpaid_amount
        c_copy["unpaid_count"] = len(unpaid_txs)
        result.append(c_copy)
    return result


def create_card(payload: dict[str, Any], username: str | None = None) -> dict[str, Any]:
    data = read_ledger(username=username)
    cid = payload.get("id") or str(uuid.uuid4())
    card = {
        "id": cid,
        "card_company": str(payload.get("card_company") or "신용카드").strip(),
        "card_name": str(payload.get("card_name") or "신용카드").strip(),
        "card_type": str(payload.get("card_type") or "credit").strip(),
        "owner": str(payload.get("owner") or "모두").strip(),
        "payment_day": max(1, min(31, int(payload.get("payment_day") or 14))),
        "linked_account_id": str(payload.get("linked_account_id") or "").strip(),
        "linked_account_name": str(payload.get("linked_account_name") or "").strip(),
        "statement_period": str(payload.get("statement_period") or "").strip(),
        "memo": str(payload.get("memo") or "").strip(),
        "created_at": datetime.now().isoformat(),
    }
    data.setdefault("cards", []).append(card)
    write_ledger(data, username=username)
    card["unpaid_amount"] = 0.0
    card["unpaid_count"] = 0
    return card


def update_card(card_id: str, payload: dict[str, Any], username: str | None = None) -> dict[str, Any] | None:
    data = read_ledger(username=username)
    for idx, c in enumerate(data.get("cards", [])):
        if c.get("id") == card_id:
            for k in ["card_company", "card_name", "card_type", "owner", "linked_account_id", "linked_account_name", "statement_period", "memo"]:
                if k in payload:
                    c[k] = str(payload[k]).strip() if payload[k] is not None else ""
            if "payment_day" in payload:
                c["payment_day"] = max(1, min(31, int(payload["payment_day"] or 14)))
            c["updated_at"] = datetime.now().isoformat()
            data["cards"][idx] = c
            write_ledger(data, username=username)
            return c
    return None


def delete_card(card_id: str, username: str | None = None) -> bool:
    data = read_ledger(username=username)
    before = len(data.get("cards", []))
    data["cards"] = [c for c in data.get("cards", []) if c.get("id") != card_id]
    if before != len(data["cards"]):
        write_ledger(data, username=username)
        return True
    return False


def settle_card_payment(card_id: str, payload: dict[str, Any], username: str | None = None) -> dict[str, Any]:
    data = read_ledger(username=username)
    target_card = next((c for c in data.get("cards", []) if c.get("id") == card_id), None)
    if not target_card:
        raise ValueError("신용카드를 찾을 수 없습니다.")

    acc_id = str(payload.get("account_id") or target_card.get("linked_account_id") or "").strip()
    acc_name = str(payload.get("account_name") or target_card.get("linked_account_name") or "").strip()
    pay_date = str(payload.get("date") or date.today().isoformat())

    unpaid_txs = [
        t for t in data.get("transactions", [])
        if t.get("card_id") == card_id and t.get("type") == "expense" and not t.get("is_settled", False)
    ]
    auto_sum = sum(float(t.get("amount") or 0.0) for t in unpaid_txs)
    amount_to_pay = float(payload.get("amount") or auto_sum)

    if amount_to_pay <= 0:
        raise ValueError("결제할 카드 청구 금액이 없습니다 (0원).")

    # 1. 은행 계좌에서 카드 대금 출금 차감
    settle_effect = None
    if acc_id:
        settle_effect = _apply_account_balance_delta(acc_id, -amount_to_pay, username=username)

    # 2. 가계부에 카드대금결제 거래 생성
    settle_tx_id = str(uuid.uuid4())
    settle_tx = {
        "id": settle_tx_id,
        "date": pay_date,
        "type": "transfer",
        "category": "카드대금결제",
        "amount": amount_to_pay,
        "owner": target_card.get("owner", "모두"),
        "pay_method": f"계좌출금 ({acc_name})" if acc_name else "계좌출금",
        "account_id": acc_id,
        "account_name": acc_name,
        "applied_delta": -amount_to_pay if acc_id else 0.0,
        "balance_effect": settle_effect,
        "merchant": f"[{target_card.get('card_name', '신용카드')}] 카드대금 결제",
        "memo": f"{len(unpaid_txs)}건 카드 이용대금 결제 완료",
        "is_recurring": False,
        "created_at": datetime.now().isoformat(),
    }
    data.setdefault("transactions", []).append(settle_tx)

    # 3. 해당 카드 미결제 거래들을 정산 완료(settled) 처리하여 카드 누적액 리셋!
    now_iso = datetime.now().isoformat()
    for t in unpaid_txs:
        t["is_settled"] = True
        t["settled_at"] = now_iso
        t["settled_tx_id"] = settle_tx_id

    write_ledger(data, username=username)
    return {
        "message": f"[{target_card.get('card_name')}] 카드대금 ₩{int(amount_to_pay):,}원이 결제 처리되었습니다.",
        "settled_amount": amount_to_pay,
        "settled_count": len(unpaid_txs),
        "transaction": settle_tx,
    }


def add_transaction(payload: dict[str, Any], username: str | None = None) -> dict[str, Any]:
    data = read_ledger(username=username)
    tx_id = payload.get("id") or str(uuid.uuid4())
    tx_type = str(payload.get("type") or "expense")
    amount = max(0.0, float(payload.get("amount") or 0.0))
    linked_acc_id = str(payload.get("account_id") or "").strip()
    linked_acc_name = str(payload.get("account_name") or "").strip()
    card_id = str(payload.get("card_id") or "").strip()
    card_name = str(payload.get("card_name") or "").strip()
    is_card = bool(card_id or payload.get("is_card_payment", False))

    # Calculate delta for account balance
    # 신용카드 지출인 경우 즉시 은행 계좌를 차감하지 않고 카드에 누적
    applied_delta = 0.0
    balance_effect = None
    apply_to_account = bool(payload.get("apply_to_account", False) or linked_acc_id)
    if apply_to_account and linked_acc_id and amount > 0 and not is_card:
        applied_delta = amount if tx_type == "income" else -amount
        balance_effect = _apply_account_balance_delta(linked_acc_id, applied_delta, username=username)
        if balance_effect:
            applied_delta = float(balance_effect.get("net_delta") or applied_delta)

    tx = {
        "id": tx_id,
        "date": str(payload.get("date") or date.today().isoformat()),
        "type": tx_type,
        "amount": amount,
        "category": str(payload.get("category") or "식비/외식"),
        "owner": str(payload.get("owner") or "모두"),
        "pay_method": str(payload.get("pay_method") or (card_name if is_card else "신용/체크카드")),
        "card_id": card_id,
        "card_name": card_name,
        "is_card_payment": is_card,
        "is_settled": False if is_card else True,
        "account_id": linked_acc_id,
        "account_name": linked_acc_name,
        "applied_delta": applied_delta,
        "balance_effect": balance_effect,
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
            old_effect = tx.get("balance_effect")
            old_delta = float(tx.get("applied_delta") or 0.0)
            old_acc_id = tx.get("account_id")

            # 1. Rollback old balance delta if existed
            rolled_back = False
            if old_effect or (old_acc_id and abs(old_delta) > 1e-6):
                _rollback_transaction_effect_or_legacy(tx, username=username)
                rolled_back = True

            tx_backup = deepcopy(tx)
            try:
                for k in ["date", "type", "category", "owner", "pay_method", "card_id", "card_name", "is_card_payment", "is_settled", "account_id", "account_name", "merchant", "memo", "is_recurring"]:
                    if k in payload:
                        if k in ["is_recurring", "is_card_payment", "is_settled"]:
                            tx[k] = bool(payload[k])
                        else:
                            tx[k] = str(payload[k]).strip() if payload[k] is not None else ""
                if "amount" in payload:
                    tx["amount"] = max(0.0, float(payload["amount"]))

                # 2. Apply new delta
                new_acc_id = str(tx.get("account_id") or "").strip()
                new_amount = float(tx.get("amount") or 0.0)
                new_type = str(tx.get("type") or "expense")
                is_card = bool(tx.get("card_id") or tx.get("is_card_payment", False))
                apply_to_account = bool(payload.get("apply_to_account", False) or new_acc_id)

                new_delta = 0.0
                new_effect = None
                if apply_to_account and new_acc_id and new_amount > 0 and not is_card:
                    new_delta = new_amount if new_type == "income" else -new_amount
                    new_effect = _apply_account_balance_delta(new_acc_id, new_delta, username=username)
                    if new_effect:
                        new_delta = float(new_effect.get("net_delta") or new_delta)

                tx["applied_delta"] = new_delta
                tx["balance_effect"] = new_effect
                tx["updated_at"] = datetime.now().isoformat()
                data["transactions"][idx] = tx
                write_ledger(data, username=username)
                return tx
            except Exception as e:
                # Rollback failed new delta: restore old state!
                if rolled_back:
                    if old_effect:
                        try:
                            target_id = old_effect.get("bank_account_id") or old_effect.get("overdraft_loan_id")
                            _apply_account_balance_delta(
                                acc_id=target_id,
                                delta=float(old_effect.get("net_delta") or 0.0),
                                username=username,
                                overdraft_loan_id=old_effect.get("overdraft_loan_id"),
                            )
                        except Exception as re_err:
                            print(f"Error restoring old balance effect during update failure: {re_err}")
                    elif old_acc_id and abs(old_delta) > 1e-6:
                        try:
                            _apply_account_balance_delta(old_acc_id, old_delta, username=username, overdraft_loan_id=None)
                        except Exception as re_err:
                            print(f"Error restoring old balance delta during update failure: {re_err}")
                data["transactions"][idx] = tx_backup
                raise e
    return None


def delete_transaction(tx_id: str, username: str | None = None) -> bool:
    data = read_ledger(username=username)
    before = len(data.get("transactions", []))
    target_tx = next((t for t in data.get("transactions", []) if t.get("id") == tx_id), None)

    if not target_tx:
        return False

    # 1. Rollback account balance delta if existed
    _rollback_transaction_effect_or_legacy(target_tx, username=username)

    # 2. If this was a card settlement transaction, reset settled status for linked card txs
    for t in data.get("transactions", []):
        if t.get("settled_tx_id") == tx_id:
            t["is_settled"] = False
            t.pop("settled_at", None)
            t.pop("settled_tx_id", None)

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
        "linked_account_id": str(payload.get("linked_account_id") or "").strip(),
        "linked_account_name": str(payload.get("linked_account_name") or "").strip(),
        "auto_deduct": bool(payload.get("auto_deduct", True)),
        "last_deducted_date": str(payload.get("last_deducted_date") or "").strip(),
        "memo": str(payload.get("memo") or "").strip(),
        "active": bool(payload.get("active", True)),
    }
    data["recurring"].append(rec)
    write_ledger(data, username=username)
    # 등록 즉시 오늘 이전 이체일인 경우 자동 출금 처리 시도
    process_recurring_deductions(username=username)
    return rec


def edit_recurring(rec_id: str, payload: dict[str, Any], username: str | None = None) -> dict[str, Any] | None:
    data = read_ledger(username=username)
    for idx, r in enumerate(data.get("recurring", [])):
        if r.get("id") == rec_id:
            r["name"] = str(payload.get("name") or r.get("name")).strip()
            r["amount"] = max(0.0, float(payload.get("amount") if "amount" in payload else r.get("amount", 0)))
            r["day_of_month"] = max(1, min(31, int(payload.get("day_of_month") if "day_of_month" in payload else r.get("day_of_month", 1))))
            r["category"] = str(payload.get("category") or r.get("category"))
            r["owner"] = str(payload.get("owner") or r.get("owner"))
            r["pay_method"] = str(payload.get("pay_method") or r.get("pay_method"))
            if "linked_account_id" in payload:
                r["linked_account_id"] = str(payload.get("linked_account_id") or "").strip()
            if "linked_account_name" in payload:
                r["linked_account_name"] = str(payload.get("linked_account_name") or "").strip()
            if "auto_deduct" in payload:
                r["auto_deduct"] = bool(payload.get("auto_deduct"))
            if "memo" in payload:
                r["memo"] = str(payload.get("memo") or "").strip()
            if "active" in payload:
                r["active"] = bool(payload.get("active"))
            
            data["recurring"][idx] = r
            write_ledger(data, username=username)
            process_recurring_deductions(username=username)
            return r
    return None


def delete_recurring(rec_id: str, username: str | None = None) -> bool:
    data = read_ledger(username=username)
    before = len(data.get("recurring", []))
    data["recurring"] = [r for r in data.get("recurring", []) if r.get("id") != rec_id]
    after = len(data["recurring"])
    if before != after:
        write_ledger(data, username=username)
        return True
    return False


def process_recurring_deductions(username: str | None = None) -> list[dict[str, Any]]:
    """당월 지정일에 도래한 자동이체 고정지출을 연동 통장에서 자동 출금하고 가계부에 기록합니다."""
    import calendar
    data = read_ledger(username=username)
    today = date.today()
    cur_year = today.year
    cur_month = today.month
    cur_prefix = f"{cur_year:04d}-{cur_month:02d}"
    _, max_day = calendar.monthrange(cur_year, cur_month)

    processed = []
    has_changes = False

    for rec in data.get("recurring", []):
        if not rec.get("active", True):
            continue
        if not rec.get("auto_deduct", False):
            continue
        linked_acc_id = str(rec.get("linked_account_id") or "").strip()
        if not linked_acc_id:
            continue
        amount = float(rec.get("amount") or 0.0)
        if amount <= 0:
            continue

        target_day = max(1, min(max_day, int(rec.get("day_of_month") or 1)))
        due_date = date(cur_year, cur_month, target_day)

        # 오늘 날짜가 지정일 이상이고, 당월 아직 출금되지 않은 경우
        if today >= due_date:
            last_deducted = str(rec.get("last_deducted_date") or "")
            if not last_deducted.startswith(cur_prefix):
                # 1. 연동 계좌 잔액 차감 시도
                try:
                    applied_effect = _apply_account_balance_delta(linked_acc_id, -amount, username=username)
                except ValueError as e:
                    # 한도 초과 또는 잔액 부족으로 출금 실패: 가계부 거래를 생성하지 않고 건너뜀
                    print(f"Recurring deduction failed for {rec.get('name')}: {e}")
                    continue
                applied_delta = float(applied_effect.get("net_delta") or -amount) if applied_effect else 0.0

                # 2. 가계부 지출 내역 1건 생성
                tx_date_str = due_date.isoformat()
                acc_name = str(rec.get("linked_account_name") or "연동 통장").strip()
                rec_name = str(rec.get("name") or "정기 고정지출").strip()

                tx = {
                    "id": str(uuid.uuid4()),
                    "date": tx_date_str,
                    "type": str(rec.get("type") or "expense"),
                    "amount": amount,
                    "category": str(rec.get("category") or "주거/통신"),
                    "owner": str(rec.get("owner") or "모두"),
                    "pay_method": str(rec.get("pay_method") or "자동이체"),
                    "account_id": linked_acc_id,
                    "account_name": acc_name,
                    "merchant": rec_name,
                    "memo": f"[정기 자동이체] {rec_name}",
                    "applied_delta": applied_delta,
                    "balance_effect": applied_effect,
                    "is_recurring": True,
                    "recurring_id": rec.get("id"),
                    "created_at": datetime.now().isoformat(),
                }
                data.setdefault("transactions", []).append(tx)
                rec["last_deducted_date"] = tx_date_str
                processed.append({
                    "recurring_id": rec.get("id"),
                    "name": rec_name,
                    "amount": amount,
                    "account_name": acc_name,
                    "deducted_date": tx_date_str,
                    "balance_deducted": bool(applied_effect),
                })
                has_changes = True

    if has_changes:
        write_ledger(data, username=username)

    return processed


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

