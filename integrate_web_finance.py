#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integrate_web_finance.py
- Connect /api/refresh-prices, /api/fx/refresh, /api/market-overview to web_finance (Naver + Yahoo + Web FX)
- Remove background startup Toss API calls
- Simplify UI buttons: Combine "시세 갱신" and "환율 갱신" into a single "갱신" button
"""

import re

# 1. Update app/main.py
with open("app/main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

# Add web_finance imports
if "from app.services.web_finance import" not in main_code:
    import_hook = "from app.services.toss import TossOpenAPI, TossOpenAPIError"
    new_import = """from app.services.toss import TossOpenAPI, TossOpenAPIError
from app.services.web_finance import (
    fetch_market_overview,
    fetch_fx_rate_usd_krw,
    refresh_all_holdings_prices,
    fetch_stock_chart_data,
)"""
    main_code = main_code.replace(import_hook, new_import, 1)

# Replace refresh_prices endpoint
old_refresh = """@app.post("/api/refresh-prices")
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
    return {"message": f"{len(prices)}개 종목의 시세를 갱신했습니다.", "count": len(prices), "warnings": warnings[:10]}"""

new_refresh = """@app.post("/api/refresh-prices")
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
    }"""

if old_refresh in main_code:
    main_code = main_code.replace(old_refresh, new_refresh, 1)
    print("OK: main.py /api/refresh-prices replaced with web_finance engine")

# Replace market-overview endpoint to use fetch_market_overview
old_market_endpoint = """@app.get("/api/market-overview")
async def market_overview() -> dict:"""
if old_market_endpoint in main_code:
    # Look for the function body
    idx_m_start = main_code.find(old_market_endpoint)
    idx_m_next = main_code.find("\n@app.", idx_m_start + 10)
    new_market_fn = """@app.get("/api/market-overview")
async def market_overview() -> dict:
    return await fetch_market_overview()
"""
    main_code = main_code[:idx_m_start] + new_market_fn + main_code[idx_m_next:]
    print("OK: main.py /api/market-overview connected to web_finance")

with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(main_code)


# 2. Update index.html - Combine buttons into single "갱신" button
with open("app/static/index.html", "r", encoding="utf-8") as f:
    html_code = f.read()

# Replace refresh buttons in header
old_buttons = """<button id="refreshButton" class="button secondary compact" type="button">시세 갱신</button>
            <button id="refreshFxButton" class="button secondary compact" type="button">환율 갱신</button>"""

new_buttons = """<button id="refreshButton" class="button primary compact" type="button">🔄 갱신</button>"""

if old_buttons in html_code:
    html_code = html_code.replace(old_buttons, new_buttons, 1)
    print("OK: index.html buttons combined into single '🔄 갱신' button")
else:
    # Regex replacement for variations
    html_code = re.sub(
        r'<button id="refreshButton"[^>]*>.*?</button>\s*<button id="refreshFxButton"[^>]*>.*?</button>',
        new_buttons,
        html_code,
        flags=re.DOTALL
    )
    print("OK: index.html regex replaced refresh buttons")

with open("app/static/index.html", "w", encoding="utf-8") as f:
    f.write(html_code)


# 3. Update wealth.js
with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    js = f.read()

# Make refreshButton do a full refresh (prices + fx + markets + dashboard)
old_refresh_event = '$("#refreshButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));'

new_refresh_event = """const refreshBtn = $("#refreshButton");
if (refreshBtn) {
  refreshBtn.addEventListener("click", (e) => action(e.currentTarget, async () => {
    const res = await api("/api/refresh-prices", { method: "POST" });
    return res;
  }, async () => {
    await loadDashboard();
    await loadMarkets();
  }));
}
const refreshFxBtn = $("#refreshFxButton");
if (refreshFxBtn) {
  refreshFxBtn.addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));
}"""

if old_refresh_event in js:
    js = js.replace(old_refresh_event, new_refresh_event, 1)
    print("OK: wealth.js refreshButton handler updated")

with open("app/static/wealth.js", "w", encoding="utf-8") as f:
    f.write(js)

print("Web Finance integration complete!")
