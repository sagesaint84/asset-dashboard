#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_full_wealth_js.py
Generates the clean, full-featured wealth.js file with zero syntax errors.
"""

JS_CONTENT = r'''let allAssetRecords = [];
let assetRecords = [];
let currentRecordPeriod = 'ALL'; // '1M' | '3M' | '6M' | '1Y' | 'ALL'
let currentRecordView = 'combo'; // 'combo' | 'monthly'
let currentAllocTab = 'asset_class'; // 'asset_class' | 'sector'
let currentStockChartCode = '';
let currentStockChartName = '';
let currentStockChartPrice = 0;
let currentStockChartCurrency = 'KRW';
let currentStockChartPeriod = '3M'; // '1W' | '1M' | '3M' | 'YTD' | '1Y'
let holdingSortField = 'market_value_krw';
let holdingSortOrder = 'desc'; // 'asc' | 'desc'

const $ = (selector) => document.querySelector(selector);
let dashboard = null;
let rawDashboard = null; // 필터링 전 원본 서버 데이터
let currentOwner = '모두'; // 선택된 가족 구성원

// ── 가족 구성원 선택 – 탑바 + ACCOUNTS 탭 동기화 ─────────────────────────────
function selectOwner(owner) {
  currentOwner = owner || '모두';
  document.querySelectorAll('#familyTabs .family-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.owner === currentOwner);
  });
  document.querySelectorAll('#topbarFamilyTabs .family-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.owner === currentOwner);
  });
  if (rawDashboard) renderWithOwner(rawDashboard, currentOwner);
}

document.addEventListener('click', (e) => {
  const accountsTab = e.target.closest('#familyTabs .family-tab');
  if (accountsTab) { selectOwner(accountsTab.dataset.owner); return; }
  const topbarTab = e.target.closest('#topbarFamilyTabs .family-tab');
  if (topbarTab) { selectOwner(topbarTab.dataset.owner); return; }
});

// ── 필터링된 데이터로 핵심 요약 재계산 ──────────────────────────────────────
function computeFilteredSummary(accounts, holdings, fxRates) {
  const usdKrw = (fxRates || {})['USD'] || 1385;
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
  const usdKrw = (fxRates || {})['USD'] || 1385;
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
  })).sort((a, b) => b.market_value_krw - a.market_value_krw);
}

function computeFilteredSectors(holdings, accounts, fxRates) {
  const usdKrw = (fxRates || {})['USD'] || 1385;
  const groups = {};
  let totalValue = 0;
  holdings.forEach(h => {
    const sec = h.sector || '기타';
    if (!groups[sec]) groups[sec] = { name: sec, market_value_krw: 0, cost_value_krw: 0, profit_krw: 0, holding_count: 0 };
    const g = groups[sec];
    g.market_value_krw += Number(h.market_value_krw || 0);
    g.cost_value_krw   += Number(h.cost_value_krw   || 0);
    g.profit_krw       += Number(h.profit_krw        || 0);
    g.holding_count    += 1;
    totalValue         += Number(h.market_value_krw || 0);
  });
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
  })).sort((a, b) => b.market_value_krw - a.market_value_krw);
}

function computeFilteredCurrencySummary(holdings, accounts, fxRates) {
  const usdKrw = (fxRates || {})['USD'] || 1385;
  let krwStock = 0, usdStock = 0;
  let krwCash = 0, usdCash = 0;
  holdings.forEach(h => {
    if (h.currency === 'KRW') krwStock += Number(h.market_value_krw || 0);
    else usdStock += Number(h.market_value || (Number(h.market_value_krw || 0) / usdKrw));
  });
  accounts.forEach(a => {
    krwCash += Number(a.cash_krw || 0);
    usdCash += Number(a.cash_usd || 0);
  });
  return {
    KRW: {
      currency: 'KRW',
      stock_value_krw: krwStock,
      cash: krwCash,
      market_value_krw: krwStock + krwCash,
    },
    USD: {
      currency: 'USD',
      stock_value: usdStock,
      cash: usdCash,
      market_value: usdStock + usdCash,
      market_value_krw: (usdStock + usdCash) * usdKrw,
    },
  };
}

function computeFilteredDayChange(holdings, rawDayChange) {
  if (!rawDayChange) return {};
  let totalValue = 0, weightedChange = 0;
  holdings.forEach(h => {
    const val = Number(h.market_value_krw || 0);
    const rate = Number(h.day_change_rate || 0);
    totalValue += val;
    weightedChange += val * rate;
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
  const src = rawDashboard || data;
  const filteredData = Object.assign({}, src);

  if (owner !== '모두') {
    filteredData.accounts = (src.accounts || []).filter(a => (a.owner || '모두') === owner);
    const ownedIds = new Set(filteredData.accounts.map(a => a.id));
    filteredData.holdings = (src.holdings || []).filter(h => ownedIds.has(h.account_id));

    filteredData.summary               = computeFilteredSummary(filteredData.accounts, filteredData.holdings, src.fx_rates);
    filteredData.classifications       = computeFilteredClassifications(filteredData.holdings, filteredData.accounts, src.fx_rates);
    filteredData.sector_classifications= computeFilteredSectors(filteredData.holdings, filteredData.accounts, src.fx_rates);
    filteredData.currency_summary      = computeFilteredCurrencySummary(filteredData.holdings, filteredData.accounts, src.fx_rates);
    filteredData.day_change            = computeFilteredDayChange(filteredData.holdings, src.day_change);
  } else {
    filteredData.accounts              = src.accounts               || [];
    filteredData.holdings              = src.holdings               || [];
    filteredData.summary               = src.summary                || {};
    filteredData.classifications       = src.classifications        || [];
    filteredData.sector_classifications= src.sector_classifications || [];
    filteredData.currency_summary      = src.currency_summary       || {};
    filteredData.day_change            = src.day_change             || {};
  }

  render(filteredData);
  loadAssetRecords(owner);
}

// 다이얼로그 닫기 버튼 공통 처리
document.addEventListener("click", (event) => {
  const button = event.target.closest(".dialog .close, .dialog .dialog-actions button[value='cancel']");
  if (!button) return;
  event.preventDefault();
  button.closest("dialog")?.close();
});

const number = (value, digits = 2) => Number(value || 0).toLocaleString("ko-KR", { maximumFractionDigits: digits });
const money = (value, currency = "KRW") => {
  try { return new Intl.NumberFormat("ko-KR", { style: "currency", currency, maximumFractionDigits: currency === "KRW" ? 0 : 2 }).format(Number(value || 0)); }
  catch { return number(value); }
};
const html = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
const signClass = (value) => Number(value) < 0 ? "down" : "up";

function sparkline(points, change) {
  if (!points || points.length < 2) {
    if (points && points.length === 1) points = [points[0], points[0]];
    else return "<span class=\"spark-empty\">—</span>";
  }
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || (min * 0.01) || 1;
  const h = 42;
  const w = 110;
  const pad = 4;

  const coords = points.map((point, index) => {
    const x = (index / (points.length - 1)) * (w - pad * 2) + pad;
    const y = (h - pad) - ((point - min) / span) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const polylineStr = coords.join(" ");
  const lastCoord = coords[coords.length - 1].split(",");
  const lastX = lastCoord[0];
  const lastY = lastCoord[1];

  const isUp = Number(change) > 0;
  const isDown = Number(change) < 0;
  const color = isUp ? "#ff5c77" : (isDown ? "#4f9dff" : "#98a6c8");

  return `
    <svg class="sparkline" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
      <polyline points="${polylineStr}" fill="none" stroke="${color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="${lastX}" cy="${lastY}" r="3" fill="${color}" />
    </svg>
  `;
}

async function api(url, options = {}) {
  options.credentials = options.credentials || 'include';
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.location.href = '/login';
    throw new Error('로그인이 필요합니다.');
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || result.message || "요청을 처리하지 못했습니다.");
  return result;
}

let toastTimer;
function toast(message, isError = false) {
  const element = $("#toast");
  if (!element) return;
  element.textContent = message;
  element.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { element.className = "toast"; }, 3600);
}

function busy(button, enabled) {
  if (!button) return;
  button.dataset.label ??= button.textContent;
  button.disabled = enabled;
  button.textContent = enabled ? "처리 중…" : button.dataset.label;
}

async function action(button, request, after = loadDashboard) {
  busy(button, true);
  try {
    const result = await request();
    toast(result.message || "반영했습니다.");
    if (after) await after();
  } catch (error) {
    toast(error.message, true);
  } finally {
    busy(button, false);
  }
}

// ── 기간별 자산기록 필터링 ──────────────────────────────────────────────────
function filterRecordsByPeriod(records, period) {
  if (!records || !records.length || period === 'ALL') return records || [];
  const now = new Date();
  let days = 30;
  if (period === '1M') days = 30;
  else if (period === '3M') days = 90;
  else if (period === '6M') days = 180;
  else if (period === '1Y') days = 365;

  const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  return records.filter(r => r.date && r.date >= cutoff);
}

// ── 1. 주요 지수 렌더링 ──────────────────────────────────────────────────────
function renderMarkets(result) {
  const mkts = result?.markets || [];
  const fx = result?.exchange_rate || {};
  const rows = [
    ...mkts.map(m => ({
      symbol: m.symbol,
      label: m.label || m.name,
      price: m.price != null ? m.price : m.current_price,
      currency: m.currency || 'KRW',
      change: m.change != null ? m.change : m.change_price,
      change_rate: m.change_rate,
      series: m.series || [m.price || 0],
    })),
    {
      symbol: "USD/KRW",
      label: "달러 환율",
      price: fx.rate,
      currency: "KRW",
      change: fx.change != null ? fx.change : fx.change_price,
      change_rate: fx.change_rate,
      series: fx.series || [fx.rate || 1385],
    },
  ];

  const grid = $("#marketGrid");
  if (!grid) return;

  grid.innerHTML = rows.map((item) => {
    const isFx = item.symbol === "USD/KRW";
    const priceText = isFx ? `${number(item.price, 1)}원` : number(item.price, 2);

    const isUp = Number(item.change_rate) > 0;
    const isDown = Number(item.change_rate) < 0;
    const sign = isUp ? "+" : "";
    const colorClass = isUp ? "up" : (isDown ? "down" : "");

    let changeText = "";
    if (item.change_rate != null) {
      const changeNum = item.change != null ? `${sign}${number(item.change, 2)}` : "";
      const rateNum = `(${sign}${number(item.change_rate, 2)}%)`;
      changeText = changeNum ? `${changeNum} ${rateNum}` : rateNum;
    } else {
      changeText = "—";
    }

    const chartHtml = sparkline(item.series, item.change_rate);

    return `
      <article class="market-card toss-market-card">
        <div class="market-chart-col">
          ${chartHtml}
        </div>
        <div class="market-info-col">
          <div class="market-title-row">
            <strong class="market-title">${html(item.label)}</strong>
          </div>
          <div class="market-value-row">
            <strong class="market-price ${colorClass}">${priceText}</strong>
            <span class="market-change ${colorClass}">${changeText}</span>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

async function loadMarkets() {
  try { renderMarkets(await api("/api/market-overview")); }
  catch (error) {
    const grid = $("#marketGrid");
    if (grid) grid.innerHTML = `<article class="market-card"><p>시장 스냅샷을 불러오지 못했습니다.</p><small>${html(error.message)}</small></article>`;
  }
}

// ── 2. 핵심 요약 렌더링 ──────────────────────────────────────────────────────
function renderSummary(data) {
  const s = data.summary || {}, currencies = data.currency_summary || {};
  const krw = currencies.KRW || {}, usd = currencies.USD || {};

  $("#totalValue").textContent = money(s.total_value_krw);
  const cashNote = s.total_cash_krw ? `주식 ${money(s.total_stock_value_krw || (s.total_value_krw - s.total_cash_krw))} · 예수금 ${money(s.total_cash_krw)}` : `보유 종목 ${number(s.holding_count, 0)}개 · ${number(s.account_count, 0)}개 계좌`;
  $("#holdingCaption").textContent = cashNote;

  $("#totalProfit").textContent = money(s.profit_krw);
  $("#totalProfit").className = signClass(s.profit_krw);
  const profitRateEl = $("#profitRate");
  if (profitRateEl) {
    profitRateEl.textContent = `(${s.return_rate >= 0 ? "+" : ""}${number(s.return_rate)}%)`;
    profitRateEl.className = `sub-rate ${signClass(s.profit_krw)}`;
  }
  $("#profitCaption").textContent = `총 매입 ${money(s.total_cost_krw)}`;

  const day = data.day_change || {};
  $("#dayProfit").textContent = day.change_krw == null ? "—" : `${day.change_krw >= 0 ? "+" : ""}${money(day.change_krw)}`;
  $("#dayProfit").className = day.change_krw == null ? "" : signClass(day.change_krw);
  const dayRateEl = $("#dayRate");
  if (dayRateEl) {
    dayRateEl.textContent = day.change_rate == null ? "" : `(${day.change_rate >= 0 ? "+" : ""}${number(day.change_rate)}%)`;
    dayRateEl.className = day.change_rate == null ? "sub-rate" : `sub-rate ${signClass(day.change_krw)}`;
  }
  $("#dayCaption").textContent = day.change_krw == null ? "전일 기준 데이터 수집 중" : `${day.date} 대비`;

  const krwStock = krw.stock_value_krw || (Number(krw.market_value_krw || 0) - Number(krw.cash || 0));
  $("#krwValue").textContent = money(krw.market_value_krw || 0);
  const krwCashBadgeEl = $("#krwCashBadge");
  if (krwCashBadgeEl) krwCashBadgeEl.textContent = `(예수금 ${money(krw.cash || 0)})`;
  $("#krwCaption").textContent = `주식 평가 ${money(krwStock)}`;

  const usdStock = usd.stock_value || (Number(usd.market_value || 0) - Number(usd.cash || 0));
  $("#usdValue").textContent = money(usd.market_value || 0, "USD");
  const usdCashBadgeEl = $("#usdCashBadge");
  if (usdCashBadgeEl) usdCashBadgeEl.textContent = `(예수금 ${money(usd.cash || 0, "USD")})`;
  $("#usdCaption").textContent = `주식 평가 ${money(usdStock, "USD")} (환산 ${money(usd.market_value_krw || 0)})`;

  $("#updatedAt") && ($("#updatedAt").textContent = data.updated_at ? `마지막 자산 반영 ${new Date(data.updated_at).toLocaleString("ko-KR")}` : "아직 보유종목이 없습니다.");
  const cashSuffix = s.total_cash_krw ? ` (예수금 ${money(s.total_cash_krw)} 포함)` : "";
  $("#accountCaption") && ($("#accountCaption").textContent = `전체 ${number(s.account_count, 0)}개 계좌 통합${cashSuffix}`);
}

// ── 3. 투자자산 분류 & 섹터별 도넛 원그래프 ──────────────────────────────────
const SECTOR_COLORS = [
  '#8e70fa', '#38bdf8', '#34d399', '#f59e0b', '#ec4899',
  '#a78bfa', '#06b6d4', '#10b981', '#f97316', '#fb7185',
  '#6366f1', '#14b8a6', '#84cc16', '#eab308', '#d946ef', '#64748b'
];

function renderSectorDonut(sectors) {
  const wrap = $("#sectorDonutWrap");
  if (!wrap) return;

  const validSectors = (sectors || []).filter(s => s.market_value_krw > 0);
  if (!validSectors.length) {
    wrap.innerHTML = '<div class="empty">섹터별 투자자산 데이터가 없습니다.</div>';
    return;
  }

  const total = validSectors.reduce((sum, s) => sum + s.market_value_krw, 0);
  const size = 140, r = 54, cx = 70, cy = 70, strokeWidth = 24;
  const circumference = 2 * Math.PI * r;

  let offset = 0;
  const slices = validSectors.map((s, idx) => {
    const pct = s.market_value_krw / total;
    const dash = pct * circumference;
    const color = SECTOR_COLORS[idx % SECTOR_COLORS.length];
    const el = `
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="${strokeWidth}"
        stroke-dasharray="${dash.toFixed(2)} ${(circumference - dash).toFixed(2)}"
        stroke-dashoffset="${(-offset).toFixed(2)}" stroke-linecap="round">
        <title>${s.name}: ${money(s.market_value_krw)} (${(pct * 100).toFixed(1)}%)</title>
      </circle>
    `;
    offset += dash;
    return el;
  }).join('');

  const topSectors = validSectors.slice(0, 6);
  const legendHtml = topSectors.map((s, idx) => {
    const color = SECTOR_COLORS[idx % SECTOR_COLORS.length];
    return `
      <div class="sector-legend-item">
        <span style="display:flex;align-items:center;gap:6px;">
          <i class="sector-legend-color" style="background:${color};"></i>
          <strong>${html(s.name)}</strong>
        </span>
        <span class="muted">${number(s.weight, 1)}%</span>
      </div>
    `;
  }).join('');

  wrap.innerHTML = `
    <div class="sector-donut-container">
      <div class="sector-donut-svg-wrap">
        <svg class="sector-donut-svg" viewBox="0 0 ${size} ${size}">
          ${slices}
        </svg>
      </div>
      <div class="sector-legend-list">
        ${legendHtml}
      </div>
    </div>
  `;
}

function renderClassifications(items) {
  const list = $("#classificationList");
  const donutWrap = $("#sectorDonutWrap");
  if (!list) return;

  if (currentAllocTab === 'sector') {
    if (donutWrap) donutWrap.style.display = 'block';
    const sectors = dashboard?.sector_classifications || [];
    renderSectorDonut(sectors);
    list.innerHTML = sectors.length ? sectors.map((item) => `
      <div class="classification-row">
        <div class="classification-title">
          <strong>${html(item.name)}</strong>
          <span>${number(item.holding_count, 0)}종목 · ${number(item.weight, 1)}%</span>
        </div>
        <div class="classification-value">
          <span>${money(item.market_value_krw)}</span>
          <b class="${signClass(item.profit_krw)}">${item.return_rate >= 0 ? "+" : ""}${number(item.return_rate, 2)}%</b>
        </div>
        <div class="bar"><i style="width:${Math.min(item.weight, 100)}%"></i></div>
      </div>
    `).join("") : '<div class="empty">섹터별 투자자산 데이터가 없습니다.</div>';
  } else {
    if (donutWrap) donutWrap.style.display = 'none';
    const classes = dashboard?.classifications || items || [];
    list.innerHTML = classes.length ? classes.map((item) => `
      <div class="classification-row">
        <div class="classification-title">
          <strong>${html(item.name)}</strong>
          <span>${number(item.holding_count, 0)}종목 · ${number(item.weight, 1)}%</span>
        </div>
        <div class="classification-value">
          <span>${money(item.market_value_krw)}</span>
          <b class="${signClass(item.profit_krw)}">${item.return_rate >= 0 ? "+" : ""}${number(item.return_rate, 2)}%</b>
        </div>
        <div class="bar"><i style="width:${Math.min(item.weight, 100)}%"></i></div>
      </div>
    `).join("") : '<div class="empty">자산을 불러오면 분류별 수익률을 표시합니다.</div>';
  }
}

// ── 4. 계좌 목록 렌더링 ──────────────────────────────────────────────────────
function renderAccounts(items) {
  const container = $("#accountList");
  if (!container) return;
  if (!items || !items.length) { container.innerHTML = '<div class="empty">동기화된 계좌가 없습니다.</div>'; return; }
  const groups = new Map();
  items.forEach((item) => {
    const current = groups.get(item.broker) || { broker: item.broker, count: 0, items: [] };
    current.count += 1;
    current.items.push(item);
    groups.set(item.broker, current);
  });
  container.innerHTML = [...groups.values()].map((group) => {
    const accounts = group.items.map((account) => {
      const parts = [];
      if (account.cash_krw) parts.push(`₩${number(account.cash_krw)}`);
      if (account.cash_usd) parts.push(`$${number(account.cash_usd, 2)}`);
      const cashText = parts.length ? ` · 예수금 ${parts.join(" / ")}` : "";
      return `<div class="account-row"><div class="account-row-info"><strong>${html(account.name)}</strong><span>${number(account.holding_count, 0)}종목${cashText}</span></div><div class="account-row-actions"><button class="account-action-button" data-cash-id="${account.id}" type="button">예수금</button><button class="account-action-button" data-account-id="${account.id}" type="button">수정</button><button class="mini-delete-button" data-account-del-id="${account.id}" title="계좌 삭제" type="button">×</button></div></div>`;
    }).join("");
    return `<section class="broker-group"><div class="broker-head"><strong>${html(group.broker)}</strong><span>${number(group.count, 0)}개 계좌</span></div><div class="broker-accounts">${accounts}</div></section>`;
  }).join("");
}

// ── 5. 자산 히트맵 ───────────────────────────────────────────────────────────
let heatmapPeriod = localStorage.getItem("heatmap_period") || "1D";
let heatmapTheme = localStorage.getItem("heatmap_theme") || "kr";
let heatmapMaxCap = localStorage.getItem("heatmap_max_cap") || "auto";

function getEffectiveCap(period, capSetting) {
  if (capSetting && capSetting !== "auto") return Number(capSetting);
  const caps = { "1D": 5, "1W": 10, "1M": 15, "YTD": 20, "1Y": 30, "TOTAL": 30 };
  return caps[period] || 15;
}

function getRateForPeriod(holding, period) {
  if (period === "TOTAL") {
    const cost = Number(holding.cost_value_krw || 0);
    const profit = Number(holding.profit_krw || 0);
    return cost > 0 ? (profit / cost) * 100 : 0;
  }
  const multi = dashboard?.settings?.period_rates || {};
  const code = (holding.code || "").toUpperCase();
  if (multi[code] && multi[code][period] != null) return Number(multi[code][period]);
  if (period === "1D") return Number(holding.day_change_rate || 0);
  return Number(holding.day_change_rate || 0);
}

function squarify(children, x, y, width, height) {
  if (!children.length) return [];
  const total = children.reduce((s, it) => s + it.value, 0);
  if (total <= 0) return [];
  return children.map((it, idx) => {
    const w = width / children.length;
    return {
      item: it,
      x: x + idx * w,
      y: y,
      dx: w - 2,
      dy: height - 2,
    };
  });
}

function renderHeatmaps(data) {
  const container = $("#assetHeatmapContainer");
  if (!container) return;
  const holdings = data?.holdings || [];
  if (!holdings.length) {
    container.innerHTML = '<div class="empty">보유종목이 없습니다.</div>';
    return;
  }

  const items = holdings.map(h => ({
    name: h.name,
    code: h.code,
    value: Number(h.market_value_krw || 0),
    rate: getRateForPeriod(h, heatmapPeriod),
  })).filter(it => it.value > 0).sort((a, b) => b.value - a.value);

  const maxCap = getEffectiveCap(heatmapPeriod, heatmapMaxCap);
  const legLeft = $("#legendCapLeft");
  const legRight = $("#legendCapRight");
  if (legLeft) legLeft.textContent = `-${maxCap}%`;
  if (legRight) legRight.textContent = `+${maxCap}%`;

  const tiles = items.slice(0, 30);
  container.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:6px;padding:8px;">
      ${tiles.map(it => {
        const isUp = it.rate >= 0;
        const color = isUp ? 'rgba(255, 92, 119, 0.22)' : 'rgba(79, 157, 255, 0.22)';
        const borderColor = isUp ? '#ff5c77' : '#4f9dff';
        return `
          <div style="background:${color};border:1px solid ${borderColor};border-radius:6px;padding:8px 10px;display:flex;flex-direction:column;justify-content:space-between;min-height:64px;cursor:pointer;"
            onclick="$('#searchInput').value='${it.name}';renderHoldings(dashboard);">
            <strong style="font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${html(it.name)}</strong>
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:4px;">
              <small class="muted" style="font-size:10px;">${money(it.value)}</small>
              <b class="${signClass(it.rate)}" style="font-size:12px;">${it.rate >= 0 ? '+' : ''}${number(it.rate, 2)}%</b>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

// ── 6. 보유종목 테이블 (정렬 + 섹터 뱃지 + 인터랙티브 차트 모달) ─────────────
function renderHoldings(data) {
  const query = $("#searchInput")?.value.trim().toLowerCase() || "";
  const rows = (data.holdings || []).filter((item) =>
    [item.name, item.code, item.broker, item.account_name, item.sector].join(" ").toLowerCase().includes(query)
  );

  const groups = new Map();
  rows.forEach((item) => {
    const key = `${item.code}|${item.currency}|${item.name}`;
    const group = groups.get(key) || {
      ...item,
      quantity: 0,
      market_value_krw: 0,
      cost_value_krw: 0,
      profit_krw: 0,
      day_change_rate: item.day_change_rate || 0,
      sector: item.sector || '기타',
      items: [],
    };
    group.quantity += Number(item.quantity || 0);
    group.market_value_krw += Number(item.market_value_krw || 0);
    group.cost_value_krw += Number(item.cost_value_krw || 0);
    group.profit_krw += Number(item.profit_krw || 0);
    group.items.push(item);
    groups.set(key, group);
  });

  let sorted = [...groups.values()].map(item => {
    const rate = item.cost_value_krw ? (item.profit_krw / item.cost_value_krw) * 100 : 0;
    return { ...item, return_rate: rate };
  });

  // 다중 컬럼 정렬
  sorted.sort((a, b) => {
    let valA = a[holdingSortField];
    let valB = b[holdingSortField];

    if (holdingSortField === 'name' || holdingSortField === 'sector' || holdingSortField === 'account') {
      valA = String(valA || '').toLowerCase();
      valB = String(valB || '').toLowerCase();
      return holdingSortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    valA = Number(valA || 0);
    valB = Number(valB || 0);
    return holdingSortOrder === 'asc' ? valA - valB : valB - valA;
  });

  // 헤더 정렬 아이콘 클래스 갱신
  document.querySelectorAll('.sortable-th').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.sort === holdingSortField) {
      th.classList.add(holdingSortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
    }
  });

  const tbody = $("#holdingsBody");
  if (!tbody) return;

  tbody.innerHTML = sorted.map((item) => {
    const dayRate = Number(item.day_change_rate || 0);
    const accounts = item.items.map((detail) => `
      <span class="holding-account-detail">
        ${html(detail.broker)} ${html(detail.account_name)} ${number(detail.quantity, 4)}주
        <button class="mini-edit-button edit-button" data-id="${detail.id}" title="수정" type="button">✎</button>
        <button class="mini-edit-button delete-button" data-id="${detail.id}" title="삭제" type="button">×</button>
      </span>
    `).join("");

    return `
      <tr data-code="${html(item.code)}">
        <td class="holding-name-cell">
          <strong class="holding-name-link" data-code="${html(item.code)}" data-name="${html(item.name)}" data-price="${item.current_price}" data-currency="${item.currency}">
            ${html(item.name)}
          </strong>
          <small>${html(item.code)} · ${html(item.market || item.currency)}</small>
        </td>
        <td>
          <span class="sector-badge">${html(item.sector || '기타')}</span>
        </td>
        <td class="holding-accounts">${accounts}</td>
        <td>${number(item.quantity, 4)}</td>
        <td><strong>${money(item.market_value_krw)}</strong></td>
        <td class="${signClass(item.profit_krw)}">${item.profit_krw >= 0 ? "+" : ""}${money(item.profit_krw)}</td>
        <td class="${signClass(item.return_rate)}">${item.return_rate >= 0 ? "+" : ""}${number(item.return_rate, 2)}%</td>
        <td class="${signClass(dayRate)}">${dayRate >= 0 ? "+" : ""}${number(dayRate, 2)}%</td>
        <td style="text-align:center;">
          <button class="stock-chart-btn" data-code="${html(item.code)}" data-name="${html(item.name)}" data-price="${item.current_price}" data-currency="${item.currency}" title="인터랙티브 차트" type="button">
            📊
          </button>
        </td>
      </tr>
    `;
  }).join("");

  $("#emptyHoldings") && ($("#emptyHoldings").hidden = sorted.length > 0);
  $(".table-wrap") && ($(".table-wrap").hidden = sorted.length === 0);
}

// ── 7. 종목 가격 & 거래량 인터랙티브 차트 모달 ──────────────────────────────
async function openStockChart(code, name, price, currency = 'KRW') {
  currentStockChartCode = code;
  currentStockChartName = name || code;
  currentStockChartPrice = Number(price || 0);
  currentStockChartCurrency = currency || 'KRW';

  const dlg = $("#stockChartDialog");
  if (!dlg) return;

  $("#stockChartTitle").textContent = currentStockChartName;
  $("#stockChartCode").textContent = `${currentStockChartCode} · ${currentStockChartCurrency}`;
  $("#stockChartPrice").textContent = money(currentStockChartPrice, currentStockChartCurrency);
  $("#stockChartChange").textContent = "데이터 조회 중…";

  // 탭 활성화 상태 동기화
  document.querySelectorAll('#stockChartPeriodTabs .heatmap-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.period === currentStockChartPeriod);
  });

  dlg.showModal();
  await loadStockChartData();
}

async function loadStockChartData() {
  const container = $("#stockChartContainer");
  if (!container) return;
  container.innerHTML = '<div class="empty">차트 데이터를 불러오는 중입니다…</div>';

  try {
    const res = await api(`/api/stock-chart/${encodeURIComponent(currentStockChartCode)}?period=${currentStockChartPeriod}`);
    const candles = res?.candles || [];
    if (!candles.length) {
      container.innerHTML = '<div class="empty">조회 가능한 캔들 차트 데이터가 없습니다.</div>';
      return;
    }

    const prices = candles.map(c => c.close);
    const volumes = candles.map(c => c.volume || 0);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const maxVol = Math.max(...volumes, 1);
    const spanPrice = maxPrice - minPrice || (minPrice * 0.02) || 1;

    const w = 680, h = 260, pad = 20;
    const hPriceArea = 170;
    const hVolTop = hPriceArea + 20;
    const hVolArea = h - hVolTop - 15;

    // 가격 라인
    const pricePoints = candles.map((c, idx) => {
      const x = pad + ((w - pad * 2) * idx) / Math.max(candles.length - 1, 1);
      const y = pad + (hPriceArea - pad) * (1 - (c.close - minPrice) / spanPrice);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const pricePath = pricePoints.join(" ");
    const priceAreaPath = `${pricePath} ${(w - pad)},${hPriceArea} ${pad},${hPriceArea}`;

    // 거래량 바
    const barWidth = Math.max(2, Math.min(14, (w - pad * 2) / candles.length - 2));
    const volBars = candles.map((c, idx) => {
      const x = pad + ((w - pad * 2) * idx) / Math.max(candles.length - 1, 1) - barWidth / 2;
      const volH = Math.max(2, (c.volume / maxVol) * hVolArea);
      const y = h - 15 - volH;
      const isUp = idx === 0 ? true : (c.close >= candles[idx - 1].close);
      const color = isUp ? '#ff5c77' : '#4f9dff';
      return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${volH.toFixed(1)}" fill="${color}" opacity="0.75" rx="1" />`;
    }).join('');

    const first = candles[0];
    const last = candles[candles.length - 1];
    const diff = last.close - first.close;
    const diffRate = first.close > 0 ? (diff / first.close) * 100 : 0;
    const isGain = diff >= 0;

    $("#stockChartPrice").textContent = money(last.close, currentStockChartCurrency);
    $("#stockChartChange").textContent = `${isGain ? "+" : ""}${money(diff, currentStockChartCurrency)} (${isGain ? "+" : ""}${number(diffRate, 2)}%)`;
    $("#stockChartChange").className = `sub-rate ${signClass(diff)}`;

    container.innerHTML = `
      <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:260px;overflow:visible;">
        <defs>
          <linearGradient id="stockPriceGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#8e70fa" stop-opacity="0.32" />
            <stop offset="100%" stop-color="#8e70fa" stop-opacity="0.0" />
          </linearGradient>
        </defs>
        <!-- 가격 영역 -->
        <polygon points="${priceAreaPath}" fill="url(#stockPriceGrad)" />
        <polyline points="${pricePath}" fill="none" stroke="#8e70fa" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
        <text x="${pad}" y="${pad + 4}" fill="#7182a6" font-size="10">최고 ${money(maxPrice, currentStockChartCurrency)}</text>
        <text x="${pad}" y="${hPriceArea - 4}" fill="#7182a6" font-size="10">최저 ${money(minPrice, currentStockChartCurrency)}</text>
        
        <!-- 거래량 영역 -->
        <line x1="${pad}" y1="${hVolTop - 5}" x2="${w - pad}" y2="${hVolTop - 5}" stroke="#1f2c4d" stroke-dasharray="2,2" />
        <text x="${pad}" y="${hVolTop + 8}" fill="#7182a6" font-size="9" font-weight="700">거래량 (VOLUME)</text>
        ${volBars}
      </svg>
      <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:11px;color:#7182a6;">
        <span>${first.date}</span>
        <span>${candles.length}개 거래일</span>
        <span>${last.date}</span>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty">차트 로드 실패: ${html(err.message)}</div>`;
  }
}

// ── 8. 자산기록 렌더링 (콤보 차트 vs 월별 자산 뷰) ───────────────────────────
function renderAssetRecords(records) {
  assetRecords = records || [];
  window.assetRecords = records || [];

  const rawList = [...records].sort((a, b) => String(a.date || '').localeCompare(String(b.date || '')));
  const filtered = filterRecordsByPeriod(rawList, currentRecordPeriod);
  const wrap = $("#assetChart");

  if (!filtered.length) {
    if (wrap) wrap.innerHTML = '<div class="empty">선택한 기간의 자산기록이 없습니다.</div>';
    $("#assetRecordList") && ($("#assetRecordList").innerHTML = "");
    $("#recordCount") && ($("#recordCount").textContent = "0개 기록");
    return;
  }

  // 뷰 모드 1: 월별 자산 막대 차트
  if (currentRecordView === 'monthly') {
    const monthlyMap = new Map();
    filtered.forEach(r => {
      if (!r.date) return;
      const ym = r.date.slice(0, 7); // 'YYYY-MM'
      monthlyMap.set(ym, r); // 마지막 날짜로 덮어씀
    });
    const monthlyList = [...monthlyMap.entries()].sort((a, b) => a[0].localeCompare(b[0]));

    let prevVal = 0;
    const cardsHtml = monthlyList.map(([ym, item]) => {
      const val = Number(item.total_value_krw || 0);
      const delta = prevVal ? val - prevVal : 0;
      const deltaRate = prevVal ? (delta / prevVal) * 100 : 0;
      prevVal = val;
      const isGain = delta >= 0;

      return `
        <div class="monthly-bar-card">
          <span class="month-label">${ym}</span>
          <strong class="month-val">${money(val)}</strong>
          <span class="month-delta ${signClass(delta)}" style="font-size:11px;">
            ${delta !== 0 ? (isGain ? '+' : '') + money(delta) + ' (' + (isGain ? '+' : '') + number(deltaRate, 1) + '%)' : '기준월'}
          </span>
          <small class="muted" style="font-size:10px;">${item.holding_count || 0}종목</small>
        </div>
      `;
    }).join('');

    if (wrap) {
      wrap.innerHTML = `
        <div style="padding:4px 0 10px;font-size:12px;font-weight:700;color:#c4b5fd;">
          📊 월별 말일 기준 자산 추이 (${monthlyList.length}개월)
        </div>
        <div class="monthly-records-grid">
          ${cardsHtml}
        </div>
      `;
    }
  } else {
    // 뷰 모드 2: 총자산 선 + 0선 기준 손익 막대 콤보 차트
    const values = filtered.map(item => Number(item.total_value_krw || 0));
    const profits = filtered.map(item => Number(item.day_profit_krw || 0));

    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const spanVal = maxVal - minVal || (minVal * 0.05) || 1;
    const maxAbsProfit = Math.max(...profits.map(Math.abs), 100000);

    const w = 900, h = 280, pad = 24;
    const hLineArea = 160;

    const linePoints = filtered.map((pt, i) => {
      const x = pad + ((w - pad * 2) * i) / Math.max(filtered.length - 1, 1);
      const y = pad + (hLineArea - pad) * (1 - (Number(pt.total_value_krw || 0) - minVal) / spanVal);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const linePath = linePoints.join(" ");
    const lineAreaPath = `${linePath} ${(w - pad)},${hLineArea} ${pad},${hLineArea}`;

    const hBarAreaTop = hLineArea + 25;
    const hBarAreaHeight = h - hBarAreaTop - pad;
    const zeroY = hBarAreaTop + (hBarAreaHeight / 2);

    const barWidth = Math.max(3, Math.min(18, (w - pad * 2) / filtered.length - 3));
    const bars = filtered.map((pt, i) => {
      const x = pad + ((w - pad * 2) * i) / Math.max(filtered.length - 1, 1) - barWidth / 2;
      const p = Number(pt.day_profit_krw || 0);
      const isGain = p >= 0;
      const barH = Math.max(2, (Math.abs(p) / maxAbsProfit) * (hBarAreaHeight / 2 - 4));
      const y = isGain ? (zeroY - barH) : zeroY;
      const color = isGain ? '#ff5c77' : '#4f9dff';
      return `
        <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barH.toFixed(1)}" fill="${color}" opacity="0.85" rx="1.5">
          <title>${pt.date}: ${isGain ? '+' : ''}${money(p)}</title>
        </rect>
      `;
    }).join('');

    const first = filtered[0];
    const last = filtered.at(-1);

    if (wrap) {
      wrap.innerHTML = `
        <div style="display:flex;justify-content:flex-end;gap:14px;margin-bottom:8px;font-size:11px;">
          <span style="display:flex;align-items:center;gap:4px;"><i style="display:inline-block;width:12px;height:3px;background:#8e70fa;border-radius:2px;"></i> 총 자산 (선)</span>
          <span style="display:flex;align-items:center;gap:4px;"><i style="display:inline-block;width:8px;height:8px;background:#ff5c77;border-radius:2px;"></i> 일간 수익 (+)</span>
          <span style="display:flex;align-items:center;gap:4px;"><i style="display:inline-block;width:8px;height:8px;background:#4f9dff;border-radius:2px;"></i> 일간 손실 (-)</span>
        </div>
        <svg class="record-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-label="자산 기록 콤보 차트">
          <defs>
            <linearGradient id="recordComboGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#8e70fa" stop-opacity="0.28" />
              <stop offset="100%" stop-color="#8e70fa" stop-opacity="0.0" />
            </linearGradient>
          </defs>
          <line x1="${pad}" y1="${hLineArea}" x2="${w - pad}" y2="${hLineArea}" stroke="#1f2c4d" stroke-dasharray="3,3" />
          <polygon points="${lineAreaPath}" fill="url(#recordComboGrad)" />
          <polyline points="${linePath}" fill="none" stroke="#8e70fa" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" />
          <line x1="${pad}" y1="${zeroY}" x2="${w - pad}" y2="${zeroY}" stroke="#334673" stroke-width="1.2" />
          <text x="${pad}" y="${hLineArea + 18}" fill="#7182a6" font-size="10" font-weight="700">일간 손익 (PROFIT / LOSS)</text>
          <text x="${w - pad}" y="${zeroY - 4}" fill="#7182a6" font-size="9" text-anchor="end">0원</text>
          ${bars}
        </svg>
        <div class="record-chart-meta">
          <div><span>기간 시작</span><strong>${html(first.date)}</strong><small>${money(first.total_value_krw)}</small></div>
          <div><span>최근 기록</span><strong>${html(last.date)}</strong><small>${money(last.total_value_krw)}</small></div>
          <div><span>최저 / 최고 자산</span><strong>${money(minVal)} / ${money(maxVal)}</strong><small>해당 기간 ${number(filtered.length, 0)}개 기록</small></div>
        </div>
      `;
    }
  }

  const first = filtered[0];
  const last = filtered.at(-1);
  const delta = Number(last.total_value_krw || 0) - Number(first.total_value_krw || 0);
  const deltaRate = Number(first.total_value_krw || 0) ? delta / Number(first.total_value_krw || 0) * 100 : 0;
  $("#recordSummary") && ($("#recordSummary").textContent = `${money(delta)} (${deltaRate >= 0 ? "+" : ""}${number(deltaRate, 2)}%)`);
  $("#recordSummary") && ($("#recordSummary").className = signClass(delta));
  $("#recordCount") && ($("#recordCount").textContent = `${number(filtered.length, 0)}개 기록`);

  const descRecords = [...filtered].reverse();
  const listEl = $("#assetRecordList");
  if (listEl) {
    listEl.innerHTML = descRecords.map((item) => `
      <div class="record-row">
        <div class="record-row-main">
          <strong>${html(item.date)}</strong>
          <span>${money(item.total_value_krw)} · ${number(item.holding_count, 0)}종목</span>
        </div>
        <div class="record-row-values">
          <b class="${signClass(item.day_profit_krw || 0)}">${Number(item.day_profit_krw || 0) >= 0 ? "+" : ""}${money(item.day_profit_krw || 0)}</b>
          <small>${html(item.memo || item.source || "")}</small>
        </div>
        <div class="record-row-actions">
          <button class="button secondary tiny" data-record-edit="${item.id}" type="button">수정</button>
          <button class="button text danger tiny" data-record-delete="${item.id}" type="button">삭제</button>
        </div>
      </div>
    `).join("");
  }
}

// ── 9. 대시보드 렌더링 총괄 ──────────────────────────────────────────────────
function render(data) {
  dashboard = data;
  renderSummary(data);
  renderClassifications(data.classifications || []);
  renderAccounts(data.accounts);
  renderHeatmaps(data);
  renderHoldings(data);
}

async function loadDashboard() {
  try {
    const allRes = await api('/api/asset-records');
    allAssetRecords = allRes.records || [];
  } catch (e) {}
  const data = await api("/api/dashboard");
  rawDashboard = data;
  dashboard = data;
  renderWithOwner(data, currentOwner);
}

async function loadAssetRecords(owner) {
  try {
    const allRes = await api('/api/asset-records');
    allAssetRecords = allRes.records || [];
  } catch (e) {}
  const o = owner || currentOwner || '모두';
  let filtered = [];
  if (o === '모두') {
    const allOwnerRecs = allAssetRecords.filter(r => (r.owner || '모두') === '모두');
    filtered = allOwnerRecs.length > 0 ? allOwnerRecs : allAssetRecords;
  } else {
    filtered = allAssetRecords.filter(r => (r.owner || '모두') === o);
  }
  assetRecords = filtered;
  renderAssetRecords(filtered);
}

// ── 다이얼로그 열기 함수들 ───────────────────────────────────────────────────
function openImport() { $("#importDialog")?.showModal(); }
function openHoldingDialog(record = null) {
  const form = $("#holdingForm");
  if (!form) return;
  form.reset();
  form.dataset.recordId = record ? String(record.id) : "";
  form.broker.value = record?.broker || "기타 증권사";
  form.account_name.value = record?.account_name || "내 주식 계좌";
  form.code.value = record?.code || "";
  form.name.value = record?.name || "";
  form.quantity.value = record?.quantity ?? "";
  form.avg_price.value = record?.avg_price ?? "";
  form.current_price.value = record?.current_price ?? "";
  form.currency.value = record?.currency || "KRW";
  form.market.value = record?.market || "";
  if (form.sector) form.sector.value = record?.sector || "";
  if (form.owner) {
    const linkedAcct = dashboard?.accounts?.find(a => a.id === record?.account_id);
    form.owner.value = linkedAcct?.owner || record?.owner || "모두";
  }
  $("#holdingDialog")?.showModal();
}

function openAssetRecordDialog(record = null) {
  const form = $("#assetRecordForm");
  if (!form) return;
  form.reset();
  form.dataset.recordId = record?.id || "";
  $("#assetRecordDialogTitle") && ($("#assetRecordDialogTitle").textContent = record ? "자산기록 수정" : "자산기록 추가");
  form.date.value = record?.date || new Date().toISOString().slice(0, 10);
  form.total_value_krw.value = record?.total_value_krw ?? "";
  form.total_cost_krw.value = record?.total_cost_krw ?? "";
  form.profit_krw.value = record?.profit_krw ?? "";
  form.return_rate.value = record?.return_rate ?? "";
  form.day_profit_krw.value = record?.day_profit_krw ?? "";
  form.krw_value_krw.value = record?.krw_value_krw ?? "";
  form.usd_value_krw.value = record?.usd_value_krw ?? "";
  form.holding_count.value = record?.holding_count ?? "";
  form.memo.value = record?.memo ?? "";
  if (form.owner) form.owner.value = record?.owner || currentOwner || "모두";
  $("#assetRecordDialog")?.showModal();
}

function openAccountCashDialog(account) {
  const form = $("#accountCashForm");
  if (!form || !account) return;
  form.reset();
  form.dataset.accountId = account.id;
  $("#accountCashDialogTitle").textContent = `[${account.broker} · ${account.name}] 예수금 입력 / 수정`;
  form.cash_krw.value = account.cash_krw || "";
  form.cash_usd.value = account.cash_usd || "";
  $("#accountCashDialog")?.showModal();
}

function openAccountEditDialog(account) {
  const form = $("#accountEditForm");
  if (!form || !account) return;
  form.reset();
  form.dataset.accountId = account.id;
  form.broker.value = account.broker || "";
  form.name.value = account.name || "";
  if (form.owner) form.owner.value = account.owner || "모두";
  $("#accountEditDialog")?.showModal();
}

// ── 이벤트 리스너 바인딩 ─────────────────────────────────────────────────────

// 1. 상단 계좌 연결 & 갱신 버튼
$("#syncAccountsButton")?.addEventListener("click", (e) => action(e.currentTarget, () => api("/api/sync/all", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));
$("#refreshButton")?.addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));
$("#demoButton")?.addEventListener("click", (e) => action(e.currentTarget, () => api("/api/demo", { method: "POST" })));
$("#addButton")?.addEventListener("click", () => openHoldingDialog());
$("#importButton")?.addEventListener("click", openImport);
$("#addRecordButton")?.addEventListener("click", () => openAssetRecordDialog());

// 2. 오늘 기록 저장
$("#snapshotButton")?.addEventListener("click", (e) => action(e.currentTarget, async () => {
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

  return await api("/api/asset-records", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}, async () => {
  await loadAssetRecords(currentOwner);
}));

// 3. 투자자산 분류 [자산군별] / [섹터별] 탭 전환
document.getElementById('allocTabs')?.addEventListener('click', (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab) return;
  document.querySelectorAll('#allocTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentAllocTab = tab.dataset.tab || 'asset_class';
  renderClassifications(dashboard?.classifications || []);
});

// 4. 자산기록 [콤보 차트] / [월별 자산] 뷰 모드 탭
document.getElementById('recordViewTabs')?.addEventListener('click', (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab) return;
  document.querySelectorAll('#recordViewTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentRecordView = tab.dataset.view || 'combo';
  renderAssetRecords(assetRecords);
});

// 5. 자산기록 기간 탭
document.getElementById('recordPeriodTabs')?.addEventListener('click', (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab) return;
  document.querySelectorAll('#recordPeriodTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentRecordPeriod = tab.dataset.period || 'ALL';
  renderAssetRecords(assetRecords);
});

// 6. 보유종목 테이블 컬럼 정렬 클릭
document.addEventListener('click', (e) => {
  const th = e.target.closest('.sortable-th');
  if (th && th.dataset.sort) {
    const sortField = th.dataset.sort;
    if (holdingSortField === sortField) {
      holdingSortOrder = holdingSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      holdingSortField = sortField;
      holdingSortOrder = 'desc';
    }
    if (dashboard) renderHoldings(dashboard);
    return;
  }

  // 종목 차트 버튼 또는 종목명 클릭
  const chartBtn = e.target.closest('.stock-chart-btn, .holding-name-link');
  if (chartBtn) {
    const code = chartBtn.dataset.code;
    const name = chartBtn.dataset.name;
    const price = chartBtn.dataset.price;
    const currency = chartBtn.dataset.currency;
    if (code) openStockChart(code, name, price, currency);
    return;
  }
});

// 7. 종목 차트 기간 탭 클릭
document.getElementById('stockChartPeriodTabs')?.addEventListener('click', async (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab) return;
  document.querySelectorAll('#stockChartPeriodTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentStockChartPeriod = tab.dataset.period || '3M';
  await loadStockChartData();
});

// 8. 검색창 및 종목 수정/삭제 리스너
$("#searchInput")?.addEventListener("input", () => dashboard && renderHoldings(dashboard));
$("#clearButton")?.addEventListener("click", () => {
  if (confirm("저장된 보유내역을 모두 지울까요?")) {
    action($("#clearButton"), () => api("/api/clear", { method: "POST" }));
  }
});

$("#holdingsBody")?.addEventListener("click", (e) => {
  const edit = e.target.closest(".edit-button");
  const del = e.target.closest(".delete-button");
  if (edit) {
    const item = dashboard?.holdings.find(row => row.id === edit.dataset.id);
    if (item) openHoldingDialog(item);
    return;
  }
  if (del && confirm("이 보유종목을 삭제할까요?")) {
    action(del, () => api(`/api/holdings/${del.dataset.id}`, { method: "DELETE" }));
  }
});

// 9. 계좌 목록 클릭
$("#accountList")?.addEventListener("click", async (e) => {
  const cashBtn = e.target.closest("[data-cash-id]");
  const editBtn = e.target.closest("[data-account-id]");
  const delBtn = e.target.closest("[data-account-del-id]");
  if (cashBtn) {
    const acct = dashboard?.accounts?.find(a => a.id === cashBtn.dataset.cashId);
    if (acct) openAccountCashDialog(acct);
    return;
  }
  if (editBtn) {
    const acct = dashboard?.accounts?.find(a => a.id === editBtn.dataset.accountId);
    if (acct) openAccountEditDialog(acct);
    return;
  }
  if (delBtn && confirm("이 계좌를 삭제할까요? 연결된 보유종목도 함께 삭제됩니다.")) {
    await action(delBtn, () => api(`/api/accounts/${delBtn.dataset.accountDelId}`, { method: "DELETE" }));
  }
});

// 10. 자산기록 리스트 수정/삭제
$("#assetRecordList")?.addEventListener("click", async (e) => {
  const editButton = e.target.closest("[data-record-edit]");
  const deleteButton = e.target.closest("[data-record-delete]");
  if (editButton) {
    const record = assetRecords.find((item) => item.id === editButton.dataset.recordEdit);
    if (record) openAssetRecordDialog(record);
  }
  if (deleteButton && confirm("이 자산기록을 삭제할까요?")) {
    await action(deleteButton, () => api(`/api/asset-records/${deleteButton.dataset.recordDelete}`, { method: "DELETE" }), () => loadAssetRecords(currentOwner));
  }
});

// 11. 폼 서브밋 핸들러들
$("#holdingForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  if (!payload.owner) payload.owner = "모두";
  ["quantity", "avg_price", "current_price"].forEach(key => { payload[key] = Number(payload[key] || 0); });
  try {
    const id = form.dataset.recordId;
    const result = await api(id ? `/api/holdings/${id}` : "/api/holdings", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    form.closest("dialog")?.close();
    toast(result.message);
    await loadDashboard();
  } catch (error) {
    toast(error.message, true);
  }
});

$("#importForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const file = $("#importFile")?.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  try {
    const result = await api(`/api/import?broker=${encodeURIComponent($("#importBroker")?.value || "기타 증권사")}`, {
      method: "POST",
      body: formData
    });
    form.closest("dialog")?.close();
    toast(result.message);
    await loadDashboard();
  } catch (error) {
    toast(error.message, true);
  }
});

$("#assetRecordForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  ["total_value_krw", "total_cost_krw", "profit_krw", "return_rate", "day_profit_krw", "krw_value_krw", "usd_value_krw", "holding_count"].forEach(key => {
    payload[key] = Number(payload[key] || 0);
  });
  payload.memo = payload.memo || "";
  payload.owner = payload.owner || currentOwner || "모두";
  try {
    const method = form.dataset.recordId ? "PUT" : "POST";
    const url = form.dataset.recordId ? `/api/asset-records/${form.dataset.recordId}` : "/api/asset-records";
    const result = await api(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    form.closest("dialog")?.close();
    toast(result.message);
    await loadAssetRecords(currentOwner);
  } catch (error) {
    toast(error.message, true);
  }
});

$("#accountCashForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const accountId = form.dataset.accountId;
  const cashKrw = Number(form.cash_krw.value || 0);
  const cashUsd = Number(form.cash_usd.value || 0);
  try {
    const res = await api(`/api/accounts/${accountId}/cash`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cash_krw: cashKrw, cash_usd: cashUsd })
    });
    form.closest("dialog")?.close();
    toast(res.message);
    await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  }
});

$("#accountEditForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const accountId = form.dataset.accountId;
  const broker = form.broker.value.trim();
  const name = form.name.value.trim();
  const owner = form.owner ? form.owner.value : "모두";
  try {
    const res = await api(`/api/accounts/${accountId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ broker, name, owner })
    });
    form.closest("dialog")?.close();
    toast(res.message);
    await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  }
});

$("#accountAddForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const broker = form.broker.value.trim();
  const name = form.account_name.value.trim();
  const owner = form.owner.value;
  try {
    const res = await api("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ broker, name, owner })
    });
    form.closest("dialog")?.close();
    toast(res.message);
    await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  }
});

// 12. 가족 구성원 관리
async function loadFamilyMembers() {
  try {
    const res = await api('/api/family-members');
    const members = res.members || [];
    renderFamilyTabs(members);
    updateOwnerSelectOptions(members);
  } catch (e) {}
}

function updateOwnerSelectOptions(members) {
  const opts = ['<option value="모두">모두</option>'].concat(members.map(m => `<option value="${m}">${m}</option>`)).join('');
  document.querySelectorAll('select[name="owner"]').forEach(sel => {
    const prev = sel.value;
    sel.innerHTML = opts;
    if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
  });
}

function renderFamilyTabs(members) {
  const allBtn = '<button type="button" class="family-tab' + (currentOwner === '모두' ? ' active' : '') + '" data-owner="모두">모두</button>';
  const memberBtns = members.map(m =>
    '<button type="button" class="family-tab' + (currentOwner === m ? ' active' : '') + '" data-owner="' + m + '">' + m + '</button>'
  ).join('');
  const inner = allBtn + memberBtns;
  const container = document.getElementById('familyTabs');
  if (container) container.innerHTML = inner;
  const topbar = document.getElementById('topbarFamilyTabs');
  if (topbar) topbar.innerHTML = inner;
}

// 13. 데이터 백업 / 복원
document.getElementById('exportButton')?.addEventListener('click', async () => {
  try {
    const response = await fetch('/api/export', { credentials: 'include' });
    if (!response.ok) throw new Error('백업 데이터를 다운로드하지 못했습니다.');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `내자산대시보드_백업_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast('백업 파일을 다운로드했습니다.');
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById('importBackupBtn')?.addEventListener('click', () => {
  document.getElementById('importBackupFile')?.click();
});

document.getElementById('importBackupFile')?.addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  if (!confirm(`'${file.name}' 파일로 데이터를 복원할까요?\n현재 데이터는 덮어쓰입니다.`)) {
    e.target.value = '';
    return;
  }
  const btn = document.getElementById('importBackupBtn');
  btn && (btn.disabled = true);
  try {
    const formData = new FormData();
    formData.append('file', file);
    const result = await api('/api/import-backup', { method: 'POST', body: formData });
    toast(result.message || '데이터를 복원했습니다.');
    await loadDashboard();
    await loadAssetRecords(currentOwner);
  } catch (err) {
    toast(err.message, true);
  } finally {
    e.target.value = '';
    btn && (btn.disabled = false);
  }
});

// PWA 서비스 워커 등록
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}

// ── APP BOOTSTRAP ─────────────────────────────────────────────────────────────
async function bootstrap() {
  try { await loadFamilyMembers(); } catch (e) {}
  try { await loadDashboard(); } catch (e) { toast(e.message || "대시보드를 불러오지 못했습니다.", true); }
  try { await loadMarkets(); } catch (e) {}
  try { await loadAssetRecords('모두'); } catch (e) {}
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}
'''

with open("app/static/wealth.js", "w", encoding="utf-8") as f:
    f.write(JS_CONTENT.strip())

print("Full wealth.js generated successfully!")
