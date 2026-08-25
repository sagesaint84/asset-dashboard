#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_web_finance_to_main.py
- Connect /api/refresh-prices to web_finance service
- Connect /api/fx/refresh to web_finance service
- Connect /api/market-overview to web_finance service
- Clean up /api/refreshButton in wealth.js
"""

MAIN_PY = 'app/main.py'
with open(MAIN_PY, 'r', encoding='utf-8') as f:
    main_code = f.read()

# Replace market-overview
OLD_MARKET_OVERVIEW_START = '@app.get("/api/market-overview")'
# Find the end of market-overview (before @app.post("/api/accounts"))
idx_mkt = main_code.find(OLD_MARKET_OVERVIEW_START)
idx_acct = main_code.find('@app.get("/api/accounts")', idx_mkt)

NEW_MARKET_OVERVIEW = '''@app.get("/api/market-overview")
async def market_overview() -> dict:
    from app.services.web_finance import get_web_market_overview, fetch_fx_rate_usd_krw
    try:
        markets = await get_web_market_overview()
        rate = await fetch_fx_rate_usd_krw()
    except Exception as exc:
        raise HTTPException(400, f"시장 스냅샷 조회 실패: {exc}") from exc

    data = read_portfolio()
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

    if prev_rate and prev_rate > 0:
        fx_change = rate - prev_rate
        fx_change_rate = fx_change / prev_rate * 100
    else:
        fx_change = 0.0
        fx_change_rate = 0.0

    return {
        "markets": markets,
        "exchange_rate": {
            "currency": "USD",
            "base_currency": "KRW",
            "rate": rate,
            "change_price": fx_change,
            "change_rate": fx_change_rate,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    }


'''

if idx_mkt != -1 and idx_acct != -1:
    main_code = main_code[:idx_mkt] + NEW_MARKET_OVERVIEW + main_code[idx_acct:]
    print("OK 1. Replaced market_overview with Web Finance")
else:
    print(f"WARN 1. Could not locate market_overview bounds (mkt={idx_mkt}, acct={idx_acct})")

# Replace fx/refresh & refresh-prices
OLD_REFRESH_START = '@app.post("/api/fx/refresh")'
idx_ref = main_code.find(OLD_REFRESH_START)
if idx_ref == -1:
    idx_ref = main_code.find('from app.services.google_finance import')

NEW_REFRESH_ENDPOINTS = '''@app.post("/api/fx/refresh")
async def refresh_fx_rate() -> dict:
    from app.services.web_finance import fetch_fx_rate_usd_krw
    data = read_portfolio()
    try:
        rate = await fetch_fx_rate_usd_krw()
    except Exception as exc:
        raise HTTPException(400, f"실시간 환율 조회 실패: {exc}") from exc

    data["settings"].setdefault("fx_rates", {})["USD"] = rate
    data["settings"]["fx_rates"]["KRW"] = 1.0
    quotes = {
        "USD": {
            "currency": "USD",
            "base_currency": "KRW",
            "rate": rate,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
    }
    data["settings"]["fx_info"] = {"source": "네이버/야후 파이낸스 실시간 환율", "quotes": quotes, **quotes["USD"]}
    write_portfolio(data)
    return {"message": f"실시간 환율(USD/KRW: {rate:,.2f}원)을 반영했습니다.", "quotes": quotes, "warnings": []}


@app.post("/api/refresh-prices")
async def refresh_prices() -> dict:
    from app.services.web_finance import refresh_all_holdings_prices
    data = read_portfolio()
    if not data["holdings"]:
        raise HTTPException(400, "갱신할 보유종목이 없습니다.")

    try:
        result = await refresh_all_holdings_prices(data["holdings"])
    except Exception as exc:
        raise HTTPException(400, f"시세 갱신 중 오류가 발생했습니다: {exc}") from exc

    prices = result.get("prices", {})
    daily_changes = result.get("daily_changes", {})
    period_rates = result.get("period_rates", {})
    fx_rate = result.get("fx_rate", 0.0)

    # 환율 반영
    if fx_rate > 0:
        data["settings"].setdefault("fx_rates", {})["USD"] = fx_rate
        data["settings"]["fx_rates"]["KRW"] = 1.0

    # 다중 기간 등락률 및 일간 등락률 반영
    if daily_changes:
        data["settings"].setdefault("daily_price_changes", {}).update(daily_changes)
    if period_rates:
        data["settings"].setdefault("period_rates", {}).update(period_rates)

    now_str = datetime.now().astimezone().isoformat(timespec="seconds")
    for holding in data["holdings"]:
        if holding["id"] in prices:
            holding["current_price"] = prices[holding["id"]]
            holding["price_updated_at"] = now_str

    write_portfolio(data)
    return {
        "message": f"네이버·야후 파이낸스로 {len(prices)}개 종목 시세 및 환율({fx_rate:,.2f}원)을 갱신했습니다.",
        "count": len(prices),
        "source": "web_finance",
        "warnings": [],
    }
'''

if idx_ref != -1:
    main_code = main_code[:idx_ref] + NEW_REFRESH_ENDPOINTS
    print("OK 2. Replaced fx/refresh and refresh-prices with Web Finance")
else:
    print("WARN 2. Could not find refresh endpoints start")

with open(MAIN_PY, 'w', encoding='utf-8') as f:
    f.write(main_code)

# 2. Update wealth.js refreshButton handler for simple one-click refresh
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js_code = f.read()

# Replace any multi-line refreshButton handler with clean one
OLD_REFRESH_PATTERN = '$("#refreshButton").addEventListener("click",'
idx_rb = js_code.find(OLD_REFRESH_PATTERN)
if idx_rb != -1:
    idx_rfb = js_code.find('$("#refreshFxButton")', idx_rb)
    if idx_rfb != -1:
        CLEAN_REFRESH = '$("#refreshButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" })));\n'
        js_code = js_code[:idx_rb] + CLEAN_REFRESH + js_code[idx_rfb:]
        print("OK 3. Cleaned up wealth.js refreshButton handler to simple one-click action")
    else:
        print("WARN 3. Could not find refreshFxButton anchor in wealth.js")
else:
    print("WARN 3. Could not find refreshButton in wealth.js")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js_code)

print("All Web Finance integration complete!")
