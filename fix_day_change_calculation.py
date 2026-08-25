#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_day_change_calculation.py
1. Fix portfolio.py previous_value lookup to only check owner == "모두"
2. Fix main.py auto snapshot to set owner = "모두"
3. Fix asset_records.json existing 2026-08-23 records
4. Fix wealth.js computeFilteredDayChange to look up past records for the selected owner
"""

import json
from pathlib import Path

# ── 1. Fix app/services/portfolio.py ──────────────────────────────────────────
PORTFOLIO_PY = 'app/services/portfolio.py'
with open(PORTFOLIO_PY, 'r', encoding='utf-8') as f:
    p_code = f.read()

OLD_PAST_LOOKUP = '''            past_records = [
                r for r in rec_data.get("records", [])
                if isinstance(r, dict) and r.get("date") and r.get("date") < today_str and to_number(r.get("total_value_krw")) > 0
            ]'''

NEW_PAST_LOOKUP = '''            past_records = [
                r for r in rec_data.get("records", [])
                if isinstance(r, dict)
                and (r.get("owner") or "모두") == "모두"
                and r.get("date")
                and r.get("date") < today_str
                and to_number(r.get("total_value_krw")) > 0
            ]'''

if OLD_PAST_LOOKUP in p_code:
    p_code = p_code.replace(OLD_PAST_LOOKUP, NEW_PAST_LOOKUP, 1)
    print("OK 1. Fixed portfolio.py previous_value owner filter")
else:
    print("WARN 1. Could not find exact past_records pattern in portfolio.py")

with open(PORTFOLIO_PY, 'w', encoding='utf-8') as f:
    f.write(p_code)

# ── 2. Fix app/main.py auto-snapshot owner ────────────────────────────────────
MAIN_PY = 'app/main.py'
with open(MAIN_PY, 'r', encoding='utf-8') as f:
    m_code = f.read()

OLD_MAIN_SNAP = '''    if data["summary"]["holding_count"]:
        snapshot = {
            "date": today,
            "total_value_krw": data["summary"]["total_value_krw"],'''

NEW_MAIN_SNAP = '''    if data["summary"]["holding_count"]:
        snapshot = {
            "date": today,
            "owner": "모두",
            "total_value_krw": data["summary"]["total_value_krw"],'''

if OLD_MAIN_SNAP in m_code:
    m_code = m_code.replace(OLD_MAIN_SNAP, NEW_MAIN_SNAP, 1)
    print("OK 2. Fixed main.py auto-snapshot owner field")
else:
    print("WARN 2. Could not find exact auto snapshot pattern in main.py")

with open(MAIN_PY, 'w', encoding='utf-8') as f:
    f.write(m_code)

# ── 3. Clean up and recalculate 2026-08-23 records in data/asset_records.json ──
DATA_FILE = 'data/asset_records.json'
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    ar_data = json.load(f)

records = ar_data.get("records", [])

# Find 2026-08-22 records by owner
prev_by_owner = {}
for r in records:
    if r.get("date") == "2026-08-22":
        prev_by_owner[r.get("owner") or "모두"] = r

for r in records:
    if r.get("date") == "2026-08-23":
        owner = r.get("owner") or "모두"
        prev = prev_by_owner.get(owner)
        if prev:
            curr_val = float(r.get("total_value_krw") or 0)
            prev_val = float(prev.get("total_value_krw") or 0)
            diff = curr_val - prev_val
            r["day_profit_krw"] = diff
            print(f"Fixed 2026-08-23 ({owner}): diff={diff}")

with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(ar_data, f, ensure_ascii=False, indent=2)
print("OK 3. Fixed asset_records.json records for 2026-08-23")

# ── 4. Fix wealth.js computeFilteredDayChange & snapshot logic ─────────────────
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# Update computeFilteredDayChange to accept owner & compute difference from previous asset record if available
OLD_CFD = '''function computeFilteredDayChange(holdings, rawDayChange) {
  if (!holdings.length) return {};
  // Approximate day change from filtered holdings
  let totalValue = 0, weightedChange = 0;
  holdings.forEach(h => {
    const val  = Number(h.market_value_krw || 0);
    const rate = Number(h.day_change_rate  || 0);
    totalValue      += val;
    weightedChange  += val * rate;
  });
  if (totalValue === 0) return {};
  const change_rate = weightedChange / totalValue;
  const change_krw  = totalValue * change_rate / (100 + change_rate) || 0;
  return {
    change_rate,
    change_krw,
    date: (rawDayChange || {}).date,
  };
}'''

NEW_CFD = '''function computeFilteredDayChange(holdings, rawDayChange, owner, filteredSummary) {
  const targetOwner = owner || '모두';
  const totalVal = filteredSummary ? Number(filteredSummary.total_value_krw || 0) : 0;
  const todayStr = new Date().toISOString().slice(0, 10);

  // 1. assetRecords 목록에서 오늘 이전의 해당 owner 최신 기록 조회
  if (window.assetRecords && window.assetRecords.length > 0 && totalVal > 0) {
    const past = window.assetRecords.filter(r => (r.owner || '모두') === targetOwner && r.date && r.date < todayStr && Number(r.total_value_krw || 0) > 0);
    if (past.length > 0) {
      past.sort((a, b) => a.date.localeCompare(b.date));
      const last = past[past.length - 1];
      const prevVal = Number(last.total_value_krw || 0);
      if (prevVal > 0) {
        const change_krw = totalVal - prevVal;
        const change_rate = (change_krw / prevVal) * 100;
        return {
          change_rate,
          change_krw,
          date: last.date,
        };
      }
    }
  }

  // 2. 과거 기록이 없거나 0일 경우 종목 가중치 기반 fallback
  if (!holdings || !holdings.length) return {};
  let totalValue = 0, weightedChange = 0;
  holdings.forEach(h => {
    const val  = Number(h.market_value_krw || 0);
    const rate = Number(h.day_change_rate  || 0);
    totalValue      += val;
    weightedChange  += val * rate;
  });
  if (totalValue === 0) return {};
  const change_rate = weightedChange / totalValue;
  const change_krw  = totalValue * change_rate / (100 + change_rate) || 0;
  return {
    change_rate,
    change_krw,
    date: (rawDayChange || {}).date,
  };
}'''

if OLD_CFD in js:
    js = js.replace(OLD_CFD, NEW_CFD, 1)
    print("OK 4a. Updated computeFilteredDayChange in wealth.js")
else:
    print("WARN 4a. Old computeFilteredDayChange not found")

# Update renderWithOwner call to pass owner and filteredSummary
OLD_RWO_CALL = '    filteredData.day_change       = computeFilteredDayChange(filteredData.holdings, src.day_change);'
NEW_RWO_CALL = '    filteredData.day_change       = computeFilteredDayChange(filteredData.holdings, src.day_change, owner, filteredData.summary);'

if OLD_RWO_CALL in js:
    js = js.replace(OLD_RWO_CALL, NEW_RWO_CALL, 1)
    print("OK 4b. Updated renderWithOwner day_change call in wealth.js")
else:
    print("WARN 4b. Old renderWithOwner day_change call not found")

# Ensure assetRecords is stored in window.assetRecords so computeFilteredDayChange can access it
OLD_RAR = 'function renderAssetRecords(items) {'
NEW_RAR = 'function renderAssetRecords(items) {\n  window.assetRecords = items || [];'

if OLD_RAR in js and 'window.assetRecords' not in js:
    js = js.replace(OLD_RAR, NEW_RAR, 1)
    print("OK 4c. Set window.assetRecords in renderAssetRecords")
else:
    print("INFO 4c. window.assetRecords already set or pattern different")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print("All day_change fixes complete!")
