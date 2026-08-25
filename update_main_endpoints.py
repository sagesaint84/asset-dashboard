#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_main_endpoints.py
- Remove startup Toss API call completely
- Update /api/fx/refresh to use web finance (no Toss dependency)
- Add /api/stock-chart/{code}
- Add /api/sync/all
"""

with open("app/main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

# 1. Remove background startup toss call
old_startup = """@app.on_event("startup")
async def startup_event() -> None:
    toss = TossOpenAPI()
    if toss.configured:
        data = read_portfolio()
        syms = list({str(h.get("code", "")).upper() for h in data.get("holdings", []) if h.get("code")})
        if syms:
            asyncio.create_task(toss.get_multi_period_changes(syms))"""

new_startup = """@app.on_event("startup")
async def startup_event() -> None:
    pass"""

if old_startup in main_code:
    main_code = main_code.replace(old_startup, new_startup, 1)
    print("OK: Removed startup Toss API call")

# 2. Update /api/fx/refresh to use web finance
old_fx_refresh = """@app.post("/api/fx/refresh")
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
    return {"message": f"토스증권 실시간 환율({updated})을 반영했습니다.", "quotes": quotes, "warnings": warnings}"""

new_fx_refresh = """@app.post("/api/fx/refresh")
async def refresh_fx_rate() -> dict:
    rate = await fetch_fx_rate_usd_krw()
    data = read_portfolio()
    data["settings"]["fx_rates"]["USD"] = rate
    now_str = datetime.now().astimezone().isoformat(timespec="seconds")
    data["settings"]["fx_info"] = {"source": "실시간 웹 환율", "rate": rate, "updated_at": now_str}
    data["settings"]["fx_updated_at"] = now_str
    write_portfolio(data)
    return {"message": f"실시간 환율(USD/KRW: {rate:,.1f}원)을 반영했습니다.", "rate": rate}"""

if old_fx_refresh in main_code:
    main_code = main_code.replace(old_fx_refresh, new_fx_refresh, 1)
    print("OK: Updated /api/fx/refresh to use web finance")

# 3. Add /api/stock-chart/{code} and /api/sync/all if not present
if "@app.get(\"/api/stock-chart/{code}\")" not in main_code:
    endpoints_to_add = """

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
"""
    main_code = main_code.strip() + endpoints_to_add
    print("OK: Added /api/stock-chart/{code} and /api/sync/all")

with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(main_code)

print("main.py updated successfully!")
