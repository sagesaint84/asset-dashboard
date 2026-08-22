#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_classification_and_records.py
1. wealth.js - computeFilteredClassifications: ETF 분리 + 현금예수금 추가
2. wealth.js - loadAssetRecords: "모두"도 owner="모두"로 필터링
"""
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# ── Fix 1: computeFilteredClassifications – proper categories + cash ──────────
OLD_CLS = '''function computeFilteredClassifications(holdings) {
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
}'''

NEW_CLS = '''// 서버 분류 로직과 동일하게 ETF/주식/해외 구분
const ETF_PREFIXES = ['KODEX','TIGER','ACE','SOL','PLUS','RISE','HANARO','KOSEF','ARIRANG','KOACT','WON'];
function classifyHolding(h) {
  const nameUpper = (h.name || '').toUpperCase();
  const market = (h.market || '').toUpperCase();
  if (h.currency === 'KRW' && ETF_PREFIXES.some(p => nameUpper.startsWith(p))) return '국내 ETF';
  if (h.currency === 'KRW') return '국내 주식';
  if (market.startsWith('NH_') && market !== 'NH_US') return '기타 해외자산';
  return '미국 주식·ETF';
}

function computeFilteredClassifications(holdings, accounts, fxRates) {
  const usdKrw = (fxRates || {})['USD'] || 1300;
  const groups = {};
  let totalValue = 0;
  holdings.forEach(h => {
    const name = classifyHolding(h);
    if (!groups[name]) groups[name] = { name, market_value_krw: 0, cost_value_krw: 0, profit_krw: 0, holding_count: 0 };
    const g = groups[name];
    g.market_value_krw += Number(h.market_value_krw || 0);
    g.cost_value_krw   += Number(h.cost_value_krw   || 0);
    g.profit_krw       += Number(h.profit_krw        || 0);
    g.holding_count    += 1;
    totalValue         += Number(h.market_value_krw || 0);
  });
  // 현금·예수금 추가
  let cashKrw = 0, cashUsd = 0;
  (accounts || []).forEach(a => {
    cashKrw += Number(a.cash_krw || 0);
    cashUsd += Number(a.cash_usd || 0);
  });
  const totalCash = cashKrw + cashUsd * usdKrw;
  if (totalCash > 0) {
    groups['현금·예수금'] = {
      name: '현금·예수금', market_value_krw: totalCash,
      cost_value_krw: totalCash, profit_krw: 0, holding_count: 0,
    };
    totalValue += totalCash;
  }
  return Object.values(groups).map(g => ({
    ...g,
    return_rate: g.cost_value_krw > 0 ? (g.profit_krw / g.cost_value_krw) * 100 : 0,
    weight: totalValue > 0 ? (g.market_value_krw / totalValue) * 100 : 0,
  }));
}'''

if OLD_CLS in js:
    js = js.replace(OLD_CLS, NEW_CLS, 1)
    print('OK 1. computeFilteredClassifications fixed (ETF + 현금예수금)')
else:
    print('WARN 1. computeFilteredClassifications not found')

# ── Fix 2: renderWithOwner – pass accounts/fxRates to computeFilteredClassifications
OLD_CLASS_CALL = '    filteredData.classifications  = computeFilteredClassifications(filteredData.holdings);'
NEW_CLASS_CALL = '    filteredData.classifications  = computeFilteredClassifications(filteredData.holdings, filteredData.accounts, src.fx_rates);'
if OLD_CLASS_CALL in js:
    js = js.replace(OLD_CLASS_CALL, NEW_CLASS_CALL, 1)
    print('OK 2. renderWithOwner passes accounts+fxRates to classification compute')
else:
    print('WARN 2. classification call in renderWithOwner not found')

# ── Fix 3: loadAssetRecords – always filter by owner (including "모두") ────────
OLD_LOAD_AR = """async function loadAssetRecords(owner) {
  const ownerParam = (owner && owner !== '모두') ? `?owner=${encodeURIComponent(owner)}` : '';
  renderAssetRecords((await api(`/api/asset-records${ownerParam}`)).records || []);
}"""
NEW_LOAD_AR = """async function loadAssetRecords(owner) {
  // 항상 owner로 필터링 ("모두"도 owner=모두 레코드만 표시)
  const o = owner || currentOwner || '모두';
  renderAssetRecords((await api(`/api/asset-records?owner=${encodeURIComponent(o)}`)).records || []);
}"""
if OLD_LOAD_AR in js:
    js = js.replace(OLD_LOAD_AR, NEW_LOAD_AR, 1)
    print('OK 3. loadAssetRecords always filters by owner')
else:
    print('WARN 3. loadAssetRecords not found')

# ── Fix 4: bootstrap also passes "모두" when loading initially ─────────────────
OLD_BOOT = 'async function bootstrap() { await loadFamilyMembers(); await loadDashboard().catch((error) => toast(error.message, true)); await loadMarkets(); await loadAssetRecords(); }'
NEW_BOOT = "async function bootstrap() { await loadFamilyMembers(); await loadDashboard().catch((error) => toast(error.message, true)); await loadMarkets(); await loadAssetRecords('모두'); }"
if OLD_BOOT in js:
    js = js.replace(OLD_BOOT, NEW_BOOT, 1)
    print('OK 4. bootstrap passes 모두 to loadAssetRecords')
else:
    print('WARN 4. bootstrap not found')

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print('\nAll JS fixes applied!')
