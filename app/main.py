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
from app.services.web_finance import (
    get_web_market_overview,
    fetch_fx_rate_usd_krw,
    refresh_all_holdings_prices,
    fetch_stock_chart_data,
    get_web_dividend_summary,
)
fetch_market_overview = get_web_market_overview
from app.services.portfolio import (
    clear_portfolio, get_dashboard, get_or_add_account, import_rows, normalize_holding,
    read_portfolio, seed_demo, upsert_holdings, write_portfolio, to_number, migrate_add_family_group
)
from app.services.asset_records import delete_asset_record, list_asset_records, upsert_asset_record
from app.services.dividend_records import (
    create_dividend_record, delete_dividend_record, get_actual_dividend_summary,
    read_dividend_records, update_dividend_record, import_dividend_file_data,
    clear_dividend_records, recalculate_dividend_historical_fx
)
from app.services.pnl_records import (
    create_pnl_record, delete_pnl_record, get_pnl_summary,
    read_pnl_records, update_pnl_record, import_pnl_file_data,
    clear_pnl_records, recalculate_pnl_historical_fx
)
from app.services.historical_fx import get_historical_fx_rate, sync_historical_fx
from app.services.stock_master import sync_stock_master_online
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
    # Run migration to ensure family_group field exists on accounts
    migrate_add_family_group()
    # 5년치 과거 환율 비동기 동기화
    asyncio.create_task(sync_historical_fx())
    # 종목 마스터(국내 ETF/상장사/미국주식) 비동기 동기화
    asyncio.create_task(sync_stock_master_online())



# ---------------------------------------------------------------------------
# 로그인 / 인증
# ---------------------------------------------------------------------------

AUTH_USERNAME = os.getenv("DASHBOARD_USERNAME", "").strip()
AUTH_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "").strip()
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "").strip() or "asset_dashboard_secret_key_default"
SESSION_MAX_AGE = 60 * 60 * 24 * 14  # 14일 동안 로그인 유지
COOKIE_NAME = "dashboard_session_v2"

_serializer = URLSafeTimedSerializer(SECRET_KEY) if SECRET_KEY else None
AUTH_CONFIGURED = bool(AUTH_USERNAME and AUTH_PASSWORD and SECRET_KEY)

PUBLIC_PATHS = {"/login", "/api/export"}


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
    client_host = request.client.host if request.client else ""
    is_local = client_host in ("127.0.0.1", "localhost", "::1", "testclient")
    
    if is_local or path in PUBLIC_PATHS or path.startswith("/static/") or path == "/favicon.ico":
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
    owner: str = "모두"


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


@app.get("/api/dividends")
async def get_dividends(owner: str = "모두") -> dict:
    """Return dividend summary and 12-month schedule for holdings."""
    full = get_dashboard()
    holdings = full.get("holdings", [])
    if owner != "모두":
        holdings = [h for h in holdings if h.get("owner", "모두") == owner]
    fx_rate = full.get("fx_rates", {}).get("USD", 1385.0)
    summary = await get_web_dividend_summary(holdings, fx_rate=fx_rate)
    return summary


@app.get("/api/actual-dividends")
async def get_actual_dividends(owner: str = "모두", year: str | None = None) -> dict:
    """Return actual dividend records and 12-month summary."""
    return get_actual_dividend_summary(owner=owner, year=year)


@app.post("/api/actual-dividends")
async def add_actual_dividend(request: Request) -> dict:
    """Add a new actual dividend record."""
    body = await request.json()
    record = create_dividend_record(body)
    return {"message": "배당금이 등록되었습니다.", "record": record}


@app.put("/api/actual-dividends/{record_id}")
async def edit_actual_dividend(record_id: str, request: Request) -> dict:
    """Update an existing actual dividend record."""
    body = await request.json()
    record = update_dividend_record(record_id, body)
    if not record:
        raise HTTPException(status_code=404, detail="배당 기록을 찾을 수 없습니다.")
    return {"message": "배당금이 수정되었습니다.", "record": record}


