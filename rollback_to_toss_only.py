#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rollback_to_toss_only.py
- Rollback app/main.py refresh-prices and fx/refresh to Toss OpenAPI only
- Rollback app/static/wealth.js refreshButton handler to Toss OpenAPI only
"""

# 1. Rollback app/main.py
MAIN_PY = 'app/main.py'
with open(MAIN_PY, 'r', encoding='utf-8') as f:
    main_code = f.read()

ORIGINAL_FX_AND_PRICES = '''@app.post("/api/fx/refresh")
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
        data["settings"].setdefault("fx_rates", {})[currency] = quote["rate"]
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
'''

target_start = main_code.find('from app.services.google_finance import')
if target_start == -1:
    target_start = main_code.find('@app.post("/api/fx/refresh")')

if target_start != -1:
    main_code = main_code[:target_start] + ORIGINAL_FX_AND_PRICES
    print("OK 1. Rolled back main.py to Toss OpenAPI only")
else:
    print("WARN 1. Could not find target in main.py")

with open(MAIN_PY, 'w', encoding='utf-8') as f:
    f.write(main_code)

# 2. Rollback app/static/wealth.js
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js_code = f.read()

ORIGINAL_REFRESH_BTN = '$("#refreshButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" })));'

# Find the multi-line new refresh button in wealth.js
btn_start = js_code.find('$("#refreshButton").addEventListener("click",')
if btn_start != -1:
    btn_end = js_code.find('$("#refreshFxButton")', btn_start)
    if btn_end != -1:
        js_code = js_code[:btn_start] + ORIGINAL_REFRESH_BTN + '\n' + js_code[btn_end:]
        print("OK 2. Rolled back wealth.js refreshButton handler")
    else:
        print("WARN 2. Could not find refreshFxButton in wealth.js")
else:
    print("WARN 2. Could not find refreshButton in wealth.js")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js_code)

print("Rollback complete!")
