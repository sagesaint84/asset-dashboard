import asyncio
from app.services.web_finance import get_web_market_overview

async def test():
    res = await get_web_market_overview()
    for m in res["markets"]:
        print(f"{m['label']:8s}: {m['price']:,.2f} {m['change']:+,.2f} ({m['change_rate']:+.2f}%)")
    fx = res["exchange_rate"]
    print(f"{'달러 환율':8s}: {fx['rate']:,.2f} {fx['change']:+,.2f} ({fx['change_rate']:+.2f}%)")

asyncio.run(test())
