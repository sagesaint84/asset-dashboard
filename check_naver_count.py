import asyncio

import httpx


async def check():
    headers = {"User-Agent": "Mozilla/5.0"}
    for cnt in [5, 15, 30, 60]:
        url = f"https://api.stock.naver.com/chart/domestic/item/005930?periodType=dayCandle&count={cnt}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            data = r.json()
            items = data.get("priceInfos", [])
            print(f"cnt={cnt}, return len={len(items)}")


asyncio.run(check())
