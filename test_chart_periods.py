import asyncio
import sys

sys.path.insert(0, ".")
from app.services.web_finance import fetch_stock_chart_data


async def test():
    print("Testing 005930 (Domestic):")
    for p in ["1W", "1M", "3M", "YTD", "1Y"]:
        res = await fetch_stock_chart_data("005930", p)
        candles = res.get("candles", [])
        c0 = candles[0]["date"] if candles else None
        c1 = candles[-1]["date"] if candles else None
        print(f"  Period {p:3s}: {len(candles):3d} candles, start={c0}, end={c1}")

    print("\nTesting QQQM (US):")
    for p in ["1W", "1M", "3M", "YTD", "1Y"]:
        res = await fetch_stock_chart_data("QQQM", p)
        candles = res.get("candles", [])
        c0 = candles[0]["date"] if candles else None
        c1 = candles[-1]["date"] if candles else None
        print(f"  Period {p:3s}: {len(candles):3d} candles, start={c0}, end={c1}")


asyncio.run(test())
