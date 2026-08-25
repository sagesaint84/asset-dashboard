import asyncio
import sys

sys.path.insert(0, ".")
from starlette.requests import Request

from app.main import get_asset_records, snapshot_asset_record


async def run():
    print("Testing snapshot_asset_record...")
    req = Request({"type": "http", "method": "POST", "url": "http://localhost/api/asset-records/snapshot"})
    res = await snapshot_asset_record(req)
    print("Snapshot result:", res)

    print("\nTesting get_asset_records...")
    records = await get_asset_records(owner="모두")
    rec_list = records.get("records", [])
    print(f"Retrieved {len(rec_list)} records for 모두")
    for r in rec_list[-5:]:
        print(f"  {r.get('date')}: total={r.get('total_value_krw')}, owner={r.get('owner')}")


asyncio.run(run())
