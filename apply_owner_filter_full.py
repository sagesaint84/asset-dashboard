#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_owner_filter_full.py
- Update renderWithOwner to recalculate summary, classifications, currency_summary
  from filtered accounts/holdings
- Update loadAssetRecords to pass currentOwner for filtering (asset_records owner field)
- Add owner field to asset record creation APIs
"""

JS_PATH = 'app/static/wealth.js'
MAIN_PATH = 'app/main.py'

# ──────────────────────────────────────────────────────────────────────────────
# 1.  wealth.js  – upgrade renderWithOwner
# ──────────────────────────────────────────────────────────────────────────────
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

OLD_RWO = '''function renderWithOwner(data, owner) {
  // Always filter from rawDashboard to prevent data loss on re-render
  const src = rawDashboard || data;
  const filteredData = Object.assign({}, src);
  if (owner !== '모두') {
    filteredData.accounts = (src.accounts || []).filter(a => {
      const o = a.owner || '모두';
      return o === owner;
    });
    const ownedIds = new Set(filteredData.accounts.map(a => a.id));
    filteredData.holdings = (src.holdings || []).filter(h => ownedIds.has(h.account_id));
  } else {
    // 모두: show everything
    filteredData.accounts = src.accounts || [];
    filteredData.holdings = src.holdings || [];
  }
  render(filteredData);
}'''

NEW_RWO = '''// ── 필터링된 데이터로 핵심 요약 재계산 ──────────────────────────────────────
function computeFilteredSummary(accounts, holdings, fxRates) {
  const usdKrw = (fxRates || {})['USD'] || 1300;
  let total_stock_value_krw = 0, total_cash_krw = 0, total_cost_krw = 0, profit_krw = 0;
  let cash_krw = 0, cash_usd = 0;

  holdings.forEach(h => {
    total_stock_value_krw += Number(h.market_value_krw || 0);
    total_cost_krw        += Number(h.cost_value_krw  || 0);
    profit_krw            += Number(h.profit_krw      || 0);
  });
  accounts.forEach(a => {
    cash_krw += Number(a.cash_krw || 0);
    cash_usd += Number(a.cash_usd || 0);
  });
  total_cash_krw = cash_krw + cash_usd * usdKrw;
  const total_value_krw = total_stock_value_krw + total_cash_krw;
  const return_rate = total_cost_krw > 0 ? (profit_krw / total_cost_krw) * 100 : 0;
  return {
    total_value_krw, total_stock_value_krw, total_cash_krw,
    total_cost_krw, profit_krw, return_rate, cash_krw, cash_usd,
    holding_count: holdings.length,
    account_count: accounts.length,
  };
}

function computeFilteredClassifications(holdings) {
  const groups = {};
  let totalValue = 0;
  holdings.forEach(h => {
    const name = h.currency === 'KRW' ? '국내 주식' : '해외 주식';
    if (!groups[name]) groups[name] = { name, market_value_krw: 0, cost_value_krw: 0, profit_krw: 0, holding_count: 0 };
    const g = groups[name];
    g.market_value_krw += Number(h.market_value_krw || 0);
    g.cost_value_krw   += Number(h.cost_value_krw   || 0);
    g.profit_krw       += Number(h.profit_krw        || 0);
    g.holding_count    += 1;
    totalValue         += Number(h.market_value_krw || 0);
  });
  return Object.values(groups).map(g => ({
    ...g,
    return_rate: g.cost_value_krw > 0 ? (g.profit_krw / g.cost_value_krw) * 100 : 0,
    weight: totalValue > 0 ? (g.market_value_krw / totalValue) * 100 : 0,
  }));
}

function computeFilteredCurrencySummary(holdings, accounts, fxRates) {
  const usdKrw = (fxRates || {})['USD'] || 1300;
  const krw = { market_value_krw: 0, stock_value_krw: 0, cash: 0 };
  const usd = { market_value: 0, stock_value: 0, cash: 0, market_value_krw: 0 };

  holdings.forEach(h => {
    if (h.currency === 'KRW') {
      krw.market_value_krw += Number(h.market_value_krw || 0);
      krw.stock_value_krw  += Number(h.market_value_krw || 0);
    } else {
      const fx = Number(h.fx_rate || usdKrw);
      const val = Number(h.market_value_krw || 0);
      usd.market_value     += val / fx;
      usd.stock_value      += val / fx;
      usd.market_value_krw += val;
    }
  });
  accounts.forEach(a => {
    krw.cash += Number(a.cash_krw || 0);
    usd.cash += Number(a.cash_usd || 0);
  });
  krw.market_value_krw += krw.cash;
  usd.market_value     += usd.cash;
  usd.market_value_krw += usd.cash * usdKrw;
  return { KRW: krw, USD: usd };
}

function computeFilteredDayChange(holdings, rawDayChange) {
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
}

function renderWithOwner(data, owner) {
  // Always filter from rawDashboard to prevent data loss on re-render
  const src = rawDashboard || data;
  const filteredData = Object.assign({}, src);

  if (owner !== '모두') {
    // 1. Filter accounts and holdings
    filteredData.accounts = (src.accounts || []).filter(a => (a.owner || '모두') === owner);
    const ownedIds = new Set(filteredData.accounts.map(a => a.id));
    filteredData.holdings = (src.holdings || []).filter(h => ownedIds.has(h.account_id));

    // 2. Recalculate derived data from filtered set
    filteredData.summary          = computeFilteredSummary(filteredData.accounts, filteredData.holdings, src.fx_rates);
    filteredData.classifications  = computeFilteredClassifications(filteredData.holdings);
    filteredData.currency_summary = computeFilteredCurrencySummary(filteredData.holdings, filteredData.accounts, src.fx_rates);
    filteredData.day_change       = computeFilteredDayChange(filteredData.holdings, src.day_change);
  } else {
    // 모두: show everything, use server-calculated values
    filteredData.accounts         = src.accounts      || [];
    filteredData.holdings         = src.holdings      || [];
    filteredData.summary          = src.summary       || {};
    filteredData.classifications  = src.classifications || [];
    filteredData.currency_summary = src.currency_summary || {};
    filteredData.day_change       = src.day_change    || {};
  }

  render(filteredData);

  // Also reload asset records filtered by owner
  loadAssetRecords(owner);
}'''

if OLD_RWO in js:
    js = js.replace(OLD_RWO, NEW_RWO, 1)
    print('OK 1a: renderWithOwner upgraded with summary/classification recalculation')
else:
    print('WARN 1a: Could not find old renderWithOwner block')

# ── 2. Update loadAssetRecords to accept and use owner ─────────────────────
OLD_LOAD_AR = "async function loadAssetRecords() { renderAssetRecords((await api(\"/api/asset-records\")).records || []); }"
NEW_LOAD_AR = """async function loadAssetRecords(owner) {
  const ownerParam = (owner && owner !== '모두') ? `?owner=${encodeURIComponent(owner)}` : '';
  renderAssetRecords((await api(`/api/asset-records${ownerParam}`)).records || []);
}"""

if OLD_LOAD_AR in js:
    js = js.replace(OLD_LOAD_AR, NEW_LOAD_AR, 1)
    print('OK 1b: loadAssetRecords updated with owner param')
else:
    print('WARN 1b: loadAssetRecords not found exactly')

# ── 3. Update bootstrap call to loadAssetRecords (no owner yet at boot) ──
# bootstrap already calls loadAssetRecords() without args – that's fine (defaults to all)

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)
print()

# ──────────────────────────────────────────────────────────────────────────────
# 2.  main.py – update /api/asset-records GET to support owner filter
# ──────────────────────────────────────────────────────────────────────────────
with open(MAIN_PATH, 'r', encoding='utf-8') as f:
    main = f.read()

OLD_GET_AR = '@app.get("/api/asset-records")\nasync def get_asset_records() -> dict:'
NEW_GET_AR = '@app.get("/api/asset-records")\nasync def get_asset_records(owner: str = "") -> dict:'

if OLD_GET_AR in main:
    main = main.replace(OLD_GET_AR, NEW_GET_AR, 1)
    print('OK 2a: /api/asset-records GET signature updated with owner param')
else:
    print('WARN 2a: get_asset_records signature not found')

# Find the body of get_asset_records to add filtering
OLD_AR_BODY = '    records = list_asset_records()\n    return {"records": records}'
NEW_AR_BODY = (
    '    records = list_asset_records()\n'
    '    # Filter by owner if specified (records must have an owner field)\n'
    '    if owner and owner != "모두":\n'
    '        records = [r for r in records if (r.get("owner") or "모두") == owner]\n'
    '    return {"records": records}'
)
if OLD_AR_BODY in main:
    main = main.replace(OLD_AR_BODY, NEW_AR_BODY, 1)
    print('OK 2b: /api/asset-records GET body updated with owner filter')
else:
    print('WARN 2b: asset records body not found')

# Update POST /api/asset-records to save owner
OLD_AR_POST = '@app.post("/api/asset-records")\nasync def create_asset_record(payload: dict) -> dict:'
if OLD_AR_POST in main:
    # Find the function body and add owner capture
    post_idx = main.find(OLD_AR_POST)
    body_start = main.find('\n', post_idx) + 1
    # Find first 'result = upsert_asset_record' after it
    upsert_idx = main.find('upsert_asset_record', post_idx)
    if upsert_idx > 0:
        line_start = main.rfind('\n', 0, upsert_idx) + 1
        # Check if owner assignment already exists
        if 'payload["owner"]' not in main[post_idx:upsert_idx]:
            owner_line = '    payload["owner"] = payload.get("owner") or "모두"\n'
            main = main[:line_start] + owner_line + main[line_start:]
            print('OK 2c: POST /api/asset-records updated to save owner')
        else:
            print('INFO 2c: owner already in POST asset-records')
    else:
        print('WARN 2c: upsert_asset_record call not found in POST')
else:
    print('WARN 2c: POST /api/asset-records not found')

with open(MAIN_PATH, 'w', encoding='utf-8') as f:
    f.write(main)
print('\nAll done!')
