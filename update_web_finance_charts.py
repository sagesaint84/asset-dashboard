#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_web_finance_charts.py
- Fix get_web_market_overview field mapping & series sparklines
- Add fetch_stock_chart_data for Naver (KR) & Yahoo (US) with volume & OHLC
"""

WEB_FINANCE_PY = 'app/services/web_finance.py'

NEW_CONTENT = '''from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def _to_float(val: Any) -> float:
    if val is None:
        return 0.0
    s = str(val).replace(",", "").replace("$", "").replace("₩", "").replace("%", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def calculate_period_changes(candles: list[dict[str, Any]], current_price: float) -> dict[str, float]:
    """
    일별 캔들 종가 리스트[{'date': 'YYYYMMDD', 'close': float}, ...]를 바탕으로
    1D, 1W, 1M, YTD, 1Y 수익률(%)을 계산합니다.
    """
    if not candles or current_price <= 0:
        return {"1D": 0.0, "1W": 0.0, "1M": 0.0, "YTD": 0.0, "1Y": 0.0}

    now_year = datetime.now().year
    ytd_target = f"{now_year - 1}1231"

    def find_close_at_index(offset: int) -> float:
        if len(candles) > offset:
            return float(candles[-(offset + 1)]["close"])
        return float(candles[0]["close"])

    close_1d = find_close_at_index(1) if len(candles) >= 2 else float(candles[-1]["close"])
    close_1w = find_close_at_index(5)
    close_1m = find_close_at_index(20)
    close_1y = find_close_at_index(240)

    close_ytd = float(candles[0]["close"])
    for c in reversed(candles):
        if c.get("date", "") <= ytd_target:
            close_ytd = float(c["close"])
            break

    def calc_rate(base_price: float) -> float:
        if base_price > 0:
            return round(((current_price - base_price) / base_price) * 100, 2)
        return 0.0

    return {
        "1D": calc_rate(close_1d),
        "1W": calc_rate(close_1w),
        "1M": calc_rate(close_1m),
        "YTD": calc_rate(close_ytd),
        "1Y": calc_rate(close_1y),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. 국내 주식 및 국내 상장 ETF (네이버 증권 웹 API)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_kr_stock_info(client: httpx.AsyncClient, code: str) -> dict[str, Any] | None:
    clean_code = str(code).strip().zfill(6)
    url = f"https://m.stock.naver.com/api/stock/{clean_code}/basic"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=6.0)
        if resp.status_code != 200:
            return None
        data = resp.json()
        now_price = _to_float(data.get("closePrice"))
        rate = _to_float(data.get("fluctuationsRatio"))
        compare = data.get("compareToPreviousPrice") or {}
        if compare.get("name") in {"FALLING", "LOWER_LIMIT"} and rate > 0:
            rate = -rate

        return {
            "code": clean_code,
            "name": data.get("stockName") or "",
            "current_price": now_price,
            "day_change_rate": rate,
            "currency": "KRW",
        }
    except Exception:
        return None


async def fetch_kr_stock_candles(client: httpx.AsyncClient, code: str, current_price: float) -> dict[str, float]:
    clean_code = str(code).strip().zfill(6)
    url = f"https://api.stock.naver.com/chart/domestic/item/{clean_code}?periodType=dayCandle&count=260"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=6.0)
        if resp.status_code != 200:
            return {"1D": 0.0, "1W": 0.0, "1M": 0.0, "YTD": 0.0, "1Y": 0.0}
        data = resp.json()
        raw_candles = data.get("priceInfos", [])
        candles = []
        for item in raw_candles:
            close_val = _to_float(item.get("closePrice"))
            if close_val > 0:
                candles.append({
                    "date": str(item.get("localDate") or ""),
                    "close": close_val,
                })
        return calculate_period_changes(candles, current_price)
    except Exception:
        return {"1D": 0.0, "1W": 0.0, "1M": 0.0, "YTD": 0.0, "1Y": 0.0}


# ─────────────────────────────────────────────────────────────────────────────
# 2. 미국 주식 및 미국 상장 ETF (야후 파이낸스 v8 API)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_us_stock_info(client: httpx.AsyncClient, symbol: str) -> dict[str, Any] | None:
    clean_sym = str(symbol).strip().upper()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_sym}?interval=1d&range=1y"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=7.0)
        if resp.status_code != 200:
            return None
        res_json = resp.json()
        result = res_json.get("chart", {}).get("result", [])
        if not result:
            return None
        meta = result[0].get("meta", {})
        price = float(meta.get("regularMarketPrice") or 0.0)
        prev_close = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
        day_rate = round(((price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0

        timestamps = result[0].get("timestamp", [])
        quotes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        candles = []
        for ts, c_val in zip(timestamps, quotes):
            if c_val is not None and float(c_val) > 0:
                dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%d")
                candles.append({"date": dt_str, "close": float(c_val)})

        period_changes = calculate_period_changes(candles, price)
        period_changes["1D"] = day_rate

        return {
            "code": clean_sym,
            "name": meta.get("shortName") or meta.get("symbol") or clean_sym,
            "current_price": price,
            "day_change_rate": day_rate,
            "currency": "USD",
            "period_changes": period_changes,
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 3. 실시간 환율 (USD/KRW 등)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_fx_rate_usd_krw(client: httpx.AsyncClient | None = None) -> float:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/KRW=X?interval=1d&range=5d"
    should_close = False
    if client is None:
        client = httpx.AsyncClient()
        should_close = True
    try:
        resp = await client.get(url, headers=HEADERS, timeout=6.0)
        if resp.status_code == 200:
            res_json = resp.json()
            meta = res_json.get("chart", {}).get("result", [{}])[0].get("meta", {})
            rate = float(meta.get("regularMarketPrice") or 0.0)
            if rate > 500:
                return round(rate, 2)
    except Exception:
        pass
    finally:
        if should_close:
            await client.aclose()
    return 1385.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. 주요 시장 지수 (시장 스냅샷 및 스파크라인 차트)
# ─────────────────────────────────────────────────────────────────────────────

async def get_web_market_overview() -> list[dict[str, Any]]:
    """
    코스피, 코스닥, S&P 500, 나스닥 종합 4개 지수 스냅샷을 조회합니다.
    wealth.js의 renderMarkets 호환용 label, price, change, change_rate, series 제공
    """
    indices = [
        {"symbol": "^KS11", "label": "코스피", "market": "KRX", "currency": "KRW"},
        {"symbol": "^KQ11", "label": "코스닥", "market": "KRX", "currency": "KRW"},
        {"symbol": "^GSPC", "label": "S&P 500", "market": "US", "currency": "USD"},
        {"symbol": "^IXIC", "label": "나스닥", "market": "US", "currency": "USD"},
    ]

    async with httpx.AsyncClient() as client:
        tasks = []
        for idx in indices:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{idx['symbol']}?interval=1d&range=1mo"
            tasks.append(client.get(url, headers=HEADERS, timeout=6.0))
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    overview = []
    for idx, resp in zip(indices, responses):
        price = 0.0
        rate = 0.0
        diff = 0.0
        series: list[float] = []
        if not isinstance(resp, Exception) and resp.status_code == 200:
            try:
                res_data = resp.json().get("chart", {}).get("result", [{}])[0]
                meta = res_data.get("meta", {})
                price = float(meta.get("regularMarketPrice") or 0.0)
                prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
                diff = price - prev
                rate = ((diff) / prev * 100) if prev > 0 else 0.0

                raw_quotes = res_data.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                valid_quotes = [float(v) for v in raw_quotes if v is not None and float(v) > 0]
                if valid_quotes:
                    series = valid_quotes[-15:]  # 최근 15개 캔들
            except Exception:
                pass

        if not series and price > 0:
            series = [price * 0.995, price]

        overview.append({
            "symbol": idx["symbol"],
            "label": idx["label"],
            "name": idx["label"],
            "market": idx["market"],
            "currency": idx["currency"],
            "price": price,
            "current_price": price,
            "change": diff,
            "change_price": diff,
            "change_rate": round(rate, 2),
            "series": series,
        })
    return overview


# ─────────────────────────────────────────────────────────────────────────────
# 5. 종목별 가격 & 거래량 인터랙티브 차트 데이터 조회
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_stock_chart_data(code: str, period: str = "1M") -> dict[str, Any]:
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
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. 전종목 일괄 병렬 시세 갱신
# ─────────────────────────────────────────────────────────────────────────────

async def refresh_all_holdings_prices(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    if not holdings:
        return {"prices": {}, "daily_changes": {}, "period_rates": {}, "fx_rate": 1385.0}

    async with httpx.AsyncClient() as client:
        fx_task = fetch_fx_rate_usd_krw(client)

        unique_codes = list({str(h.get("code", "")).strip() for h in holdings if h.get("code")})

        def is_kr_symbol(c: str) -> bool:
            return len(c) == 6 and any(ch.isdigit() for ch in c)

        kr_codes = [c for c in unique_codes if is_kr_symbol(c)]
        us_symbols = [c for c in unique_codes if not is_kr_symbol(c)]

        kr_tasks = {c: fetch_kr_stock_info(client, c) for c in kr_codes}
        us_tasks = {s: fetch_us_stock_info(client, s) for s in us_symbols}

        all_tasks = list(kr_tasks.values()) + list(us_tasks.values()) + [fx_task]
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        fx_rate = results[-1] if isinstance(results[-1], (int, float)) else 1385.0
        stock_results = results[:-1]

        code_to_info: dict[str, dict[str, Any]] = {}
        all_codes = list(kr_tasks.keys()) + list(us_tasks.keys())
        for code, res in zip(all_codes, stock_results):
            if isinstance(res, dict) and res.get("current_price", 0) > 0:
                code_to_info[code] = res

        # 국내 종목 기간별 캔들 병렬 조회
        kr_candle_tasks = {}
        for c in kr_codes:
            if c in code_to_info:
                p = code_to_info[c]["current_price"]
                kr_candle_tasks[c] = fetch_kr_stock_candles(client, c, p)

        if kr_candle_tasks:
            kr_candle_results = await asyncio.gather(*kr_candle_tasks.values(), return_exceptions=True)
            for c, c_res in zip(kr_candle_tasks.keys(), kr_candle_results):
                if isinstance(c_res, dict):
                    code_to_info[c]["period_changes"] = c_res

    prices_by_holding_id: dict[str, float] = {}
    daily_changes: dict[str, float] = {}
    period_rates: dict[str, dict[str, float]] = {}

    for h in holdings:
        c = str(h.get("code", "")).strip()
        h_id = h.get("id")
        if c in code_to_info:
            info = code_to_info[c]
            p = info["current_price"]
            if p > 0:
                prices_by_holding_id[h_id] = p
            daily_changes[c.upper()] = info.get("day_change_rate", 0.0)
            if "period_changes" in info:
                period_rates[c.upper()] = info["period_changes"]

    return {
        "prices": prices_by_holding_id,
        "daily_changes": daily_changes,
        "period_rates": period_rates,
        "fx_rate": fx_rate,
    }
'''

with open(WEB_FINANCE_PY, 'w', encoding='utf-8') as f:
    f.write(NEW_CONTENT)

print("web_finance.py updated successfully!")