@app.delete("/api/actual-dividends/{record_id}")
async def remove_actual_dividend(record_id: str) -> dict:
    """Delete an actual dividend record."""
    ok = delete_dividend_record(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="배당 기록을 찾을 수 없습니다.")
    return {"message": "배당 기록이 삭제되었습니다."}


@app.post("/api/import-dividends")
async def import_dividends_endpoint(file: UploadFile = File(...)) -> dict:
    """Import actual dividend records from Excel or CSV."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="업로드할 파일을 선택하세요.")
    contents = await file.read()
    full = get_dashboard()
    fx_rate = full.get("fx_rates", {}).get("USD", 1385.0)
    try:
        records = import_dividend_file_data(contents, file.filename, fx_rate=fx_rate)
        return {
            "message": f"총 {len(records)}건의 배당금 내역을 가져왔습니다.",
            "count": len(records),
            "records": records,
        }
    except Exception as e:
        logger.exception("배당 파일 가져오기 실패")
        raise HTTPException(status_code=400, detail=f"배당 파일 처리 실패: {e}")


@app.post("/api/actual-dividends/clear")
async def clear_actual_dividends_endpoint() -> dict:
    """Clear all actual dividend records."""
    clear_dividend_records()
    return {"message": "모든 실제 배당금 기록이 삭제되었습니다."}


@app.post("/api/actual-dividends/recalculate-fx")
async def recalculate_actual_dividends_fx() -> dict:
    """Recalculate USD dividend amounts using historical exchange rates for each deposit date."""
    await sync_historical_fx()
    updated = recalculate_dividend_historical_fx()
    return {"message": f"총 {updated}건의 해외 배당금 환율이 입금일자 기준으로 재계산되었습니다.", "updated_count": updated}


@app.get("/api/historical-fx")
async def get_historical_fx_endpoint(date: str = "") -> dict:
    """Get historical USD/KRW exchange rate for a given date."""
    today = datetime.now().strftime("%Y-%m-%d")
    target = date.strip() or today
    rate = get_historical_fx_rate(target)
    return {"date": target, "rate": rate, "currency": "USD"}


@app.get("/api/sample/dividends")
async def download_sample_dividends():
    """Download sample Excel file for actual dividend tracking."""
    p = ROOT_DIR / "data" / "샘플_배당.xlsx"
    if not p.exists():
        p = ROOT_DIR / "샘플_배당.xlsx"
    if not p.exists():
        raise HTTPException(status_code=404, detail="샘플_배당.xlsx 파일을 찾을 수 없습니다.")
    return FileResponse(
        path=str(p),
        filename="샘플_배당.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/sample/holdings")
async def download_sample_holdings():
    """Download sample Excel file for portfolio holdings."""
    p = ROOT_DIR / "data" / "샘플_타증권사_보유종목.xlsx"
    if not p.exists():
        p = ROOT_DIR / "샘플_타증권사_보유종목.xlsx"
    if not p.exists():
        raise HTTPException(status_code=404, detail="샘플_타증권사_보유종목.xlsx 파일을 찾을 수 없습니다.")
    return FileResponse(
        path=str(p),
        filename="샘플_타증권사_보유종목.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Realized PnL API
# ---------------------------------------------------------------------------

@app.get("/api/realized-pnl")
async def get_realized_pnl(owner: str = "모두", year: str | None = None, trade_type: str = "all") -> dict:
    """Return realized profit and loss records and summary."""
    return get_pnl_summary(owner=owner, year=year, trade_type=trade_type)


@app.post("/api/realized-pnl")
async def add_realized_pnl(request: Request) -> dict:
    """Add a new realized PnL record."""
    body = await request.json()
    record = create_pnl_record(body)
    return {"message": "매도 실현손익이 등록되었습니다.", "record": record}


@app.put("/api/realized-pnl/{record_id}")
async def edit_realized_pnl(record_id: str, request: Request) -> dict:
    """Update an existing realized PnL record."""
    body = await request.json()
    record = update_pnl_record(record_id, body)
    if not record:
        raise HTTPException(status_code=404, detail="실현손익 기록을 찾을 수 없습니다.")
    return {"message": "매도 실현손익이 수정되었습니다.", "record": record}


@app.delete("/api/realized-pnl/{record_id}")
async def remove_realized_pnl(record_id: str) -> dict:
    """Delete a realized PnL record."""
    ok = delete_pnl_record(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="실현손익 기록을 찾을 수 없습니다.")
    return {"message": "실현손익 기록이 삭제되었습니다."}


@app.post("/api/realized-pnl/clear")
async def clear_realized_pnl_endpoint() -> dict:
    """Clear all realized PnL records."""
    clear_pnl_records()
    return {"message": "모든 매도 실현손익 기록이 삭제되었습니다."}


@app.post("/api/holdings/clear")
async def clear_holdings_endpoint() -> dict:
    """Clear all portfolio holdings."""
    data = read_portfolio()
    data["holdings"] = []
    write_portfolio(data)
    return {"message": "모든 보유종목이 삭제되었습니다."}


@app.post("/api/import-realized-pnl")
async def import_realized_pnl_endpoint(file: UploadFile = File(...)) -> dict:
    """Import realized PnL records from Excel or CSV."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="업로드할 파일을 선택하세요.")
    contents = await file.read()
    full = get_dashboard()
    fx_rate = full.get("fx_rates", {}).get("USD", 1385.0)
    try:
        records = import_pnl_file_data(contents, file.filename, fx_rate=fx_rate)
        return {
            "message": f"총 {len(records)}건의 실현손익 내역을 가져왔습니다.",
            "count": len(records),
            "records": records,
        }
    except Exception as e:
        logger.exception("실현손익 파일 가져오기 실패")
        raise HTTPException(status_code=400, detail=f"실현손익 파일 처리 실패: {e}")


