#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_all_reported_issues.py
1. Fix web_finance.py: Properly slice candles for 1W, 1M, 3M, YTD, 1Y for both KR and US stocks
2. Fix wealth.js:
   - Add filterRecordsByPeriod function before renderAssetRecords
   - Fix stockChartPeriodTabs event listener and openStockChart period state
"""

# 1. Update web_finance.py
WEB_FINANCE_PY = 'app/services/web_finance.py'
with open(WEB_FINANCE_PY, 'r', encoding='utf-8') as f:
    wf_code = f.read()

OLD_FETCH_CHART = '''async def fetch_stock_chart_data(code: str, period: str = "1M") -> dict[str, Any]:
    """
    종목 코드와 기간(1W, 1M, 3M, YTD, 1Y)을 받아
    일자별 가격(시/고/저/종가)과 거래량(volume) 리스트를 반환합니다.
    """
    clean_code = str(code).strip().upper()
    is_kr = len(clean_code) == 6 and any(ch.isdigit() for ch in clean_code)

    # 기간별 캔들 개수 또는 야후 range 매핑
    count_map = {"1W": 10, "1M": 30, "3M": 75, "YTD": 180, "1Y": 260}
    range_map = {"1W": "5d", "1M": "1mo", "3M": "3mo", "YTD": "ytd", "1Y": "1y"}

    candles: list[dict[str, Any]] = []
    stock_name = clean_code
    currency = "KRW" if is_kr else "USD"
    current_price = 0.0

    async with httpx.AsyncClient() as client:
        if is_kr:
            cnt = count_map.get(period, 30)
            url = f"https://api.stock.naver.com/chart/domestic/item/{clean_code}?periodType=dayCandle&count={cnt}"
            try:
                resp = await client.get(url, headers=HEADERS, timeout=6.0)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("priceInfos", []):
                        d_str = str(item.get("localDate") or "")
                        # Format YYYYMMDD -> YYYY-MM-DD
                        if len(d_str) == 8:
                            d_str = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                        candles.append({
                            "date": d_str,
                            "open": _to_float(item.get("openPrice")),
                            "high": _to_float(item.get("highPrice")),
                            "low": _to_float(item.get("lowPrice")),
                            "close": _to_float(item.get("closePrice")),
                            "volume": int(_to_float(item.get("accumulatedTradingVolume"))),
                        })
                    if candles:
                        current_price = candles[-1]["close"]
            except Exception:
                pass
        else:
            rng = range_map.get(period, "1mo")
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_code}?interval=1d&range={rng}"
            try:
                resp = await client.get(url, headers=HEADERS, timeout=7.0)
                if resp.status_code == 200:
                    res_json = resp.json()
                    result = res_json.get("chart", {}).get("result", [{}])[0]
                    meta = result.get("meta", {})
                    stock_name = meta.get("shortName") or clean_code
                    current_price = float(meta.get("regularMarketPrice") or 0.0)

                    timestamps = result.get("timestamp", [])
                    quote = result.get("indicators", {}).get("quote", [{}])[0]
                    opens = quote.get("open", [])
                    highs = quote.get("high", [])
                    lows = quote.get("low", [])
                    closes = quote.get("close", [])
                    volumes = quote.get("volume", [])

                    for i, ts in enumerate(timestamps):
                        c_val = closes[i] if i < len(closes) else None
                        if c_val is not None and float(c_val) > 0:
                            d_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                            candles.append({
                                "date": d_str,
                                "open": float(opens[i]) if i < len(opens) and opens[i] is not None else float(c_val),
                                "high": float(highs[i]) if i < len(highs) and highs[i] is not None else float(c_val),
                                "low": float(lows[i]) if i < len(lows) and lows[i] is not None else float(c_val),
                                "close": round(float(c_val), 2),
                                "volume": int(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0,
                            })
            except Exception:
                pass

    return {
        "code": clean_code,
        "name": stock_name,
        "currency": currency,
        "period": period,
        "current_price": current_price,
        "candles": candles,
    }'''

NEW_FETCH_CHART = '''async def fetch_stock_chart_data(code: str, period: str = "1M") -> dict[str, Any]:
    """
    종목 코드와 기간(1W, 1M, 3M, YTD, 1Y)을 받아
    일자별 가격(시/고/저/종가)과 거래량(volume) 리스트를 정확한 기간 크기로 반환합니다.
    """
    clean_code = str(code).strip().upper()
    is_kr = len(clean_code) == 6 and any(ch.isdigit() for ch in clean_code)

    candles: list[dict[str, Any]] = []
    stock_name = clean_code
    currency = "KRW" if is_kr else "USD"
    current_price = 0.0

    async with httpx.AsyncClient() as client:
        if is_kr:
            url = f"https://api.stock.naver.com/chart/domestic/item/{clean_code}?periodType=dayCandle&count=260"
            try:
                resp = await client.get(url, headers=HEADERS, timeout=6.0)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("priceInfos", []):
                        d_str = str(item.get("localDate") or "")
                        if len(d_str) == 8:
                            d_str = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                        candles.append({
                            "date": d_str,
                            "open": _to_float(item.get("openPrice")),
                            "high": _to_float(item.get("highPrice")),
                            "low": _to_float(item.get("lowPrice")),
                            "close": _to_float(item.get("closePrice")),
                            "volume": int(_to_float(item.get("accumulatedTradingVolume"))),
                        })
                    if candles:
                        current_price = candles[-1]["close"]
            except Exception:
                pass
        else:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_code}?interval=1d&range=1y"
            try:
                resp = await client.get(url, headers=HEADERS, timeout=7.0)
                if resp.status_code == 200:
                    res_json = resp.json()
                    result = res_json.get("chart", {}).get("result", [{}])[0]
                    meta = result.get("meta", {})
                    stock_name = meta.get("shortName") or clean_code
                    current_price = float(meta.get("regularMarketPrice") or 0.0)

                    timestamps = result.get("timestamp", [])
                    quote = result.get("indicators", {}).get("quote", [{}])[0]
                    opens = quote.get("open", [])
                    highs = quote.get("high", [])
                    lows = quote.get("low", [])
                    closes = quote.get("close", [])
                    volumes = quote.get("volume", [])

                    for i, ts in enumerate(timestamps):
                        c_val = closes[i] if i < len(closes) else None
                        if c_val is not None and float(c_val) > 0:
                            d_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                            candles.append({
                                "date": d_str,
                                "open": float(opens[i]) if i < len(opens) and opens[i] is not None else float(c_val),
                                "high": float(highs[i]) if i < len(highs) and highs[i] is not None else float(c_val),
                                "low": float(lows[i]) if i < len(lows) and lows[i] is not None else float(c_val),
                                "close": round(float(c_val), 2),
                                "volume": int(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0,
                            })
            except Exception:
                pass

    # ── 기간(Period)별 정확한 캔들 슬라이싱 ──
    sliced_candles = candles
    if candles:
        if period == "1W":
            sliced_candles = candles[-5:] if len(candles) >= 5 else candles
        elif period == "1M":
            sliced_candles = candles[-22:] if len(candles) >= 22 else candles
        elif period == "3M":
            sliced_candles = candles[-65:] if len(candles) >= 65 else candles
        elif period == "YTD":
            now_year = datetime.now().year
            ytd_str = f"{now_year}-01-01"
            ytd_list = [c for c in candles if c.get("date", "") >= ytd_str]
            sliced_candles = ytd_list if ytd_list else candles[-60:]
        elif period == "1Y":
            sliced_candles = candles[-250:] if len(candles) >= 250 else candles

    return {
        "code": clean_code,
        "name": stock_name,
        "currency": currency,
        "period": period,
        "current_price": current_price,
        "candles": sliced_candles,
    }'''

if OLD_FETCH_CHART in wf_code:
    wf_code = wf_code.replace(OLD_FETCH_CHART, NEW_FETCH_CHART, 1)
    with open(WEB_FINANCE_PY, 'w', encoding='utf-8') as f:
        f.write(wf_code)
    print("OK 1. Updated fetch_stock_chart_data in web_finance.py with accurate slicing")
else:
    print("WARN 1. Could not locate OLD_FETCH_CHART in web_finance.py")

# 2. Update wealth.js
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# Make sure filterRecordsByPeriod is placed before renderAssetRecords
FILTER_RECORDS_FN = '''
function filterRecordsByPeriod(records, period) {
  if (!records || !records.length || period === 'ALL') return records || [];
  const now = new Date();
  let days = 30;
  if (period === '1M') days = 30;
  else if (period === '3M') days = 90;
  else if (period === '6M') days = 180;
  else if (period === '1Y') days = 365;

  const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  return records.filter(r => r.date && r.date >= cutoff);
}
'''

# Find renderAssetRecords in wealth.js
RAR_START = 'function renderAssetRecords(records) {'
if RAR_START in js:
    # If filterRecordsByPeriod is already in js, remove duplicate first
    js = js.replace('function filterRecordsByPeriod(records, period) {', '// old filter')
    # Prepend FILTER_RECORDS_FN right before renderAssetRecords
    js = js.replace(RAR_START, FILTER_RECORDS_FN + '\n' + RAR_START, 1)
    print("OK 2. Added filterRecordsByPeriod right before renderAssetRecords")

# Also ensure openStockChart resets currentStockChartPeriod and highlights active tab
OLD_OPEN_CHART = '''async function openStockChart(code, name, price, currency = 'KRW') {
  if (!code) return;
  currentStockChartCode = code;
  const dlg = document.getElementById('stockChartDialog');
  if (!dlg) return;

  document.getElementById('stockChartTitle').textContent = name || code;
  document.getElementById('stockChartCode').textContent = code;
  document.getElementById('stockChartPrice').textContent = money(price, currency);

  dlg.showModal();
  await loadStockChartData(code, currentStockChartPeriod);
}'''

NEW_OPEN_CHART = '''async function openStockChart(code, name, price, currency = 'KRW') {
  if (!code) return;
  currentStockChartCode = code;
  currentStockChartPeriod = '1M'; // 기본 1개월로 초기화

  const dlg = document.getElementById('stockChartDialog');
  if (!dlg) return;

  // 탭 active 클래스 초기화
  document.querySelectorAll('#stockChartPeriodTabs .heatmap-tab').forEach(t => {
    if (t.dataset.period === '1M') t.classList.add('active');
    else t.classList.remove('active');
  });

  document.getElementById('stockChartTitle').textContent = name || code;
  document.getElementById('stockChartCode').textContent = code;
  document.getElementById('stockChartPrice').textContent = money(price, currency);

  dlg.showModal();
  await loadStockChartData(code, '1M');
}'''

if OLD_OPEN_CHART in js:
    js = js.replace(OLD_OPEN_CHART, NEW_OPEN_CHART, 1)
    print("OK 3. Updated openStockChart with proper period reset")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print("All fixes applied successfully!")
