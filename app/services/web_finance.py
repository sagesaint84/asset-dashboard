from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
import xml.etree.ElementTree as ET

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
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={clean_code}&timeframe=day&count=300&requestType=0"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=6.0)
        if resp.status_code != 200:
            return {"1D": 0.0, "1W": 0.0, "1M": 0.0, "YTD": 0.0, "1Y": 0.0}
        root = ET.fromstring(resp.text)
        items = root.findall(".//item")
        candles = []
        for it in items:
            raw = it.attrib.get("data", "")
            parts = raw.split("|")
            if len(parts) >= 6:
                d_str = parts[0]
                if len(d_str) == 8:
                    d_str = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                candles.append({
                    "date": d_str,
                    "close": float(parts[4]),
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
        timestamps = result[0].get("timestamp", [])
        quotes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        candles = []
        for ts, c_val in zip(timestamps, quotes):
            if c_val is not None and float(c_val) > 0:
                dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%d")
                candles.append({"date": dt_str, "close": float(c_val)})

        price = float(meta.get("regularMarketPrice") or (candles[-1]["close"] if candles else 0.0))
        
        # 야후 파이낸스 정규장 전일 종가 정밀 결정
        prev_close = 0.0
        if meta.get("previousClose") is not None and float(meta.get("previousClose")) > 0:
            prev_close = float(meta.get("previousClose"))
        elif len(candles) >= 2:
            prev_close = float(candles[-2]["close"])
        elif candles:
            prev_close = float(candles[-1]["close"])

        day_rate = round(((price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0

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
                raw_quotes = res_data.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                valid_quotes = [float(v) for v in raw_quotes if v is not None and float(v) > 0]
                price = float(meta.get("regularMarketPrice") or (valid_quotes[-1] if valid_quotes else 0.0))

                # 직전 거래일 종가 (previousClose 또는 최근 캔들[-2])
                prev = float(meta.get("previousClose") or (valid_quotes[-2] if len(valid_quotes) >= 2 else price))
                diff = price - prev
                rate = ((diff) / prev * 100) if prev > 0 else 0.0

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
            "change": round(diff, 2),
            "change_price": round(diff, 2),
            "change_rate": round(rate, 2),
            "series": series,
        })

    fx_rate = 1385.0
    fx_change = 0.0
    fx_rate_pct = 0.0
    fx_series = [1385.0, 1385.0]
    try:
        async with httpx.AsyncClient() as client:
            resp_fx = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/KRW=X?interval=1d&range=1mo", headers=HEADERS, timeout=6.0)
            if resp_fx.status_code == 200:
                res_data = resp_fx.json().get("chart", {}).get("result", [{}])[0]
                meta = res_data.get("meta", {})
                raw_quotes = res_data.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                valid_quotes = [float(v) for v in raw_quotes if v is not None and float(v) > 0]
                fx_rate = float(meta.get("regularMarketPrice") or (valid_quotes[-1] if valid_quotes else 1385.0))
                prev = float(meta.get("previousClose") or (valid_quotes[-2] if len(valid_quotes) >= 2 else fx_rate))
                fx_change = fx_rate - prev
                fx_rate_pct = ((fx_change) / prev * 100) if prev > 0 else 0.0
                if valid_quotes:
                    fx_series = valid_quotes[-15:]
    except Exception:
        pass

    return {
        "markets": overview,
        "exchange_rate": {
            "rate": fx_rate,
            "change": round(fx_change, 2),
            "change_rate": round(fx_rate_pct, 2),
            "series": fx_series,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. 종목별 가격 & 거래량 인터랙티브 차트 데이터 조회
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_stock_chart_data(code: str, period: str = "1M") -> dict[str, Any]:
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
            url = f"https://fchart.stock.naver.com/sise.nhn?symbol={clean_code}&timeframe=day&count=300&requestType=0"
            try:
                resp = await client.get(url, headers=HEADERS, timeout=6.0)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    items = root.findall(".//item")
                    for it in items:
                        raw = it.attrib.get("data", "")
                        parts = raw.split("|")
                        if len(parts) >= 6:
                            d_str = parts[0]
                            if len(d_str) == 8:
                                d_str = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                            candles.append({
                                "date": d_str,
                                "open": float(parts[1]),
                                "high": float(parts[2]),
                                "low": float(parts[3]),
                                "close": float(parts[4]),
                                "volume": int(parts[5]),
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


# ─────────────────────────────────────────────────────────────────────────────
# 6. 배당(분배금) 수집 및 1월~12월 캘린더 분석 엔진
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_us_dividend(client: httpx.AsyncClient, symbol: str) -> dict[str, Any]:
    """미국 주식/ETF의 1년치 배당 이력, 배당월, 주당 배당금 수집"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y&events=div"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=6.0)
        if resp.status_code != 200:
            return {"annual_div": 0.0, "payout_months": [], "div_yield": 0.0, "div_count": 0}
        data = resp.json()
        result = (data.get("chart", {}).get("result") or [{}])[0]
        meta = result.get("meta", {})
        price = _to_float(meta.get("regularMarketPrice"))
        divs = result.get("events", {}).get("dividends", {})
        if not divs:
            return {"annual_div": 0.0, "payout_months": [], "div_yield": 0.0, "div_count": 0}

        amounts = [float(d["amount"]) for d in divs.values() if "amount" in d]
        annual_div = round(sum(amounts), 4)
        div_count = len(amounts)

        months = set()
        for d in divs.values():
            if "date" in d:
                dt = datetime.fromtimestamp(d["date"], tz=timezone.utc)
                months.add(dt.month)

        payout_months = sorted(list(months))
        if not payout_months and div_count >= 10:
            payout_months = list(range(1, 13))
        elif not payout_months and div_count == 4:
            payout_months = [3, 6, 9, 12]

        div_yield = round((annual_div / price * 100), 2) if price > 0 else 0.0

        return {
            "annual_div": annual_div,
            "payout_months": payout_months,
            "div_yield": div_yield,
            "div_count": div_count,
        }
    except Exception:
        return {"annual_div": 0.0, "payout_months": [], "div_yield": 0.0, "div_count": 0}


async def fetch_kr_dividend(client: httpx.AsyncClient, code: str, current_price: float) -> dict[str, Any]:
    """국내 주식/ETF의 배당수익률 및 배당월 수집"""
    clean_code = str(code).strip().zfill(6)
    url = f"https://finance.naver.com/item/main.naver?code={clean_code}"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=6.0)
        if resp.status_code != 200:
            return {"annual_div": 0.0, "payout_months": [], "div_yield": 0.0, "div_count": 0}
        import re
        html = resp.text
        dvd_yield_match = re.findall(r"배당수익률.*?<em[^>]*>([^<]+)</em>", html, re.DOTALL)
        dvd_yield = _to_float(dvd_yield_match[0]) if dvd_yield_match else 0.0

        dvd_amt_match = re.findall(r"주당배당금.*?<td[^>]*>([^<]+)</td>", html, re.DOTALL)
        dvd_amt = _to_float(dvd_amt_match[0]) if dvd_amt_match else 0.0

        if dvd_amt == 0.0 and dvd_yield > 0.0 and current_price > 0:
            dvd_amt = round(current_price * (dvd_yield / 100), 0)

        # 주요 분기배당 및 월배당 ETF 판별
        quarterly_codes = {"005930", "005935", "005380", "005385", "005387", "005490", "055550", "105560", "086790"}
        if clean_code in quarterly_codes:
            payout_months = [4, 5, 8, 11] # 국내 분기배당 실제 지급월 (4월, 5월, 8월, 11월)
        elif dvd_yield > 0:
            payout_months = [4] # 12월 결산법인 일반 배당 지급월 (4월)
        else:
            payout_months = []

        return {
            "annual_div": dvd_amt,
            "payout_months": payout_months,
            "div_yield": dvd_yield,
            "div_count": len(payout_months),
        }
    except Exception:
        return {"annual_div": 0.0, "payout_months": [], "div_yield": 0.0, "div_count": 0}


async def get_web_dividend_summary(holdings: list[dict[str, Any]], fx_rate: float = 1385.0) -> dict[str, Any]:
    """
    전체 보유 종목에 대해 실시간 배당 정보를 집계하고,
    1월부터 12월까지의 월별 예상 배당금 캘린더 데이터를 계산합니다.
    """
    if not holdings:
        return {
            "total_annual_dividend_krw": 0.0,
            "portfolio_yield": 0.0,
            "monthly_avg_dividend_krw": 0.0,
            "dividend_paying_count": 0,
            "monthly_schedule": {m: {"total_krw": 0.0, "items": []} for m in range(1, 13)},
            "holding_dividends": [],
        }

    async with httpx.AsyncClient(timeout=8.0) as client:
        # 중복 종목 코드 제거 후 병렬 조회
        unique_stocks = {}
        for h in holdings:
            code = str(h.get("code", "")).strip()
            if code and code not in unique_stocks:
                currency = str(h.get("currency", "KRW")).upper()
                curr_p = _to_float(h.get("current_price") or h.get("purchase_price"))
                unique_stocks[code] = (currency, curr_p)

        div_tasks = {}
        for code, (currency, curr_p) in unique_stocks.items():
            if currency == "USD" or not code.isdigit():
                div_tasks[code] = fetch_us_dividend(client, code)
            else:
                div_tasks[code] = fetch_kr_dividend(client, code, curr_p)

        results = await asyncio.gather(*div_tasks.values(), return_exceptions=True)
        div_map = {}
        for code, res in zip(div_tasks.keys(), results):
            if isinstance(res, dict):
                div_map[code] = res
            else:
                div_map[code] = {"annual_div": 0.0, "payout_months": [], "div_yield": 0.0, "div_count": 0}

    total_annual_krw = 0.0
    total_eval_krw = 0.0
    dividend_paying_count = 0
    monthly_schedule = {m: {"month": m, "total_krw": 0.0, "items": []} for m in range(1, 13)}
    holding_dividends = []

    for h in holdings:
        code = str(h.get("code", "")).strip()
        name = str(h.get("name", code))
        qty = _to_float(h.get("quantity", 0))
        currency = str(h.get("currency", "KRW")).upper()
        curr_p = _to_float(h.get("current_price") or h.get("purchase_price"))
        market_val_krw = qty * curr_p * (fx_rate if currency == "USD" else 1.0)
        total_eval_krw += market_val_krw

        d_info = div_map.get(code, {"annual_div": 0.0, "payout_months": [], "div_yield": 0.0, "div_count": 0})
        annual_div_per_share = d_info.get("annual_div", 0.0)
        div_yield = d_info.get("div_yield", 0.0)
        payout_months = d_info.get("payout_months", [])

        annual_payout_orig = qty * annual_div_per_share
        annual_payout_krw = annual_payout_orig * (fx_rate if currency == "USD" else 1.0)

        if annual_payout_krw > 0:
            dividend_paying_count += 1
            total_annual_krw += annual_payout_krw

            # 월별 분배
            if payout_months:
                per_month_krw = annual_payout_krw / len(payout_months)
                per_month_orig = annual_payout_orig / len(payout_months)
                for m in payout_months:
                    if 1 <= m <= 12:
                        monthly_schedule[m]["total_krw"] += per_month_krw
                        monthly_schedule[m]["items"].append({
                            "code": code,
                            "name": name,
                            "quantity": qty,
                            "currency": currency,
                            "payout_krw": round(per_month_krw, 0),
                            "payout_orig": round(per_month_orig, 2),
                            "div_yield": div_yield,
                        })

        holding_dividends.append({
            "code": code,
            "name": name,
            "quantity": qty,
            "currency": currency,
            "annual_div_per_share": annual_div_per_share,
            "div_yield": div_yield,
            "annual_payout_krw": round(annual_payout_krw, 0),
            "annual_payout_orig": round(annual_payout_orig, 2),
            "payout_months": payout_months,
        })

    portfolio_yield = round((total_annual_krw / total_eval_krw * 100), 2) if total_eval_krw > 0 else 0.0
    monthly_avg_krw = round(total_annual_krw / 12, 0)

    # 월별 일정 정렬
    monthly_list = []
    for m in range(1, 13):
        item = monthly_schedule[m]
        item["total_krw"] = round(item["total_krw"], 0)
        item["items"].sort(key=lambda x: x["payout_krw"], reverse=True)
        monthly_list.append(item)

    return {
        "total_annual_dividend_krw": round(total_annual_krw, 0),
        "portfolio_yield": portfolio_yield,
        "monthly_avg_dividend_krw": monthly_avg_krw,
        "dividend_paying_count": dividend_paying_count,
        "monthly_schedule": monthly_list,
        "holding_dividends": sorted(holding_dividends, key=lambda x: x["annual_payout_krw"], reverse=True),
    }