@app.post("/api/realized-pnl/recalculate-fx")
async def recalculate_realized_pnl_fx_endpoint() -> dict:
    """Recalculate historical FX rates and KRW amounts for all USD realized PnL records."""
    count = recalculate_pnl_historical_fx()
    return {
        "message": f"총 {count}건의 달러 실현손익 내역을 매도일자 기준 환율 및 환차손익으로 재계산했습니다.",
        "count": count,
    }


@app.get("/api/sample/realized-pnl")
async def download_sample_pnl():
    """Download sample Excel file for realized profit/loss tracking."""
    p = ROOT_DIR / "data" / "샘플_매도실현손익.xlsx"
    if not p.exists():
        p = ROOT_DIR / "샘플_매도실현손익.xlsx"
    if not p.exists():
        raise HTTPException(status_code=404, detail="샘플_매도실현손익.xlsx 파일을 찾을 수 없습니다.")
    return FileResponse(
        path=str(p),
        filename="샘플_매도실현손익.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/status")
async def status() -> dict:
    return {
        "kb_configured": KBOpenAPI().configured,
        "toss_configured": TossOpenAPI().configured,
        "namoo_configured": NhPlugOpenAPI().configured,
        "storage": "local",
    }


# ---------------------------------------------------------------------------
# Family accounts API
# ---------------------------------------------------------------------------

@app.get("/api/accounts")
async def get_accounts(group: str = "All", owner: str = "모두") -> dict:
    """Return accounts filtered by family_group and aggregated summary."""
    full = get_dashboard()
    accounts = full.get("accounts", [])
    filtered = [a for a in accounts
                if (owner == "모두" or a.get("owner", "모두") == owner)
                and (group == "All" or a.get("family_group", "All") == group)]
    total_stock_value = sum(a.get("stock_value_krw", 0) for a in filtered)
    total_cash = sum(a.get("cash_krw", 0) for a in filtered)
    total_value = total_stock_value + total_cash
    profit = sum(a.get("profit_krw", 0) for a in filtered)
    holding_count = sum(a.get("holding_count", 0) for a in filtered)
    return {
        "summary": {
            "total_value_krw": total_value,
            "total_stock_value_krw": total_stock_value,
            "total_cash_krw": total_cash,
            "profit_krw": profit,
            "return_rate": profit / total_stock_value * 100 if total_stock_value else 0,
            "holding_count": holding_count,
            "account_count": len(filtered),
        },
        "accounts": filtered,
        "holdings": full.get("holdings", []),
        "fx_rates": full.get("fx_rates", {}),
        "currency_summary": full.get("currency_summary", {}),
        "classifications": full.get("classifications", []),
        "updated_at": full.get("updated_at"),
    }


