#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_wealth_and_main.py
- Fix cache-control in FastAPI for index.html
- Fix wealth.js asset records handling and filter
- Ensure index.html and root route serve the updated dashboard directly
"""

import re
import time

# 1. Update app/main.py
with open("app/main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

# Make "/" and "/dashboard" return FileResponse with no-cache headers
old_routes = '''@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")'''

new_routes = '''@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
async def dashboard_page() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    )'''

if old_routes in main_code:
    main_code = main_code.replace(old_routes, new_routes, 1)
    print("OK: main.py root & dashboard routes updated with no-cache headers")

with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(main_code)


# 2. Update wealth.js
with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    js = f.read()

# Ensure filterRecordsByPeriod and renderAssetRecords and loadAssetRecords are rock-solid
# Replace loadAssetRecords
old_load_records = '''async function loadAssetRecords(owner) {
  // 전체 자산기록 동기화 (일간 수익 비교용)
  try {
    const allRes = await api('/api/asset-records');
    allAssetRecords = allRes.records || [];
  } catch (e) {}

  // 화면 표시용 필터링
  const o = owner || currentOwner || '모두';
  const filtered = allAssetRecords.filter(r => (r.owner || '모두') === o);
  renderAssetRecords(filtered);
}'''

new_load_records = '''async function loadAssetRecords(owner) {
  try {
    const allRes = await api('/api/asset-records');
    allAssetRecords = allRes.records || [];
  } catch (e) {
    console.error("loadAssetRecords error:", e);
  }

  const o = owner || currentOwner || '모두';
  let filtered = [];
  if (o === '모두') {
    // 모두일 때는 owner가 '모두'인 기록이 있으면 그것을 우선, 없으면 전체 기록 표시
    const allOwnerRecs = allAssetRecords.filter(r => (r.owner || '모두') === '모두');
    filtered = allOwnerRecs.length > 0 ? allOwnerRecs : allAssetRecords;
  } else {
    filtered = allAssetRecords.filter(r => (r.owner || '모두') === o);
  }
  
  assetRecords = filtered;
  window.assetRecords = filtered;
  renderAssetRecords(filtered);
}'''

if old_load_records in js:
    js = js.replace(old_load_records, new_load_records, 1)
    print("OK: loadAssetRecords improved")

# Replace snapshotButton handler to be ultra explicit and guaranteed to succeed
old_snapshot_handler = '''$("#snapshotButton").addEventListener("click", (e) => action(e.currentTarget, async () => {
  const today = new Date().toISOString().slice(0, 10);
  const s = dashboard?.summary || {};
  const day = dashboard?.day_change || {};
  const currency = dashboard?.currency_summary || {};

  const payload = {
    date: today,
    total_value_krw: Number(s.total_value_krw || 0),
    total_cost_krw: Number(s.total_cost_krw || 0),
    profit_krw: Number(s.profit_krw || 0),
    return_rate: Number(s.return_rate || 0),
    day_profit_krw: Number(day.change_krw || 0),
    krw_value_krw: Number(currency.KRW?.market_value_krw || 0),
    usd_value_krw: Number(currency.USD?.market_value_krw || 0),
    holding_count: Number(s.holding_count || 0),
    source: "snapshot",
    memo: currentOwner === '모두' ? "오늘 스냅샷" : `${currentOwner} 스냅샷`,
    owner: currentOwner || "모두",
  };

  const res = await api("/api/asset-records", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res;
}, async () => {
  await loadAssetRecords(currentOwner);
}));'''

new_snapshot_handler = '''$("#snapshotButton").addEventListener("click", (e) => action(e.currentTarget, async () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const dayStr = String(now.getDate()).padStart(2, '0');
  const today = `${year}-${month}-${dayStr}`;

  const s = dashboard?.summary || {};
  const day = dashboard?.day_change || {};
  const currency = dashboard?.currency_summary || {};

  const payload = {
    date: today,
    total_value_krw: Number(s.total_value_krw || 0),
    total_cost_krw: Number(s.total_cost_krw || 0),
    profit_krw: Number(s.profit_krw || 0),
    return_rate: Number(s.return_rate || 0),
    day_profit_krw: Number(day.change_krw || 0),
    krw_value_krw: Number(currency.KRW?.market_value_krw || 0),
    usd_value_krw: Number(currency.USD?.market_value_krw || 0),
    holding_count: Number(s.holding_count || 0),
    source: "snapshot",
    memo: currentOwner === '모두' ? "오늘 스냅샷" : `${currentOwner} 스냅샷`,
    owner: currentOwner || "모두",
  };

  const res = await api("/api/asset-records", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res;
}, async () => {
  await loadAssetRecords(currentOwner);
}));'''

if old_snapshot_handler in js:
    js = js.replace(old_snapshot_handler, new_snapshot_handler, 1)
    print("OK: snapshotButton handler updated")

with open("app/static/wealth.js", "w", encoding="utf-8") as f:
    f.write(js)


# 3. Update index.html version with timestamp
ts = int(time.time())
with open("app/static/index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

html_content = re.sub(r'wealth-overrides\.css\?v=[^\"]+', f'wealth-overrides.css?v={ts}', html_content)
html_content = re.sub(r'wealth\.js\?v=[^\"]+', f'wealth.js?v={ts}', html_content)

with open("app/static/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"OK: index.html asset query strings updated to v={ts}")
