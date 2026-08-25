#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_wealth_js.py
- Remove obsolete duplicate function definitions in wealth.js
- Remove market-symbol-tag from renderMarkets
- Ensure clean single-source logic for renderHoldings, renderClassifications, renderAssetRecords
"""

JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Remove symbol tag from renderMarkets
OLD_SYMBOL_TAG = '<span class="market-symbol-tag">${html(item.symbol)}</span>'
if OLD_SYMBOL_TAG in js:
    js = js.replace(OLD_SYMBOL_TAG, '')
    print("OK 1. Removed market-symbol-tag from renderMarkets")

# 2. Remove obsolete first renderAssetRecords (around lines 300-370)
# Look for function renderAssetRecords(records) { ... } before renderMarkets
idx_rar_1 = js.find('function renderAssetRecords(records) {')
idx_rm = js.find('function renderMarkets(result) {')

if idx_rar_1 != -1 and idx_rm != -1 and idx_rar_1 < idx_rm:
    js = js[:idx_rar_1] + js[idx_rm:]
    print("OK 2. Removed obsolete first renderAssetRecords")

# 3. Remove obsolete first renderClassifications (around line 490)
# Look for first renderClassifications
idx_rc_1 = js.find('function renderClassifications(items) {')
idx_rc_end = js.find('function renderHoldings(data) {')
if idx_rc_1 != -1 and idx_rc_end != -1 and idx_rc_1 < idx_rc_end:
    js = js[:idx_rc_1] + js[idx_rc_end:]
    print("OK 3. Removed obsolete first renderClassifications")

# 4. Remove obsolete first renderHoldings
idx_rh_1 = js.find('function renderHoldings(data) {')
idx_rh_end = js.find('function renderAccounts(accounts) {')
if idx_rh_1 != -1 and idx_rh_end != -1 and idx_rh_1 < idx_rh_end:
    js = js[:idx_rh_1] + js[idx_rh_end:]
    print("OK 4. Removed obsolete first renderHoldings")

# 5. Fix snapshotButton click handler to directly save and immediately reload asset records
OLD_SNAPSHOT_HANDLER = '''$("#snapshotButton").addEventListener("click", (e) => action(e.currentTarget, async () => {
  const today = new Date().toISOString().slice(0, 10);

  if (currentOwner !== '모두') {
    // 특정 구성원 선택 시: loadDashboard 없이 현재 필터된 데이터를 그대로 저장
    const s = dashboard?.summary || {};
    const day = dashboard?.day_change || {};
    const currency = dashboard?.currency_summary || {};
    if (!s.holding_count && !s.total_value_krw) throw new Error('저장할 자산 데이터가 없습니다.');
    return api("/api/asset-records", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      date: today,
      total_value_krw: s.total_value_krw || 0,
      total_cost_krw: s.total_cost_krw || 0,
      profit_krw: s.profit_krw || 0,
      return_rate: s.return_rate || 0,
      day_profit_krw: day.change_krw || 0,
      krw_value_krw: currency.KRW?.market_value_krw || 0,
      usd_value_krw: currency.USD?.market_value_krw || 0,
      holding_count: s.holding_count || 0,
      source: "snapshot",
      memo: `${currentOwner} 스냅샷`,
      owner: currentOwner,
    }) });
  }

  // 모두 선택 시: 서버 snapshot API 시도 → 실패 시 전체 데이터로 직접 저장
  await loadDashboard();
  try {
    return await api("/api/asset-records/snapshot", { method: "POST" });
  } catch (error) {
    if (!/Not Found|찾지 못|404/i.test(error.message || "")) throw error;
    const s = dashboard.summary || {};
    const day = dashboard.day_change || {};
    const currency = dashboard.currency_summary || {};
    return api("/api/asset-records", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      date: new Date().toISOString().slice(0, 10), total_value_krw: s.total_value_krw, total_cost_krw: s.total_cost_krw,
      profit_krw: s.profit_krw, return_rate: s.return_rate, day_profit_krw: day.change_krw || 0,
      krw_value_krw: currency.KRW?.market_value_krw || 0, usd_value_krw: currency.USD?.market_value_krw || 0,
      holding_count: s.holding_count, source: "snapshot", memo: "수동 스냅샷", owner: currentOwner || "모두"
    }) });
  }
}, async () => { await loadDashboard(); await loadAssetRecords(currentOwner); }));'''

NEW_SNAPSHOT_HANDLER = '''$("#snapshotButton").addEventListener("click", (e) => action(e.currentTarget, async () => {
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

if OLD_SNAPSHOT_HANDLER in js:
    js = js.replace(OLD_SNAPSHOT_HANDLER, NEW_SNAPSHOT_HANDLER, 1)
    print("OK 5. Simplified and robustified snapshotButton handler")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print("wealth.js cleanup complete!")