@app.post("/api/accounts")
async def create_account(request: Request) -> dict:
    """Create a new account entry."""
    import uuid
    body = await request.json()
    broker = (body.get("broker") or "").strip()
    account_name = (body.get("account_name") or body.get("name") or "").strip()
    owner = (body.get("owner") or "모두").strip()
    if not broker or not account_name:
        raise HTTPException(status_code=400, detail="증권사와 계좌 이름은 필수입니다.")
    data = read_portfolio()
    new_account = {
        "id": str(uuid.uuid4()),
        "broker": broker,
        "name": account_name,
        "owner": owner,
        "family_group": "All",
        "market_value_krw": 0,
        "stock_value_krw": 0,
        "cash_krw": 0,
        "cash_usd": 0,
        "cash_total_krw": 0,
        "profit_krw": 0,
        "holding_count": 0,
    }
    data.setdefault("accounts", []).append(new_account)
    write_portfolio(data)
    return {"message": f"계좌 '{broker} - {account_name}'이(가) 추가되었습니다.", **new_account}


# ---------------------------------------------------------------------------
# Family members CRUD API
# ---------------------------------------------------------------------------
DEFAULT_FAMILY_MEMBERS = ["아빠", "엄마", "자녀"]

def get_family_members(data: dict) -> list:
    return data.get("settings", {}).get("family_members", list(DEFAULT_FAMILY_MEMBERS))

@app.get("/api/family-members")
async def list_family_members() -> dict:
    data = read_portfolio()
    return {"members": get_family_members(data)}

@app.post("/api/family-members")
async def add_family_member(request: Request) -> dict:
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "이름을 입력해 주세요.")
    data = read_portfolio()
    members = get_family_members(data)
    if name in members:
        raise HTTPException(409, "이미 존재하는 이름입니다.")
    members.append(name)
    data.setdefault("settings", {})["family_members"] = members
    write_portfolio(data)
    return {"members": members, "message": f"'{name}' 구성원을 추가했습니다."}

@app.put("/api/family-members/{old_name}")
async def rename_family_member(old_name: str, request: Request) -> dict:
    body = await request.json()
    new_name = (body.get("name") or "").strip()
    if not new_name:
        raise HTTPException(400, "새 이름을 입력해 주세요.")
    data = read_portfolio()
    members = get_family_members(data)
    if old_name not in members:
        raise HTTPException(404, "구성원을 찾지 못했습니다.")
    if new_name in members and new_name != old_name:
        raise HTTPException(409, "이미 존재하는 이름입니다.")
    members = [new_name if m == old_name else m for m in members]
    data.setdefault("settings", {})["family_members"] = members
    # Update all accounts with old_name owner -> new_name
    for acct in data.get("accounts", []):
        if acct.get("owner") == old_name:
            acct["owner"] = new_name
    write_portfolio(data)
    return {"members": members, "message": f"'{old_name}' -> '{new_name}'으로 이름을 변경했습니다."}

@app.delete("/api/family-members/{member_name}")
async def delete_family_member(member_name: str) -> dict:
    data = read_portfolio()
    members = get_family_members(data)
    if member_name not in members:
        raise HTTPException(404, "구성원을 찾지 못했습니다.")
    members = [m for m in members if m != member_name]
    data.setdefault("settings", {})["family_members"] = members
    # Reset owner on accounts that belonged to deleted member
    for acct in data.get("accounts", []):
        if acct.get("owner") == member_name:
            acct["owner"] = "모두"
    write_portfolio(data)
    return {"members": members, "message": f"'{member_name}' 구성원을 삭제했습니다."}


