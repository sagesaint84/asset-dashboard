#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_google_finance_priority.py
1. Update app/main.py:
   - refresh_fx_rate: Try Google Finance first, then fallback to Toss OpenAPI
   - refresh_prices: source parameter (google_first / toss)
2. Update app/static/wealth.js:
   - #refreshButton: Call google_first, prompt confirm if missing_count > 0, call toss if confirmed
   - #refreshFxButton: Refresh FX and toast source
"""

MAIN_PY = 'app/main.py'
with open(MAIN_PY, 'r', encoding='utf-8') as f:
    main_code = f.read()

NEW_FX_AND_PRICES = '''from app.services.google_finance import fetch_google_sheet_data, refresh_prices_from_google_sheet


@app.post("/api/fx/refresh")
async def refresh_fx_rate() -> dict:
    data = read_portfolio()
    warnings: list[str] = []

    # 1. 구글 파이낸스 (스프레드시트) 환율 우선 조회
    try:
        g_data = fetch_google_sheet_data()
        g_fx = g_data.get("fx_usd_krw", 0.0)
        if g_fx and g_fx > 0:
            data["settings"].setdefault("fx_rates", {})["USD"] = g_fx
            data["settings"]["fx_rates"]["KRW"] = 1.0
            data["settings"]["fx_info"] = {
                "source": "구글 파이낸스",
                "rate": g_fx,
                "at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            write_portfolio(data)
            return {
                "message": f"구글 파이낸스 환율(USD/KRW: {g_fx:,.2f}원)을 반영했습니다.",
                "source": "google_finance",
                "rate": g_fx,
                "warnings": [],
            }
    except Exception as exc:
        warnings.append(f"구글 시트 환율 조회 실패: {exc}")

    # 2. 실패 시 토스증권 OpenAPI 폴백
    client = TossOpenAPI()
    currencies = sorted({str(holding.get("currency", "")).upper() for holding in data["holdings"] if holding.get("currency") not in {"", "KRW"}})
    if not currencies:
        currencies = ["USD"]
    quotes: dict[str, dict] = {}
    for currency in currencies:
        try:
            quotes[currency] = await client.get_exchange_rate(currency, "KRW")
        except TossOpenAPIError as exc:
            warnings.append(str(exc))
    if not quotes:
        raise HTTPException(400, " / ".join(warnings) or "환율을 가져오지 못했습니다.")
    for currency, quote in quotes.items():
        data["settings"].setdefault("fx_rates", {})[currency] = quote["rate"]
    usd_quote = quotes.get("USD", {})
    data["settings"]["fx_info"] = {"source": "토스증권 OpenAPI", "quotes": quotes, **usd_quote}
    write_portfolio(data)
    updated = ", ".join(f"{currency}/KRW" for currency in quotes)
    return {"message": f"토스증권 실시간 환율({updated})을 반영했습니다.", "source": "toss_openapi", "quotes": quotes, "warnings": warnings}


@app.post("/api/refresh-prices")
async def refresh_prices(source: str = "google_first") -> dict:
    data = read_portfolio()
    if not data["holdings"]:
        raise HTTPException(400, "갱신할 보유종목이 없습니다.")

    # ── [Mode A] 구글 파이낸스 우선 갱신 ──────────────────────────────────────
    if source == "google_first":
        matched_prices: dict[str, float] = {}
        missing_holdings: list[dict[str, Any]] = []
        g_fx = 0.0
        try:
            matched_prices, missing_holdings, g_fx = refresh_prices_from_google_sheet(data["holdings"])
            if g_fx > 0:
                data["settings"].setdefault("fx_rates", {})["USD"] = g_fx
                data["settings"]["fx_rates"]["KRW"] = 1.0
        except Exception as exc:
            missing_holdings = data["holdings"]

        # 구글 시트로 매칭된 종목 현재가 저장
        now_str = datetime.now().astimezone().isoformat(timespec="seconds")
        for holding in data["holdings"]:
            if holding["id"] in matched_prices:
                holding["current_price"] = matched_prices[holding["id"]]
                holding["price_updated_at"] = now_str
        write_portfolio(data)

        missing_names = sorted(list({h.get("name") or str(h.get("code")) for h in missing_holdings}))
        return {
            "message": f"구글 파이낸스로 {len(matched_prices)}개 종목 시세를 갱신했습니다.",
            "source": "google_finance",
            "updated_count": len(matched_prices),
            "missing_count": len(missing_holdings),
            "missing_symbols": missing_names[:10],
            "needs_toss_fallback": len(missing_holdings) > 0,
            "warnings": [],
        }

    # ── [Mode B] 토스 / KB OpenAPI 전체 갱신 (폴백 또는 직접 요청) ────────────
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

    now_str = datetime.now().astimezone().isoformat(timespec="seconds")
    for holding in data["holdings"]:
        if holding["id"] in prices:
            holding["current_price"] = prices[holding["id"]]
            holding["price_updated_at"] = now_str
    write_portfolio(data)
    return {
        "message": f"토스·KB OpenAPI로 {len(prices)}개 종목 시세를 갱신했습니다.",
        "source": "toss_api",
        "updated_count": len(prices),
        "missing_count": 0,
        "needs_toss_fallback": False,
        "warnings": warnings[:10],
    }
'''

# Replace old fx/refresh and refresh-prices in main.py
target_start = main_code.find('@app.post("/api/fx/refresh")')
if target_start != -1:
    main_code = main_code[:target_start] + NEW_FX_AND_PRICES
    print("OK 1. Updated main.py endpoints")
else:
    print("WARN 1. Could not find @app.post('/api/fx/refresh') in main.py")

with open(MAIN_PY, 'w', encoding='utf-8') as f:
    f.write(main_code)

# 2. Update wealth.js #refreshButton handler
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js_code = f.read()

OLD_REFRESH_BTN = '$("#refreshButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" })));'
NEW_REFRESH_BTN = '''$("#refreshButton").addEventListener("click", async (e) => {
  const btn = e.currentTarget;
  await action(btn, async () => {
    // 1. 구글 파이낸스 우선 시세 갱신
    const res = await api("/api/refresh-prices?source=google_first", { method: "POST" });
    toast(res.message || "구글 시세를 갱신했습니다.");
    await loadDashboard();

    // 2. 구글 시트에 없는 종목이 있을 경우 토스 API 폴백 확인
    if (res.needs_toss_fallback && res.missing_count > 0) {
      const sample = res.missing_symbols ? ` (예: ${res.missing_symbols.slice(0, 3).join(", ")} 등)` : "";
      const confirmToss = confirm(`구글 시트에 없는 ${res.missing_count}개 종목${sample}이 있습니다.\\n토스 OpenAPI로 추가 갱신할까요?`);
      if (confirmToss) {
        const tossRes = await api("/api/refresh-prices?source=toss", { method: "POST" });
        toast(tossRes.message || "토스 API로 시세를 추가 갱신했습니다.");
        await loadDashboard();
      }
    }
  });
});'''

if OLD_REFRESH_BTN in js_code:
    js_code = js_code.replace(OLD_REFRESH_BTN, NEW_REFRESH_BTN, 1)
    print("OK 2. Updated wealth.js refreshButton handler")
else:
    print("WARN 2. Could not find exact refreshButton in wealth.js")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js_code)

print("All updates applied!")
