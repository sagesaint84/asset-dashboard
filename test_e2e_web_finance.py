import asyncio
import sys

sys.path.insert(0, ".")

from app.main import market_overview, refresh_fx_rate, refresh_prices


async def run():
    print("1. Testing refresh_fx_rate()...")
    fx_res = await refresh_fx_rate()
    print("   FX result:", fx_res)

    print("\n2. Testing refresh_prices()...")
    p_res = await refresh_prices()
    print("   Price result:", p_res)

    print("\n3. Testing market_overview()...")
    m_res = await market_overview()
    print("   Market count:", len(m_res["markets"]))
    for m in m_res["markets"]:
        print(f"     {m['name']}: {m['current_price']} ({m['change_rate']}%)")
    print("   USD/KRW rate:", m_res["exchange_rate"]["rate"])


asyncio.run(run())