@app.on_event("startup")
async def startup_event() -> None:
    pass


@app.get("/api/market-overview")
async def market_overview() -> dict:
    return await fetch_market_overview()

@app.post("/api/holdings", status_code=201)
async def create_holding(payload: HoldingCreate) -> dict:
    data = read_portfolio()
    account_id = get_or_add_account(data, payload.broker.strip(), payload.account_name.strip(), "manual")
    item = normalize_holding(payload.model_dump(), account_id, payload.broker.strip(), payload.account_name.strip(), "manual")
    # propagate owner to account
    owner_val = getattr(payload, "owner", "모두") or "모두"
    for acct in data.get("accounts", []):
        if acct.get("id") == account_id:
            acct["owner"] = owner_val
            break
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
    owner_val = str(payload.get("owner") or "").strip()
    if owner_val:
        account["owner"] = owner_val
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



@app.get("/api/export")
async def export_data():
    """포트폴리오 전체 데이터를 JSON 파일로 다운로드"""
    import json
    from app.services.portfolio import read_portfolio
    from app.services.asset_records import read_asset_records
    from app.services.dividend_records import read_dividend_records
    from app.services.pnl_records import read_pnl_records

    bundle = {
        "version": "2.0",
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "portfolio": read_portfolio(),
        "asset_records": read_asset_records(),
        "dividend_records": read_dividend_records(),
        "realized_pnl_records": read_pnl_records(),
    }
    content = json.dumps(bundle, ensure_ascii=False, indent=2)
    from starlette.responses import Response
    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"asset-dashboard_{today_str}.json"
    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/import-backup")
async def import_backup(file: UploadFile = File(...)) -> dict:
    """백업 JSON 파일에서 데이터 복원"""
    import json
    from app.services.portfolio import write_portfolio
    from app.services.asset_records import write_asset_records
    from app.services.dividend_records import write_dividend_records
    from app.services.pnl_records import write_pnl_records

    try:
        raw = await file.read()
        bundle = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(400, f"JSON 파싱 실패: {exc}") from exc

    if "portfolio" not in bundle and "asset_records" not in bundle:
        raise HTTPException(400, "유효한 백업 파일이 아닙니다.")

    msgs = []
    if "portfolio" in bundle:
        write_portfolio(bundle["portfolio"])
        msgs.append("포트폴리오")
    if "asset_records" in bundle:
        write_asset_records(bundle["asset_records"])
        msgs.append("자산기록")
    if "dividend_records" in bundle:
        write_dividend_records(bundle["dividend_records"])
        msgs.append("배당내역")
    if "realized_pnl_records" in bundle:
        write_pnl_records(bundle["realized_pnl_records"])
        msgs.append("매도실현손익")

    return {"message": f"{', '.join(msgs)} 데이터를 복원했습니다."}

@app.post("/api/demo")
async def load_demo() -> dict:
    seed_demo()
    return {"message": "예시 데이터를 불러왔습니다."}


@app.post("/api/clear")
async def clear_all() -> dict:
    clear_portfolio()
    return {"message": "저장된 보유내역을 모두 지웠습니다."}


@app.get("/api/asset-records")
async def get_asset_records(owner: str = "") -> dict:
    records = list_asset_records()
    if owner:
        # "모두" 포함 항상 owner 필드로 필터링
        records = [r for r in records if (r.get("owner") or "모두") == owner]
    return {"records": records}



@app.post("/api/asset-records")
async def create_asset_record(payload: dict) -> dict:
    payload["owner"] = payload.get("owner") or "모두"
    record = upsert_asset_record(payload, by_date=bool(payload.get("date")))
    return {"message": "자산기록을 저장했습니다.", "record": record}


@app.put("/api/asset-records/{record_id}")
async def update_asset_record(record_id: str, payload: dict) -> dict:
    payload["id"] = record_id
    if "owner" not in payload or not payload["owner"]:
        payload["owner"] = "모두"
    record = upsert_asset_record(payload)
    return {"message": "자산기록을 수정했습니다.", "record": record}


