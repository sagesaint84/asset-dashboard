import asyncio
import sys

sys.path.insert(0, ".")

from app.services.portfolio import read_portfolio
from app.services.web_finance import (
    fetch_fx_rate_usd_krw,
    get_web_market_overview,
    refresh_all_holdings_prices,
)


async def test():
    data = read_portfolio()
    holdings = data.get("holdings", [])
    print(f"Testing with {len(holdings)} holdings...")
    res = await refresh_all_holdings_prices(holdings)
    print("FX Rate:", res["fx_rate"])
    print("Updated prices count:", len(res["prices"]))
    print("Daily changes count:", len(res["daily_changes"]))
    print("Period rates count:", len(res["period_rates"]))

    # Sample items
    for sym in ["005930", "0015B0", "QQQM", "TLT", "NVDA", "475050"]:
        if sym in res["period_rates"]:
            print(f"  {sym}: {res['period_rates'][sym]}")

    # Market overview
    mkt = await get_web_market_overview()
    print("Market overview:")
    for m in mkt:
        print(f"  {m['name']}: {m['current_price']} ({m['change_rate']}%)")


asyncio.run(test())
