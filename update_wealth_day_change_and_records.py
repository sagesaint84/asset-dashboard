#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_wealth_day_change_and_records.py
- Ensure allAssetRecords is maintained
- Enhance computeFilteredDayChange to use allAssetRecords
- Ensure loadDashboard & bootstrap load allAssetRecords
"""

JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 1. allAssetRecords 전역 변수 선언
GLOBAL_DECL = "let allAssetRecords = [];\n"
if "let allAssetRecords = [];" not in js:
    js = GLOBAL_DECL + js
    print("OK 1. Declared allAssetRecords global")

# 2. computeFilteredDayChange 함수 개선
OLD_CFD = '''function computeFilteredDayChange(holdings, rawDayChange, owner, filteredSummary) {
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

NEW_CFD = '''function computeFilteredDayChange(holdings, rawDayChange, owner, filteredSummary) {
  const targetOwner = owner || '모두';
  const totalVal = filteredSummary ? Number(filteredSummary.total_value_krw || 0) : 0;
  const todayStr = new Date().toISOString().slice(0, 10);

  // 1. allAssetRecords에서 오늘 이전의 해당 구성원 최신 기록 조회
  const recList = (allAssetRecords && allAssetRecords.length > 0) ? allAssetRecords : (window.assetRecords || []);
  if (recList.length > 0 && totalVal > 0) {
    const past = recList.filter(r => (r.owner || '모두') === targetOwner && r.date && r.date < todayStr && Number(r.total_value_krw || 0) > 0);
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
    print("OK 2. Updated computeFilteredDayChange with allAssetRecords fallback")

# 3. loadAssetRecords & loadDashboard에서 allAssetRecords 갱신
OLD_LOAD_AR = '''async function loadAssetRecords(owner) {
  // 항상 owner로 필터링 ("모두"도 owner=모두 레코드만 표시)
  const o = owner || currentOwner || '모두';
  renderAssetRecords((await api(`/api/asset-records?owner=${encodeURIComponent(o)}`)).records || []);
}'''

NEW_LOAD_AR = '''async function loadAssetRecords(owner) {
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

if OLD_LOAD_AR in js:
    js = js.replace(OLD_LOAD_AR, NEW_LOAD_AR, 1)
    print("OK 3. Updated loadAssetRecords to maintain allAssetRecords")

# 4. loadDashboard에서 loadAssetRecords 동기화 후 렌더링하도록 개선
OLD_LOAD_DB = 'async function loadDashboard() { const data = await api("/api/dashboard"); rawDashboard = data; dashboard = data; renderWithOwner(data, currentOwner); }'
NEW_LOAD_DB = '''async function loadDashboard() {
  try {
    const allRes = await api('/api/asset-records');
    allAssetRecords = allRes.records || [];
  } catch (e) {}
  const data = await api("/api/dashboard");
  rawDashboard = data;
  dashboard = data;
  renderWithOwner(data, currentOwner);
}'''

if OLD_LOAD_DB in js:
    js = js.replace(OLD_LOAD_DB, NEW_LOAD_DB, 1)
    print("OK 4. Updated loadDashboard to sync allAssetRecords before render")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print("wealth.js updates complete!")