@app.delete("/api/asset-records/{record_id}")
async def remove_asset_record(record_id: str) -> dict:
    if not delete_asset_record(record_id):
        raise HTTPException(404, "자산기록을 찾지 못했습니다.")
    return {"message": "자산기록을 삭제했습니다."}


@app.post("/api/asset-records/snapshot")
async def snapshot_asset_record(request: Request) -> dict:
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
    rate = await fetch_fx_rate_usd_krw()
    data = read_portfolio()
    data["settings"]["fx_rates"]["USD"] = rate
    now_str = datetime.now().astimezone().isoformat(timespec="seconds")
    data["settings"]["fx_info"] = {"source": "실시간 웹 환율", "rate": rate, "updated_at": now_str}
    data["settings"]["fx_updated_at"] = now_str
    write_portfolio(data)
    return {"message": f"실시간 환율(USD/KRW: {rate:,.1f}원)을 반영했습니다.", "rate": rate}


@app.post("/api/refresh-prices")
async def refresh_prices() -> dict:
    data = read_portfolio()
    if not data["holdings"]:
        raise HTTPException(400, "갱신할 보유종목이 없습니다.")

    # 네이버페이 증권 & 야후 파이낸스 & 웹 실시간 환율 병렬 직접 갱신 (토큰 불필요)
    res = await refresh_all_holdings_prices(data["holdings"])
    prices = res.get("prices", {})
    daily_changes = res.get("daily_changes", {})
    period_rates = res.get("period_rates", {})
    fx_rate = res.get("fx_rate", 1385.0)

    # 포트폴리오 업데이트
    now_str = datetime.now().astimezone().isoformat(timespec="seconds")
    for holding in data["holdings"]:
        hid = holding["id"]
        if hid in prices and prices[hid] > 0:
            holding["current_price"] = prices[hid]
            holding["price_updated_at"] = now_str

    if daily_changes:
        data["settings"].setdefault("daily_price_changes", {}).update(daily_changes)
    if period_rates:
        data["settings"].setdefault("period_rates", {}).update(period_rates)
    if fx_rate and fx_rate > 0:
        data["settings"].setdefault("exchange_rates", {})["USD"] = fx_rate
        data["settings"]["fx_updated_at"] = now_str

    write_portfolio(data)
    return {
        "message": f"전체 {len(prices)}개 종목 시세 및 환율({fx_rate:,.1f}원)을 갱신했습니다.",
        "count": len(prices),
        "fx_rate": fx_rate,
        "warnings": [],
    }

@app.get("/api/stock-chart/{code}")
async def get_stock_chart(code: str, period: str = "1M") -> dict:
    return await fetch_stock_chart_data(code, period)


@app.post("/api/sync/all")
async def sync_all_accounts() -> dict:
    results = []
    errors = []
    
    # 1. KB
    kb = KBOpenAPI()
    if kb.configured:
        try:
            r = await sync_kb()
            results.append(r.get("message", "KB 동기화 완료"))
        except Exception as e:
            errors.append(f"KB: {e}")
            
    # 2. Toss
    toss = TossOpenAPI()
    if toss.configured:
        try:
            r = await sync_toss()
            results.append(r.get("message", "토스 동기화 완료"))
        except Exception as e:
            errors.append(f"토스: {e}")
            
    # 3. Namoo
    namoo = NhPlugOpenAPI()
    if namoo.configured:
        try:
            r = await sync_namoo()
            results.append(r.get("message", "나무 동기화 완료"))
        except Exception as e:
            errors.append(f"나무: {e}")
            
    if not results and not errors:
        return {"message": "설정된 증권사 연동 계정이 없습니다. .env 설정을 확인하세요.", "synced": 0}
        
    msg = " / ".join(results)
    if errors:
        msg += f" (오류: {', '.join(errors)})"
    return {"message": msg, "synced": len(results), "errors": errors}
