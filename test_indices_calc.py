import asyncio
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
indices = [
    {"symbol": "^KS11", "label": "코스피"},
    {"symbol": "^KQ11", "label": "코스닥"},
    {"symbol": "^GSPC", "label": "S&P 500"},
    {"symbol": "^IXIC", "label": "나스닥"},
    {"symbol": "KRW=X", "label": "달러 환율"},
]

async def test():
    async with httpx.AsyncClient() as client:
        for idx in indices:
            sym = idx["symbol"]
            label = idx["label"]
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1mo"
            r = await client.get(url, headers=HEADERS)
            res = r.json()["chart"]["result"][0]
            meta = res["meta"]
            raw_quotes = res["indicators"]["quote"][0]["close"]
            valid = [float(v) for v in raw_quotes if v is not None and float(v) > 0]
            price = float(meta.get("regularMarketPrice") or (valid[-1] if valid else 0.0))
            
            # 전일 종가: previousClose 또는 valid[-2]
            prev = float(meta.get("previousClose") or (valid[-2] if len(valid) >= 2 else price))
            diff = price - prev
            rate = (diff / prev * 100) if prev > 0 else 0.0
            print(f"{label:8s}: Price: {price:,.2f}, Diff: {diff:+,.2f}, Rate: {rate:+.2f}% (PrevClose: {prev:,.2f})")

asyncio.run(test())
