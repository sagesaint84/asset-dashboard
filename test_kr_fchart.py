import asyncio
import httpx
import xml.etree.ElementTree as ET

async def fetch_kr_fchart(code: str, count: int = 300):
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count={count}&requestType=0"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6.0)
        root = ET.fromstring(r.text)
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
                    "open": float(parts[1]),
                    "high": float(parts[2]),
                    "low": float(parts[3]),
                    "close": float(parts[4]),
                    "volume": int(parts[5]),
                })
        return candles

candles = asyncio.run(fetch_kr_fchart("005930", 300))
print(f"Samsung Electronics: {len(candles)} candles. Range: {candles[0]['date']} ~ {candles[-1]['date']}")
