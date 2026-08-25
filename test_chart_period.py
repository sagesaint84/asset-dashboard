import asyncio
from app.services.web_finance import fetch_stock_chart_data

async def test():
    for p in ['1W', '1M', '3M', 'YTD', '1Y']:
        res = await fetch_stock_chart_data('QQQM', p)
        candles = res.get('candles', [])
        first_d = candles[0]['date'] if candles else None
        last_d = candles[-1]['date'] if candles else None
        print(f"Period {p:3s} -> {len(candles)} candles. [{first_d} ~ {last_d}]")

asyncio.run(test())
