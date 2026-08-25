import asyncio
import sys

sys.path.insert(0, ".")

from app.main import get_stock_chart, market_overview
from app.services.portfolio import get_dashboard


async def test_all():
    print("=== 1. Market Overview Test ===")
    mkt = await market_overview()
    print("Markets count:", len(mkt["markets"]))
    for m in mkt["markets"]:
        print(f"  {m['label']}: price={m['price']}, change={m['change']}, rate={m['change_rate']}%, series_len={len(m.get('series', []))}")
    print("USD/KRW:", mkt["exchange_rate"]["rate"])

    print("\n=== 2. Stock Chart Test (Domestic: 005930 Samsung) ===")
    chart_kr = await get_stock_chart("005930", "1M")
    print(f"  KR Chart {chart_kr['name']} ({chart_kr['code']}): {len(chart_kr['candles'])} candles")
    if chart_kr["candles"]:
        c0 = chart_kr["candles"][0]
        c_last = chart_kr["candles"][-1]
        print(f"  First: {c0['date']} close={c0['close']} vol={c0['volume']}")
        print(f"  Last:  {c_last['date']} close={c_last['close']} vol={c_last['volume']}")

    print("\n=== 3. Stock Chart Test (US: QQQM) ===")
    chart_us = await get_stock_chart("QQQM", "1M")
    print(f"  US Chart {chart_us['name']} ({chart_us['code']}): {len(chart_us['candles'])} candles")
    if chart_us["candles"]:
        c0 = chart_us["candles"][0]
        c_last = chart_us["candles"][-1]
        print(f"  First: {c0['date']} close={c0['close']} vol={c0['volume']}")
        print(f"  Last:  {c_last['date']} close={c_last['close']} vol={c_last['volume']}")

    print("\n=== 4. Sector Classifications Test ===")
    dash = get_dashboard()
    sectors = dash.get("sector_classifications", [])
    print(f"Sectors count: {len(sectors)}")
    for s in sectors:
        print(f"  {s['name']}: {s['market_value_krw']:,.0f}원 ({s['weight']:.1f}%), 수익률: {s['return_rate']:.2f}%, 종목수: {s['holding_count']}")


asyncio.run(test_all())
