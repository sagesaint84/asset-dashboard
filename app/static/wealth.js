let allAssetRecords = [];
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
let heatmapViewMode = localStorage.getItem("heatmap_view_mode") || "treemap"; // 'treemap' | 'cards'
let heatmapPeriod = localStorage.getItem("heatmap_period") || "1D";
let heatmapTheme = localStorage.getItem("heatmap_theme") || "kr";
let heatmapMaxCap = localStorage.getItem("heatmap_max_cap") || "auto";

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
  loadDividends(currentOwner);
  loadActualDividends(currentOwner, selectedDividendYear);
  loadRealizedPnl(currentOwner, selectedPnlYear, currentPnlTradeType);
}

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

let isSectorDetailExpanded = false;

function renderClassifications(items) {
  const list = $("#classificationList");
  const donutWrap = $("#sectorDonutWrap");
  const toggleWrap = $("#sectorDetailToggleWrap");
  const toggleBtn = $("#toggleSectorDetailBtn");
  if (!list) return;

  if (currentAllocTab === 'sector') {
    if (donutWrap) donutWrap.style.display = 'block';
    if (toggleWrap) toggleWrap.style.display = 'block';
    if (toggleBtn) toggleBtn.innerHTML = isSectorDetailExpanded ? '간단히 ✕' : '자세히 🔍';

    list.style.display = isSectorDetailExpanded ? 'flex' : 'none';

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
    if (toggleWrap) toggleWrap.style.display = 'none';
    list.style.display = 'flex';

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
      return `<div class="account-row"><div class="account-row-info"><strong>${html(account.name)}</strong><span>${number(account.holding_count, 0)}종목${cashText}</span></div><div class="account-row-actions"><button class="account-action-button" data-cash-id="${account.id}" title="예수금 수정" type="button">💵</button><button class="account-action-button" data-account-id="${account.id}" title="계좌 정보 수정" type="button">✎</button><button class="mini-delete-button" data-account-del-id="${account.id}" title="계좌 삭제" type="button">🗑️</button></div></div>`;
    }).join("");
    return `<section class="broker-group"><div class="broker-head"><strong>${html(group.broker)}</strong><span>${number(group.count, 0)}개 계좌</span></div><div class="broker-accounts">${accounts}</div></section>`;
  }).join("");
}

// ── 5. 자산 히트맵 (정통 Squarify 면적 트리맵 + 와이드 카드형 뷰) ─────────────
const PERIOD_LABELS = {
  "1D": "일간",
  "1W": "주간 (5영업일)",
  "1M": "월간 (20영업일)",
  "YTD": "연초부터 (YTD)",
  "1Y": "연간 (240영업일)",
  "TOTAL": "진입가 (매입단가 대비)",
};

const PERIOD_CAPS = {
  "1D": 10,
  "1W": 15,
  "1M": 20,
  "YTD": 50,
  "1Y": 50,
  "TOTAL": 30,
};

function getEffectiveCap(period, capSetting, items = []) {
  if (capSetting && capSetting !== "auto" && !isNaN(Number(capSetting)) && Number(capSetting) > 0) {
    return Number(capSetting);
  }

  if (items && items.length > 0) {
    let maxAbs = 0;
    items.forEach((it) => {
      let r = 0;
      const periodRates = it.period_changes || {};
      if (period === "TOTAL") {
        r = Math.abs(Number(it.rate != null ? it.rate : (it.return_rate || 0)));
      } else if (periodRates[period] != null) {
        r = Math.abs(Number(periodRates[period]));
      } else if (period === "1D") {
        r = Math.abs(Number(it.day_change_rate || 0));
      } else {
        r = Math.abs(Number(it.rate || it.day_change_rate || 0));
      }
      if (!isNaN(r) && r > maxAbs) maxAbs = r;
    });

    if (maxAbs > 0) {
      let cap = Math.ceil(maxAbs);
      if (cap < 3) cap = 3;
      else if (cap <= 25) cap = Math.ceil(maxAbs);
      else if (cap <= 60) cap = Math.ceil(cap / 5) * 5;
      else cap = Math.ceil(cap / 10) * 10;
      return Math.min(200, cap);
    }
  }

  return PERIOD_CAPS[period] || 15;
}

function getHeatmapColor(rate, maxRate = 15, theme = "kr") {
  const clamped = Math.max(-maxRate, Math.min(maxRate, rate));
  const t = Math.pow(Math.abs(clamped) / maxRate, 0.72);

  if (theme === "us") {
    if (clamped >= 0) {
      const r = Math.round(25 + (16 - 25) * t);
      const g = Math.round(45 + (190 - 45) * t);
      const b = Math.round(38 + (120 - 38) * t);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      const r = Math.round(48 + (235 - 48) * t);
      const g = Math.round(30 + (55 - 30) * t);
      const b = Math.round(38 + (55 - 38) * t);
      return `rgb(${r}, ${g}, ${b})`;
    }
  } else if (theme === "neon") {
    if (clamped >= 0) {
      const r = Math.round(40 + (170 - 40) * t);
      const g = Math.round(28 + (80 - 28) * t);
      const b = Math.round(62 + (250 - 62) * t);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      const r = Math.round(20 + (8 - 20) * t);
      const g = Math.round(42 + (190 - 42) * t);
      const b = Math.round(60 + (220 - 60) * t);
      return `rgb(${r}, ${g}, ${b})`;
    }
  } else {
    if (clamped >= 0) {
      const r = Math.round(48 + (238 - 48) * t);
      const g = Math.round(40 + (42 - 40) * t);
      const b = Math.round(52 + (68 - 52) * t);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      const r = Math.round(35 + (35 - 35) * t);
      const g = Math.round(45 + (95 - 45) * t);
      const b = Math.round(58 + (238 - 58) * t);
      return `rgb(${r}, ${g}, ${b})`;
    }
  }
}

function updateHeatmapLegendUI(period, theme, maxCap, items = []) {
  const cap = getEffectiveCap(period, maxCap, items);
  const legLeft = $("#legendCapLeft");
  const legRight = $("#legendCapRight");
  const legBar = $("#legendBar");
  const legText = $("#legendText");
  const tipNote = $("#heatmapTipNote");
  const capSel = document.getElementById("heatmapCapSelect");

  if (capSel) {
    const autoOpt = capSel.querySelector("option[value='auto']");
    if (autoOpt) autoOpt.textContent = `범위: 자동 (±${cap}%)`;
    if (maxCap && capSel.value !== maxCap) capSel.value = maxCap;
  }

  if (legLeft) legLeft.textContent = `-${cap}%`;
  if (legRight) legRight.textContent = `+${cap}%`;
  if (legBar) legBar.className = `legend-bar theme-${theme}`;
  if (legText) {
    if (theme === "us") legText.textContent = "하락(Red) ← 0 → 상승(Green)";
    else if (theme === "neon") legText.textContent = "하락(Cyan) ← 0 → 상승(Violet)";
    else legText.textContent = "하락(Blue) ← 0 → 상승(Red)";
  }
  if (tipNote) tipNote.textContent = `면적 = 포지션 규모 · 색 = ${PERIOD_LABELS[period] || period} 손익률 (범위 ±${cap}%) · 클릭하면 종목 검색`;
}

// ── 정통 Squarify 트리맵 알고리즘 ──
function squarify(items, x, y, width, height) {
  if (!items.length) return [];
  const totalVal = items.reduce((s, it) => s + it.value, 0);
  if (totalVal <= 0) return [];
  const rects = [];
  const sorted = [...items].sort((a, b) => b.value - a.value);

  function layout(children, rect) {
    if (!children.length) return;
    if (children.length === 1) {
      rects.push({ ...children[0], x: rect.x, y: rect.y, w: rect.w, h: rect.h });
      return;
    }
    const isHoriz = rect.w < rect.h;
    const side = isHoriz ? rect.w : rect.h;
    let row = [];
    let rowSum = 0;
    let bestWorst = Infinity;

    for (let i = 0; i < children.length; i++) {
      const nextRow = [...row, children[i]];
      const nextSum = rowSum + children[i].value;
      const curWorst = worst(nextRow, nextSum, side, rect.total, rect.w * rect.h);
      if (row.length === 0 || curWorst <= bestWorst) {
        row = nextRow;
        rowSum = nextSum;
        bestWorst = curWorst;
      } else {
        const remaining = children.slice(i);
        const frac = rowSum / rect.total;
        if (isHoriz) {
          const rowH = rect.h * frac;
          layoutRow(row, { x: rect.x, y: rect.y, w: rect.w, h: rowH }, isHoriz);
          layout(remaining, { x: rect.x, y: rect.y + rowH, w: rect.w, h: rect.h - rowH, total: rect.total - rowSum });
        } else {
          const rowW = rect.w * frac;
          layoutRow(row, { x: rect.x, y: rect.y, w: rowW, h: rect.h }, isHoriz);
          layout(remaining, { x: rect.x + rowW, y: rect.y, w: rect.w - rowW, h: rect.h, total: rect.total - rowSum });
        }
        return;
      }
    }
    layoutRow(row, rect, isHoriz);
  }

  function worst(row, s, side, total, totalArea) {
    if (!row.length || s === 0 || side === 0) return Infinity;
    const rowArea = (s / total) * totalArea;
    const otherSide = rowArea / side;
    if (otherSide === 0) return Infinity;
    let maxRatio = 0;
    for (const item of row) {
      const itemArea = (item.value / total) * totalArea;
      const itemLen = itemArea / otherSide;
      if (itemLen === 0) return Infinity;
      const ratio = Math.max(itemLen / otherSide, otherSide / itemLen);
      if (ratio > maxRatio) maxRatio = ratio;
    }
    return maxRatio;
  }

  function layoutRow(row, rect, isHoriz) {
    if (!row.length) return;
    let offset = isHoriz ? rect.x : rect.y;
    const totalRowVal = row.reduce((s, it) => s + it.value, 0);
    for (const item of row) {
      const frac = totalRowVal > 0 ? item.value / totalRowVal : 1 / row.length;
      if (isHoriz) {
        const w = rect.w * frac;
        rects.push({ ...item, x: offset, y: rect.y, w, h: rect.h });
        offset += w;
      } else {
        const h = rect.h * frac;
        rects.push({ ...item, x: rect.x, y: offset, w: rect.w, h });
        offset += h;
      }
    }
  }

  layout(sorted, { x, y, w: width, h: height, total: totalVal });
  return rects;
}

function renderTreemapContainer(container, items, period = "1D", theme = "kr", capSetting = "auto") {
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="empty">평가금액이 있는 보유종목이 없습니다.</div>';
    return;
  }

  const maxCap = getEffectiveCap(period, capSetting, items);
  const totalVal = items.reduce((s, it) => s + it.value, 0);
  items.forEach((it) => {
    it.weight = totalVal > 0 ? (it.value / totalVal) * 100 : 0;
  });

  const width = container.clientWidth || 920;
  const height = Math.max(380, Math.min(540, Math.round(width * 0.46)));
  container.style.position = "relative";
  container.style.height = `${height}px`;

  const tiles = squarify(items, 0, 0, width, height);

  container.innerHTML = tiles.map((tile) => {
    const periodRates = tile.period_changes || {};
    let rateVal = 0;
    if (period === "TOTAL") {
      rateVal = Number(tile.rate || 0);
    } else if (periodRates[period] != null) {
      rateVal = Number(periodRates[period]);
    } else if (period === "1D") {
      rateVal = Number(tile.day_change_rate || 0);
    } else {
      rateVal = Number(tile.rate || 0);
    }

    const color = getHeatmapColor(rateVal, maxCap, theme);
    const sign = rateVal >= 0 ? "+" : "";
    const rateText = `${sign}${number(rateVal, 1)}%`;

    const isTiny = tile.w < 38 || tile.h < 26;
    const isSmall = !isTiny && (tile.w < 62 || tile.h < 42);
    const isMed = !isTiny && !isSmall && (tile.w < 98 || tile.h < 64);

    let inner = "";
    if (isTiny) {
      inner = `<span class="tile-tiny-dot"></span>`;
    } else if (isSmall) {
      inner = `<span class="tile-name small">${html(tile.name)}</span><span class="tile-rate small">${rateText}</span>`;
    } else if (isMed) {
      inner = `<strong class="tile-name med">${html(tile.name)}</strong><span class="tile-rate med">${rateText}</span>`;
    } else {
      inner = `<strong class="tile-name">${html(tile.name)}</strong><span class="tile-rate">${rateText}</span>`;
    }

    const infoStr = encodeURIComponent(JSON.stringify({
      period,
      name: tile.name,
      code: tile.code,
      market: tile.market || tile.currency,
      value: tile.market_value_krw,
      cost: tile.cost_value_krw,
      profit: tile.profit_krw,
      rate: tile.rate,
      selected_rate: rateVal,
      day_change_rate: tile.day_change_rate || 0,
      period_changes: tile.period_changes,
      weight: tile.weight,
    }));

    return `<div class="heatmap-tile" data-symbol="${html(tile.name)}" data-info="${infoStr}" style="left:${tile.x.toFixed(1)}px;top:${tile.y.toFixed(1)}px;width:${tile.w.toFixed(1)}px;height:${tile.h.toFixed(1)}px;background-color:${color};"><div class="heatmap-tile-inner">${inner}</div></div>`;
  }).join("");

  updateHeatmapLegendUI(period, theme, capSetting, items);
  bindHeatmapInteractions(container);
}

function renderHeatmaps(data) {
  const holdings = data?.holdings || [];
  const container = $("#assetHeatmapContainer");
  if (!container) return;

  if (!holdings.length) {
    container.innerHTML = '<div class="empty">보유종목이 없습니다. 증권사 동기화 후 히트맵이 표시됩니다.</div>';
    return;
  }

  const groups = new Map();
  holdings.forEach((item) => {
    const key = `${item.code}|${item.currency}|${item.name}`;
    const group = groups.get(key) || {
      code: item.code,
      name: item.name,
      currency: item.currency,
      market: item.market,
      quantity: 0,
      market_value_krw: 0,
      cost_value_krw: 0,
      profit_krw: 0,
      day_change_rate: Number(item.day_change_rate || 0),
      period_changes: item.period_changes || {
        "1D": Number(item.day_change_rate || 0),
        "1W": Number(item.day_change_rate || 0),
        "1M": Number(item.day_change_rate || 0),
        "YTD": Number(item.day_change_rate || 0),
        "1Y": Number(item.day_change_rate || 0),
        "TOTAL": Number(item.return_rate || 0),
      },
    };
    group.quantity += Number(item.quantity || 0);
    group.market_value_krw += Number(item.market_value_krw || 0);
    group.cost_value_krw += Number(item.cost_value_krw || 0);
    group.profit_krw += Number(item.profit_krw || 0);
    if (item.day_change_rate != null && Number(item.day_change_rate) !== 0) {
      group.day_change_rate = Number(item.day_change_rate);
    }
    if (item.period_changes) {
      group.period_changes = item.period_changes;
    }
    groups.set(key, group);
  });

  const totalVal = [...groups.values()].reduce((s, it) => s + it.market_value_krw, 0);
  const items = [...groups.values()]
    .filter((it) => it.market_value_krw > 0)
    .map((it) => {
      const rate = it.cost_value_krw ? (it.profit_krw / it.cost_value_krw) * 100 : 0;
      return {
        ...it,
        value: it.market_value_krw,
        rate: rate,
        weight: totalVal > 0 ? (it.market_value_krw / totalVal) * 100 : 0,
      };
    })
    .sort((a, b) => b.value - a.value);

  if (heatmapViewMode === 'cards') {
    container.style.height = "auto";
    container.style.position = "static";
    const maxCap = getEffectiveCap(heatmapPeriod, heatmapMaxCap, items);
    updateHeatmapLegendUI(heatmapPeriod, heatmapTheme, heatmapMaxCap, items);

    container.innerHTML = `
      <div class="heatmap-cards-grid">
        ${items.map(it => {
          const periodRates = it.period_changes || {};
          let selRate = 0;
          if (heatmapPeriod === 'TOTAL') selRate = it.rate;
          else if (periodRates[heatmapPeriod] != null) selRate = Number(periodRates[heatmapPeriod]);
          else selRate = Number(it.day_change_rate || 0);

          const bgColor = getHeatmapColor(selRate, maxCap, heatmapTheme);
          const isUp = selRate >= 0;
          const sign = isUp ? '+' : '';

          return `
            <div class="heatmap-card-item" style="background-color:${bgColor};border:1px solid rgba(255,255,255,0.16);cursor:pointer;padding:12px 14px;border-radius:10px;transition:all 0.16s ease;box-shadow:0 2px 6px rgba(0,0,0,0.25);"
              onclick="$('#searchInput').value='${it.name}';renderHoldings(dashboard);">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
                <strong style="font-size:13.5px;font-weight:700;color:#ffffff;text-shadow:0 1px 3px rgba(0,0,0,0.55);">${html(it.name)}</strong>
                <span style="font-size:11.5px;color:rgba(255,255,255,0.8);font-weight:600;">${number(it.weight, 1)}%</span>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:8px;">
                <small style="font-size:11.5px;color:rgba(255,255,255,0.85);">${money(it.value)}</small>
                <b style="font-size:14px;font-weight:800;color:#ffffff;text-shadow:0 1px 4px rgba(0,0,0,0.7);">${sign}${number(selRate, 2)}%</b>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  } else {
    renderTreemapContainer(container, items, heatmapPeriod, heatmapTheme, heatmapMaxCap);
  }
}

// ── 히트맵 툴팁 바인딩 ──
function bindHeatmapInteractions(container) {
  const tooltipEl = document.getElementById("heatmapTooltip");
  if (!container || !tooltipEl) return;
  
  // 중복 이벤트 리스너 방지 플래그
  if (container._heatmapBound) return;
  container._heatmapBound = true;

  container.addEventListener("mousemove", (e) => {
    const tile = e.target.closest(".heatmap-tile");
    if (!tile || !tile.dataset.info) {
      tooltipEl.style.display = "none";
      return;
    }
    try {
      const rawInfo = tile.dataset.info.startsWith("%") ? decodeURIComponent(tile.dataset.info) : tile.dataset.info;
      const info = JSON.parse(rawInfo);
      const period = info.period || heatmapPeriod || "1D";
      const selRate = Number(info.selected_rate != null ? info.selected_rate : (period === "TOTAL" ? info.rate : (info.period_changes?.[period] || info.day_change_rate || 0)));
      const sign = selRate >= 0 ? "+" : "";
      const rateColor = selRate >= 0 ? "#f43f5e" : "#38bdf8";
      const totalRateColor = (info.rate || 0) >= 0 ? "#f43f5e" : "#38bdf8";
      const periodLabel = PERIOD_LABELS[period] || period;

      tooltipEl.innerHTML = `
        <div class="heatmap-tooltip-title">
          <strong>${html(info.name)}</strong>
          <span>${html(info.code)} · ${html(info.market || 'KRX')}</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">포지션 규모:</span>
          <span class="val">${money(info.value)} (${number(info.weight, 1)}%)</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">${periodLabel}:</span>
          <span class="val" style="color:${rateColor};font-weight:700;">${sign}${number(selRate, 2)}%</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">누적 수익률:</span>
          <span class="val" style="color:${totalRateColor};font-weight:700;">${(info.rate || 0) >= 0 ? "+" : ""}${number(info.rate, 2)}% (${(info.profit || 0) >= 0 ? "+" : ""}${money(info.profit)})</span>
        </div>
      `;
      tooltipEl.style.display = "block";
      const x = Math.min(Math.max(140, e.clientX), window.innerWidth - 140);
      const y = Math.max(70, e.clientY);
      tooltipEl.style.left = `${x}px`;
      tooltipEl.style.top = `${y}px`;
    } catch (err) {
      console.warn("Tooltip info parse error:", err);
      tooltipEl.style.display = "none";
    }
  });

  container.addEventListener("mouseleave", () => {
    if (tooltipEl) tooltipEl.style.display = "none";
  });

  container.addEventListener("click", (e) => {
    const tile = e.target.closest(".heatmap-tile");
    if (!tile || !tile.dataset.symbol) return;
    const search = $("#searchInput");
    if (search) {
      search.value = tile.dataset.symbol;
      if (dashboard) renderHoldings(dashboard);
    }
  });
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

    const pricePoints = candles.map((c, idx) => {
      const x = pad + ((w - pad * 2) * idx) / Math.max(candles.length - 1, 1);
      const y = pad + (hPriceArea - pad) * (1 - (c.close - minPrice) / spanPrice);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const pricePath = pricePoints.join(" ");
    const priceAreaPath = `${pricePath} ${(w - pad)},${hPriceArea} ${pad},${hPriceArea}`;

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
        <polygon points="${priceAreaPath}" fill="url(#stockPriceGrad)" />
        <polyline points="${pricePath}" fill="none" stroke="#8e70fa" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
        <text x="${pad}" y="${pad + 4}" fill="#7182a6" font-size="10">최고 ${money(maxPrice, currentStockChartCurrency)}</text>
        <text x="${pad}" y="${hPriceArea - 4}" fill="#7182a6" font-size="10">최저 ${money(minPrice, currentStockChartCurrency)}</text>
        
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

  if (currentRecordView === 'bar' || currentRecordView === 'monthly') {
    const values = filtered.map(item => Number(item.total_value_krw || 0));
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const spanVal = maxVal - (minVal * 0.8) || 1;

    const w = 900, h = 260, pad = 30;
    const hBarArea = 180;
    const barWidth = Math.max(12, Math.min(48, (w - pad * 2) / filtered.length - 8));

    let prevVal = 0;
    const bars = filtered.map((item, idx) => {
      const val = Number(item.total_value_krw || 0);
      const delta = prevVal ? val - prevVal : Number(item.day_profit_krw || 0);
      const deltaRate = prevVal ? (delta / prevVal) * 100 : 0;
      prevVal = val;
      const isGain = delta >= 0;

      const x = pad + ((w - pad * 2) * (idx + 0.5)) / Math.max(filtered.length, 1) - barWidth / 2;
      const barH = Math.max(10, ((val - minVal * 0.8) / spanVal) * (hBarArea - 25));
      const y = hBarArea - barH;

      const sign = delta >= 0 ? "+" : "";
      const deltaText = delta !== 0 ? `${sign}${number(deltaRate, 1)}%` : "-";
      const deltaColor = delta !== 0 ? (isGain ? "#ff5c77" : "#4f9dff") : "#8e9bb5";
      const shortDate = item.date ? item.date.slice(5) : ""; // MM-DD

      return `
        <g class="monthly-bar-group">
          <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barH.toFixed(1)}" fill="url(#assetBarGrad)" rx="3.5" opacity="0.9">
            <title>${item.date}: ${money(val)} (변동 ${sign}${money(delta)} / ${deltaRate.toFixed(2)}%)</title>
          </rect>
          <text x="${(x + barWidth / 2).toFixed(1)}" y="${(y - 6).toFixed(1)}" fill="#f3f5ff" font-size="10" font-weight="700" text-anchor="middle">
            ${money(val)}
          </text>
          <text x="${(x + barWidth / 2).toFixed(1)}" y="${(hBarArea + 16).toFixed(1)}" fill="#c4d1eb" font-size="10.5" font-weight="700" text-anchor="middle">
            ${shortDate}
          </text>
          <text x="${(x + barWidth / 2).toFixed(1)}" y="${(hBarArea + 28).toFixed(1)}" fill="${deltaColor}" font-size="9" font-weight="700" text-anchor="middle">
            ${deltaText}
          </text>
        </g>
      `;
    }).join('');

    const first = filtered[0];
    const last = filtered.at(-1);
    const totalDelta = Number(last.total_value_krw || 0) - Number(first.total_value_krw || 0);
    const totalDeltaRate = Number(first.total_value_krw || 0) ? (totalDelta / Number(first.total_value_krw || 0)) * 100 : 0;

    if (wrap) {
      wrap.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:2px 4px 8px;font-size:12px;font-weight:700;">
          <span style="color:#c4b5fd;">📊 총 투자자산 일자별 막대그래프 (${filtered.length}개 기록)</span>
          <span class="${signClass(totalDelta)}" style="font-size:12px;">기간 변동: ${totalDelta >= 0 ? '+' : ''}${money(totalDelta)} (${totalDelta >= 0 ? '+' : ''}${number(totalDeltaRate, 2)}%)</span>
        </div>
        <svg class="record-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:260px;overflow:visible;">
          <defs>
            <linearGradient id="assetBarGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#a78bfa" />
              <stop offset="100%" stop-color="#6366f1" />
            </linearGradient>
          </defs>
          <line x1="${pad}" y1="${hBarArea}" x2="${w - pad}" y2="${hBarArea}" stroke="#283758" stroke-width="1.2" />
          ${bars}
        </svg>
        <div class="record-chart-meta">
          <div><span>기간 시작</span><strong>${html(first.date)}</strong><small>${money(first.total_value_krw)}</small></div>
          <div><span>최근 기록</span><strong>${html(last.date)}</strong><small>${money(last.total_value_krw)}</small></div>
          <div><span>최저 / 최고 자산</span><strong>${money(minVal)} / ${money(maxVal)}</strong><small>해당 기간 ${number(filtered.length, 0)}개 기록</small></div>
        </div>
      `;
    }
  } else {
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

// ── 14. 가족 구성원 관리 함수들 ──────────────────────────────────────────────
function renderFamilyMemberList(members) {
  const list = document.getElementById('familyMemberList');
  if (!list) return;
  if (!members.length) {
    list.innerHTML = '<p style="color:var(--muted);font-size:13px;">구성원이 없습니다.</p>';
    return;
  }
  list.innerHTML = members.map(m => `
    <div class="family-member-row" style="display:flex;align-items:center;gap:8px;">
      <input class="family-member-name-input" type="text" value="${m}" data-original="${m}"
        style="flex:1;font-size:13px;" maxlength="20" />
      <button class="button secondary compact family-rename-btn" data-name="${m}" type="button">수정</button>
      <button class="button text danger compact family-delete-btn" data-name="${m}" type="button">삭제</button>
    </div>
  `).join('');
}

async function openFamilyManager() {
  const dlg = document.getElementById('familyManagerDialog');
  if (!dlg) return;
  try {
    const res = await api('/api/family-members');
    renderFamilyMemberList(res.members || []);
  } catch(e) {
    renderFamilyMemberList([]);
  }
  dlg.showModal();
}

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

// ── 전역 클릭 이벤트 위임 ───────────────────────────────────────────────────
document.addEventListener('click', async (e) => {
  // 🔽 섹션 접기 / 펼치기 버튼
  const collapseBtn = e.target.closest('.section-collapse-btn');
  if (collapseBtn) {
    e.preventDefault();
    e.stopPropagation();
    if (typeof toggleSection === 'function') {
      toggleSection(collapseBtn.dataset.section);
    }
    return;
  }

  // 🎨 테마 변경 탭 버튼
  const themeTab = e.target.closest('#themeSwitcherTabs .theme-tab');
  if (themeTab) {
    e.preventDefault();
    if (typeof setAppTheme === 'function') {
      setAppTheme(themeTab.dataset.theme);
    }
    return;
  }

  // 가족 탭 선택
  const accountsTab = e.target.closest('#familyTabs .family-tab');
  if (accountsTab) { selectOwner(accountsTab.dataset.owner); return; }
  const topbarTab = e.target.closest('#topbarFamilyTabs .family-tab');
  if (topbarTab) { selectOwner(topbarTab.dataset.owner); return; }

  // ⚙️ 가족 관리 모달 열기
  if (e.target.closest('#manageFamilyBtn')) {
    await openFamilyManager();
    return;
  }

  // ➕ 계좌 추가 모달 열기
  if (e.target.closest('#addAccountBtn')) {
    const form = document.getElementById("accountAddForm");
    if (form) {
      form.reset();
      const ownerSelect = form.querySelector("[name='owner']");
      if (ownerSelect && currentOwner !== "모두") {
        ownerSelect.value = currentOwner;
      }
    }
    document.getElementById("accountAddDialog")?.showModal();
    return;
  }

  // 💾 계좌 추가 저장 버튼
  if (e.target.closest('#accountAddSaveBtn')) {
    e.preventDefault();
    if (typeof saveNewAccount === 'function') {
      saveNewAccount();
    }
    return;
  }

  // 가족 구성원 추가
  if (e.target.closest('#addMemberBtn')) {
    const input = document.getElementById('newMemberName');
    const name = (input?.value || '').trim();
    if (!name) { toast('이름을 입력해 주세요.', true); return; }
    try {
      const res = await api('/api/family-members', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      toast(res.message || '추가했습니다.');
      if (input) input.value = '';
      renderFamilyTabs(res.members || []);
      updateOwnerSelectOptions(res.members || []);
      renderFamilyMemberList(res.members || []);
    } catch(err) { toast(err.message, true); }
    return;
  }

  // 가족 구성원 이름 수정
  const renameBtn = e.target.closest('.family-rename-btn');
  if (renameBtn) {
    const row = renameBtn.closest('.family-member-row');
    const input = row?.querySelector('.family-member-name-input');
    const oldName = renameBtn.dataset.name;
    const newName = (input?.value || '').trim();
    if (!newName || newName === oldName) return;
    try {
      const res = await api(`/api/family-members/${encodeURIComponent(oldName)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName }),
      });
      toast(res.message || '수정했습니다.');
      renderFamilyTabs(res.members || []);
      updateOwnerSelectOptions(res.members || []);
      renderFamilyMemberList(res.members || []);
      await loadDashboard();
    } catch(err) { toast(err.message, true); }
    return;
  }

  // 가족 구성원 삭제
  const deleteMemberBtn = e.target.closest('.family-delete-btn');
  if (deleteMemberBtn) {
    const name = deleteMemberBtn.dataset.name;
    if (!confirm(`'${name}' 구성원을 삭제할까요?\n연결된 계좌는 '모두'로 변경됩니다.`)) return;
    try {
      const res = await api(`/api/family-members/${encodeURIComponent(name)}`, { method: 'DELETE' });
      toast(res.message || '삭제했습니다.');
      renderFamilyTabs(res.members || []);
      updateOwnerSelectOptions(res.members || []);
      renderFamilyMemberList(res.members || []);
      await loadDashboard();
    } catch(err) { toast(err.message, true); }
    return;
  }

  // 보유종목 정렬 헤더 클릭
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

  // 종목 차트 모달 기간 탭 클릭
  const chartTab = e.target.closest('#stockChartPeriodTabs .heatmap-tab');
  if (chartTab) {
    document.querySelectorAll('#stockChartPeriodTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
    chartTab.classList.add('active');
    currentStockChartPeriod = chartTab.dataset.period || '3M';
    await loadStockChartData();
    return;
  }

  // 자산기록 뷰 전환 탭 (📈 콤보 차트 vs 📊 막대 차트)
  const recordViewTab = e.target.closest('#recordViewTabs .heatmap-tab');
  if (recordViewTab) {
    document.querySelectorAll('#recordViewTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
    recordViewTab.classList.add('active');
    currentRecordView = recordViewTab.dataset.view || 'combo';
    renderAssetRecords(assetRecords);
    return;
  }

  // 자산기록 기간 탭 (1M, 3M, 6M, 1Y, ALL)
  const recordPeriodTab = e.target.closest('#recordPeriodTabs .heatmap-tab');
  if (recordPeriodTab) {
    document.querySelectorAll('#recordPeriodTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
    recordPeriodTab.classList.add('active');
    currentRecordPeriod = recordPeriodTab.dataset.period || 'ALL';
    renderAssetRecords(assetRecords);
    return;
  }

  // 투자자산 분류 탭 (자산군별 vs 섹터별)
  const allocTab = e.target.closest('#allocTabs .heatmap-tab');
  if (allocTab) {
    document.querySelectorAll('#allocTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
    allocTab.classList.add('active');
    currentAllocTab = allocTab.dataset.tab || 'asset_class';
    renderClassifications(dashboard?.classifications || []);
    return;
  }

  // 히트맵 뷰 전환 탭 (면적형 vs 카드형)
  const hmViewTab = e.target.closest('#heatmapViewTabs .heatmap-tab');
  if (hmViewTab) {
    document.querySelectorAll('#heatmapViewTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
    hmViewTab.classList.add('active');
    heatmapViewMode = hmViewTab.dataset.view || 'treemap';
    localStorage.setItem("heatmap_view_mode", heatmapViewMode);
    if (dashboard) renderHeatmaps(dashboard);
    return;
  }

  // 히트맵 기간 탭 (1D, 1W, 1M, YTD, 1Y, TOTAL)
  const hmPeriodTab = e.target.closest('#heatmapPeriodTabs .heatmap-tab');
  if (hmPeriodTab) {
    document.querySelectorAll('#heatmapPeriodTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
    hmPeriodTab.classList.add('active');
    heatmapPeriod = hmPeriodTab.dataset.period || '1D';
    localStorage.setItem("heatmap_period", heatmapPeriod);
    if (dashboard) renderHeatmaps(dashboard);
    return;
  }

  // 섹터별 상세 토글 버튼 (자세히 🔍 / 간단히 ✕)
  const sectorToggleBtn = e.target.closest('#toggleSectorDetailBtn');
  if (sectorToggleBtn) {
    isSectorDetailExpanded = !isSectorDetailExpanded;
    renderClassifications(dashboard?.sector_classifications || []);
    return;
  }

  // 배당 재조회 버튼
  const divRefreshBtn = e.target.closest('#refreshDividendBtn');
  if (divRefreshBtn) {
    action(divRefreshBtn, () => api("/api/refresh-prices", { method: "POST" }), async () => {
      await loadDashboard();
      await loadMarkets();
      await loadDividends(currentOwner);
    });
    return;
  }

  // 배당 모드 탭 (🔮 예상 vs 💵 실제)
  const divModeTab = e.target.closest('#dividendModeTabs .heatmap-tab');
  if (divModeTab) {
    document.querySelectorAll('#dividendModeTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
    divModeTab.classList.add('active');
    currentDividendMode = divModeTab.dataset.divMode || 'estimated';
    selectedDividendMonth = null;
    const refreshBtn = $("#refreshDividendBtn");
    const addBtn = $("#addDividendBtn");
    const importBtn = $("#importDividendBtn");

    if (currentDividendMode === 'estimated') {
      if (refreshBtn) refreshBtn.style.display = 'inline-block';
      if (addBtn) addBtn.style.display = 'none';
      if (importBtn) importBtn.style.display = 'none';
      if (dividendData) renderDividends(dividendData);
      else loadDividends(currentOwner);
    } else {
      if (refreshBtn) refreshBtn.style.display = 'none';
      if (addBtn) addBtn.style.display = 'inline-block';
      if (importBtn) importBtn.style.display = 'inline-block';
      if (actualDividendData) renderActualDividends(actualDividendData);
      else loadActualDividends(currentOwner);
    }
    return;
  }

  // 💾 실제 배당 저장하기 버튼
  if (e.target.closest('#dividendSaveBtn')) {
    e.preventDefault();
    if (typeof saveActualDividendRecord === 'function') {
      saveActualDividendRecord();
    }
    return;
  }

  // 💾 매도 실현손익 저장하기 버튼
  if (e.target.closest('#pnlSaveBtn')) {
    e.preventDefault();
    if (typeof saveRealizedPnlRecord === 'function') {
      saveRealizedPnlRecord();
    }
    return;
  }

  // ➕ 실제 배당 추가 버튼
  if (e.target.closest('#addDividendBtn')) {
    openDividendRecordDialog();
    return;
  }

  // 📂 실제 배당 가져오기 버튼
  if (e.target.closest('#importDividendBtn')) {
    const dlg = document.getElementById("dividendImportDialog");
    if (dlg) dlg.showModal();
    return;
  }

  // 실제 배당 수정 버튼
  const editActualDivBtn = e.target.closest('.edit-actual-div-btn');
  if (editActualDivBtn) {
    const rId = editActualDivBtn.dataset.id;
    const rec = (actualDividendData?.records || []).find(r => r.id === rId);
    if (rec) openDividendRecordDialog(rec);
    return;
  }

  // 실제 배당 삭제 버튼
  const delActualDivBtn = e.target.closest('.delete-actual-div-btn');
  if (delActualDivBtn) {
    const rId = delActualDivBtn.dataset.id;
    const rec = (actualDividendData?.records || []).find(r => r.id === rId);
    const label = rec ? `${rec.date} ${rec.name} (${money(rec.amount_krw)})` : '배당 기록';
    if (!confirm(`'${label}' 배당 내역을 삭제할까요?`)) return;
    try {
      const res = await api(`/api/actual-dividends/${rId}`, { method: 'DELETE' });
      toast(res.message || '삭제되었습니다.');
      await loadActualDividends(currentOwner);
    } catch (err) {
      toast(err.message, true);
    }
    return;
  }

  // 배당 막대 차트 월 선택
  const divBar = e.target.closest('.dividend-bar-group');
  if (divBar && divBar.dataset.month) {
    const m = Number(divBar.dataset.month);
    selectedDividendMonth = selectedDividendMonth === m ? null : m;
    if (currentDividendMode === 'estimated') {
      if (dividendData) renderDividends(dividendData);
    } else {
      if (actualDividendData) renderActualDividends(actualDividendData);
    }
    return;
  }

  // 배당 전체 보기 버튼
  if (e.target.closest('#clearDivMonthBtn')) {
    selectedDividendMonth = null;
    if (currentDividendMode === 'estimated') {
      if (dividendData) renderDividends(dividendData);
    } else {
      if (actualDividendData) renderActualDividends(actualDividendData);
    }
    return;
  }

  // 실현손익 거래유형 탭 (🏢 전체 vs 📦 공모주)
  const pnlTab = e.target.closest('#pnlTradeTypeTabs .heatmap-tab');
  if (pnlTab) {
    document.querySelectorAll('#pnlTradeTypeTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
    pnlTab.classList.add('active');
    currentPnlTradeType = pnlTab.dataset.tradeType || 'all';
    selectedPnlMonth = null;
    loadRealizedPnl(currentOwner, selectedPnlYear, currentPnlTradeType);
    return;
  }

  // ➕ 실현손익 추가 버튼
  if (e.target.closest('#addPnlBtn')) {
    openPnlRecordDialog();
    return;
  }

  // 📂 실현손익 가져오기 버튼
  if (e.target.closest('#importPnlBtn')) {
    const dlg = document.getElementById("pnlImportDialog");
    if (dlg) dlg.showModal();
    return;
  }

  // 실현손익 수정 버튼
  const editPnlBtn = e.target.closest('.edit-pnl-btn');
  if (editPnlBtn) {
    const rId = editPnlBtn.dataset.id;
    const rec = (pnlData?.records || []).find(r => r.id === rId);
    if (rec) openPnlRecordDialog(rec);
    return;
  }

  // 실현손익 삭제 버튼
  const delPnlBtn = e.target.closest('.delete-pnl-btn');
  if (delPnlBtn) {
    const rId = delPnlBtn.dataset.id;
    const rec = (pnlData?.records || []).find(r => r.id === rId);
    const label = rec ? `${rec.date} ${rec.name} (${money(rec.pnl_krw)})` : '손익 기록';
    if (!confirm(`'${label}' 매도 실현손익 내역을 삭제할까요?`)) return;
    try {
      const res = await api(`/api/realized-pnl/${rId}`, { method: 'DELETE' });
      toast(res.message || '삭제되었습니다.');
      await loadRealizedPnl(currentOwner, selectedPnlYear, currentPnlTradeType);
    } catch (err) {
      toast(err.message, true);
    }
    return;
  }

  // 실현손익 막대 차트 월 선택
  const pnlBar = e.target.closest('.pnl-bar-group');
  if (pnlBar && pnlBar.dataset.month) {
    const m = Number(pnlBar.dataset.month);
    selectedPnlMonth = selectedPnlMonth === m ? null : m;
    if (pnlData) renderRealizedPnl(pnlData);
    return;
  }

  // 실현손익 전체 보기 버튼
  if (e.target.closest('#clearPnlMonthBtn')) {
    selectedPnlMonth = null;
    if (pnlData) renderRealizedPnl(pnlData);
    return;
  }
});

// ── 이벤트 리스너 바인딩 ─────────────────────────────────────────────────────

// 1. 상단 계좌 연결 & 갱신 버튼
$("#syncAccountsButton")?.addEventListener("click", (e) => action(e.currentTarget, () => api("/api/sync/all", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));
$("#refreshButton")?.addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));
$("#refreshMarketButton")?.addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));
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

// 6. 히트맵 [면적형] / [카드형] 뷰 전환 탭
document.getElementById('heatmapViewTabs')?.addEventListener('click', (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab) return;
  document.querySelectorAll('#heatmapViewTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  heatmapViewMode = tab.dataset.view || 'treemap';
  localStorage.setItem("heatmap_view_mode", heatmapViewMode);
  if (dashboard) renderHeatmaps(dashboard);
});

// 7. 히트맵 기간 탭 & 셀렉트 박스
document.getElementById('heatmapPeriodTabs')?.addEventListener('click', (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab) return;
  document.querySelectorAll('#heatmapPeriodTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  heatmapPeriod = tab.dataset.period || '1D';
  localStorage.setItem("heatmap_period", heatmapPeriod);
  if (dashboard) renderHeatmaps(dashboard);
});

document.getElementById('heatmapCapSelect')?.addEventListener('change', (e) => {
  heatmapMaxCap = e.target.value;
  localStorage.setItem("heatmap_max_cap", heatmapMaxCap);
  if (dashboard) renderHeatmaps(dashboard);
});

document.getElementById('heatmapThemeSelect')?.addEventListener('change', (e) => {
  heatmapTheme = e.target.value;
  localStorage.setItem("heatmap_theme", heatmapTheme);
  if (dashboard) renderHeatmaps(dashboard);
});

// 히트맵 인터랙션 바인딩
bindHeatmapInteractions($("#assetHeatmapContainer"));

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

let isSubmittingAccount = false;
async function saveNewAccount() {
  if (isSubmittingAccount) return;
  const form = document.getElementById("accountAddForm");
  if (!form) return;
  const broker = (form.querySelector("[name='broker']")?.value || "").trim();
  const account_name = (form.querySelector("[name='account_name']")?.value || "").trim();
  const owner = (form.querySelector("[name='owner']")?.value || "모두").trim();

  if (!broker || !account_name) {
    toast("증권사와 계좌 이름을 모두 입력해 주세요.", true);
    return;
  }

  isSubmittingAccount = true;
  try {
    const res = await api("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ broker, account_name, name: account_name, owner })
    });
    document.getElementById("accountAddDialog")?.close();
    toast(res.message || "계좌가 추가되었습니다.");
    await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  } finally {
    isSubmittingAccount = false;
  }
}

$("#accountAddForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  saveNewAccount();
});

// ── 종목 사전 및 양방향 자동완성 (종목코드 ↔ 종목명) ─────────────────────────
const POPULAR_STOCKS = [
  { code: "005930", name: "삼성전자", currency: "KRW" },
  { code: "005935", name: "삼성전자우", currency: "KRW" },
  { code: "000660", name: "SK하이닉스", currency: "KRW" },
  { code: "373220", name: "LG에너지솔루션", currency: "KRW" },
  { code: "207940", name: "삼성바이오로직스", currency: "KRW" },
  { code: "005380", name: "현대차", currency: "KRW" },
  { code: "000270", name: "기아", currency: "KRW" },
  { code: "068270", name: "셀트리온", currency: "KRW" },
  { code: "035420", name: "NAVER", currency: "KRW" },
  { code: "035720", name: "카카오", currency: "KRW" },
  { code: "005490", name: "POSCO홀딩스", currency: "KRW" },
  { code: "105560", name: "KB금융", currency: "KRW" },
  { code: "055550", name: "신한지주", currency: "KRW" },
  { code: "086790", name: "하나금융지주", currency: "KRW" },
  { code: "316140", name: "우리금융지주", currency: "KRW" },
  { code: "069500", name: "KODEX 200", currency: "KRW" },
  { code: "360750", name: "TIGER 미국S&P500", currency: "KRW" },
  { code: "133690", name: "TIGER 미국나스닥100", currency: "KRW" },
  { code: "379800", name: "KODEX 미국S&P500TR", currency: "KRW" },
  { code: "379810", name: "KODEX 미국나스닥100TR", currency: "KRW" },
  { code: "360200", name: "ACE 미국S&P500", currency: "KRW" },
  { code: "449450", name: "PLUS 고배당주", currency: "KRW" },
  { code: "AAPL", name: "애플 (Apple)", currency: "USD" },
  { code: "MSFT", name: "마이크로소프트 (Microsoft)", currency: "USD" },
  { code: "NVDA", name: "엔비디아 (NVIDIA)", currency: "USD" },
  { code: "GOOGL", name: "알파벳 A (Google)", currency: "USD" },
  { code: "AMZN", name: "아마존 (Amazon)", currency: "USD" },
  { code: "META", name: "메타 (Meta)", currency: "USD" },
  { code: "TSLA", name: "테슬라 (Tesla)", currency: "USD" },
  { code: "QQQ", name: "인베스코 QQQ (Invesco QQQ)", currency: "USD" },
  { code: "QQQM", name: "인베스코 나스닥100 (QQQM)", currency: "USD" },
  { code: "SPY", name: "SPDR S&P 500 (SPY)", currency: "USD" },
  { code: "IVV", name: "iShares Core S&P 500", currency: "USD" },
  { code: "VOO", name: "Vanguard S&P 500", currency: "USD" },
  { code: "SPYG", name: "SPDR Portfolio S&P 500 Growth", currency: "USD" },
  { code: "SCHD", name: "Schwab US Dividend Equity", currency: "USD" },
  { code: "TLT", name: "iShares 20+ Year Treasury Bond", currency: "USD" },
  { code: "TQQQ", name: "ProShares UltraPro QQQ", currency: "USD" },
  { code: "QLD", name: "ProShares Ultra QQQ", currency: "USD" },
];

function getAllKnownStockList() {
  const map = new Map();
  POPULAR_STOCKS.forEach(s => map.set(s.code.toUpperCase(), { ...s }));
  (dashboard?.holdings || []).forEach(h => {
    if (h.code) {
      map.set(h.code.toUpperCase(), {
        code: h.code.toUpperCase(),
        name: h.name || h.code,
        currency: h.currency || (h.code.length === 6 && /^\d+$/.test(h.code) ? "KRW" : "USD"),
      });
    }
  });
  (actualDividendData?.records || []).forEach(r => {
    if (r.code) {
      map.set(r.code.toUpperCase(), {
        code: r.code.toUpperCase(),
        name: r.name || r.code,
        currency: r.currency || "KRW",
      });
    }
  });
  (pnlData?.records || []).forEach(r => {
    if (r.code) {
      map.set(r.code.toUpperCase(), {
        code: r.code.toUpperCase(),
        name: r.name || r.code,
        currency: r.currency || "KRW",
      });
    }
  });
  return [...map.values()];
}

function populateStockDatalists() {
  const list = getAllKnownStockList();
  const codeListEl = document.getElementById("holdingCodeList");
  const nameListEl = document.getElementById("holdingNameList");

  if (codeListEl) {
    codeListEl.innerHTML = list.map(s => `<option value="${s.code}">${s.name} (${s.currency})</option>`).join("");
  }
  if (nameListEl) {
    nameListEl.innerHTML = list.map(s => `<option value="${s.name}">${s.code} · ${s.currency}</option>`).join("");
  }
}

function attachStockAutoFill(formId, updateFieldsFn) {
  const form = document.getElementById(formId);
  if (!form) return;
  const codeInput = form.querySelector("[name='code']");
  const nameInput = form.querySelector("[name='name']");
  const currSelect = form.querySelector("[name='currency']");

  function onCodeChanged() {
    const raw = (codeInput?.value || "").trim().toUpperCase();
    if (!raw) return;
    const all = getAllKnownStockList();
    const found = all.find(s => s.code.toUpperCase() === raw || s.code.toUpperCase().replace(/\s+/g, '') === raw.replace(/\s+/g, ''));
    if (found) {
      if (nameInput) nameInput.value = found.name;
      if (currSelect && found.currency) currSelect.value = found.currency;
      if (typeof updateFieldsFn === 'function') updateFieldsFn();
    }
  }

  function onNameChanged() {
    const raw = (nameInput?.value || "").trim();
    if (!raw) return;
    const all = getAllKnownStockList();
    const cleanRaw = raw.toLowerCase().replace(/\s+/g, '');
    let found = all.find(s => s.name.toLowerCase().replace(/\s+/g, '') === cleanRaw || s.name === raw);
    if (!found && raw.length >= 2) {
      found = all.find(s => s.name.toLowerCase().includes(cleanRaw) || cleanRaw.includes(s.name.toLowerCase().replace(/\s+/g, '')));
    }
    if (found) {
      if (codeInput) codeInput.value = found.code;
      if (currSelect && found.currency) currSelect.value = found.currency;
      if (typeof updateFieldsFn === 'function') updateFieldsFn();
    }
  }

  if (!codeInput._boundAuto) {
    codeInput._boundAuto = true;
    codeInput.addEventListener("input", onCodeChanged);
    codeInput.addEventListener("change", onCodeChanged);
  }
  if (!nameInput._boundAuto) {
    nameInput._boundAuto = true;
    nameInput.addEventListener("input", onNameChanged);
    nameInput.addEventListener("change", onNameChanged);
  }
}

// 실제 배당금 기록 저장 함수
let isSubmittingDividend = false;
async function saveActualDividendRecord() {
  if (isSubmittingDividend) return;
  const form = document.getElementById("dividendRecordForm");
  if (!form) return;
  const rId = form.dataset.recordId;
  const dateVal = (form.querySelector("[name='date']")?.value || "").trim();
  const ownerVal = (form.querySelector("[name='owner']")?.value || "모두").trim();
  const codeVal = (form.querySelector("[name='code']")?.value || "").trim().toUpperCase();
  const nameVal = (form.querySelector("[name='name']")?.value || "").trim();
  const currVal = (form.querySelector("[name='currency']")?.value || "KRW").toUpperCase();
  const amtInput = form.querySelector("[name='amount']");
  const amtVal = Number(amtInput?.value || 0);
  const fxVal = Number(form.querySelector("[name='fx_rate']")?.value || 1385.0);
  let amtKrwVal = Number(form.querySelector("[name='amount_krw']")?.value || 0);
  if (!amtKrwVal && amtVal) {
    amtKrwVal = currVal === "USD" ? Math.round(amtVal * fxVal) : Math.round(amtVal);
  }
  const memoVal = (form.querySelector("[name='memo']")?.value || "").trim();

  if (!dateVal) {
    toast("입금일을 선택해 주세요.", true);
    return;
  }
  if (!codeVal) {
    toast("종목코드를 입력해 주세요.", true);
    return;
  }
  if (!amtVal && (amtInput?.value === '' || amtInput?.value == null)) {
    toast("배당금(입금액)을 입력해 주세요.", true);
    return;
  }

  const payload = {
    date: dateVal,
    owner: ownerVal,
    code: codeVal,
    name: nameVal || codeVal,
    currency: currVal,
    amount: amtVal,
    fx_rate: fxVal,
    amount_krw: amtKrwVal,
    memo: memoVal,
  };

  isSubmittingDividend = true;
  try {
    const url = rId ? `/api/actual-dividends/${rId}` : "/api/actual-dividends";
    const method = rId ? "PUT" : "POST";
    const res = await api(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    document.getElementById("dividendRecordDialog")?.close();
    toast(res.message || "배당금이 저장되었습니다.");
    await loadActualDividends(currentOwner, selectedDividendYear);
    if (typeof loadDividends === 'function') await loadDividends(currentOwner);
    if (typeof loadDashboard === 'function') await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  } finally {
    isSubmittingDividend = false;
  }
}

// 실제 배당금 파일 가져오기 폼 이벤트
const divImportForm = document.getElementById("dividendImportForm");
if (divImportForm) {
  divImportForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("divImportFileInput");
    if (!fileInput || !fileInput.files.length) {
      toast("가져올 엑셀 또는 CSV 파일을 선택하세요.", true);
      return;
    }
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
      const res = await api("/api/import-dividends", {
        method: "POST",
        body: formData,
      });
      divImportForm.closest("dialog")?.close();
      fileInput.value = "";
      toast(res.message || "배당금 내역을 성공적으로 가져왔습니다.");
      await loadActualDividends(currentOwner);
    } catch (err) {
      toast(err.message || "배당 파일 처리 실패", true);
    }
  });
}

// 12. 데이터 백업 / 복원
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

// ── 15. 배당(분배금) 현황 및 1월~12월 캘린더 ─────────────────────────────────────
// ── 15. 배당(분배금) 현황 및 1월~12월 캘린더 (예상 / 실제 모드 지원) ───────────
let currentDividendMode = 'estimated'; // 'estimated' | 'actual'
let dividendData = null;
let actualDividendData = null;
let selectedDividendMonth = null;
let selectedDividendYear = "2026";

async function loadDividends(owner = currentOwner) {
  try {
    const res = await api(`/api/dividends?owner=${encodeURIComponent(owner)}`);
    dividendData = res;
    if (currentDividendMode === 'estimated') {
      renderDividends(res);
    }
  } catch (err) {
    console.error("배당 정보를 불러오지 못했습니다.", err);
  }
}

async function loadActualDividends(owner = currentOwner, year = selectedDividendYear) {
  try {
    const res = await api(`/api/actual-dividends?owner=${encodeURIComponent(owner)}&year=${encodeURIComponent(year || '')}`);
    actualDividendData = res;
    if (currentDividendMode === 'actual') {
      renderActualDividends(res);
    }
    updateDividendYearOptions(res?.available_years || []);
    if (res) {
      const totalActual = Number(res.total_actual_dividend_krw || 0);
      $("#summaryActualDividend") && ($("#summaryActualDividend").textContent = money(totalActual));
    }
  } catch (err) {
    console.error("실제 배당 정보를 불러오지 못했습니다.", err);
  }
}

function updateDividendYearOptions(years) {
  const sel = document.getElementById("dividendYearSelect");
  if (!sel) return;
  const currentVal = selectedDividendYear;
  const allYears = Array.from(new Set([new Date().getFullYear().toString(), ...years])).sort().reverse();
  
  const opts = allYears.map(y => `<option value="${y}">${y}년</option>`);
  opts.push('<option value="all">전체 기간</option>');
  sel.innerHTML = opts.join('');
  if (allYears.includes(currentVal) || currentVal === 'all') {
    sel.value = currentVal;
  }
}

function renderDividends(data) {
  if (!data) return;
  const fxUsd = (dashboard?.fx_rates?.USD) || 1385.0;

  $("#divCardLabel1") && ($("#divCardLabel1").textContent = "연간 예상 배당금");
  $("#divCardLabel2") && ($("#divCardLabel2").textContent = "포트폴리오 배당수익률");
  $("#divCardLabel3") && ($("#divCardLabel3").textContent = "월평균 예상 배당금");
  $("#divCardLabel4") && ($("#divCardLabel4").textContent = "배당 지급 종목 수");
  $("#dividendChartTitle") && ($("#dividendChartTitle").textContent = "📊 1월 ~ 12월 월별 예상 배당금 추이");

  // 1. 상단 4대 요약 카드
  const totalAnnual = Number(data.total_annual_dividend_krw || 0);
  const totalAnnualUsd = fxUsd > 0 ? (totalAnnual / fxUsd) : 0;
  const yieldRate = Number(data.portfolio_yield || 0);
  const monthlyAvg = Number(data.monthly_avg_dividend_krw || 0);
  const payingCount = Number(data.dividend_paying_count || 0);
  const totalHoldings = (dashboard?.holdings || []).length;

  $("#divTotalAnnual") && ($("#divTotalAnnual").textContent = money(totalAnnual));
  $("#divTotalAnnualUsd") && ($("#divTotalAnnualUsd").textContent = `$${number(totalAnnualUsd, 2)} 환산 포함`);
  $("#divYield") && ($("#divYield").textContent = `${number(yieldRate, 2)}%`);
  $("#divYieldSub") && ($("#divYieldSub").textContent = "총 평가금액 대비");
  $("#divMonthlyAvg") && ($("#divMonthlyAvg").textContent = money(monthlyAvg));
  $("#divPayingCount") && ($("#divPayingCount").textContent = `${payingCount}개`);
  $("#divTotalHoldings") && ($("#divTotalHoldings").textContent = `전체 ${totalHoldings}개 종목 중`);

  // 핵심 요약 패널의 예상 연간 배당금 갱신
  $("#summaryEstimatedDividend") && ($("#summaryEstimatedDividend").textContent = `예상 연간 배당금 ${money(totalAnnual)} (${number(yieldRate, 2)}%)`);

  // 2. 1월~12월 월별 막대그래프 (SVG Bar Chart)
  const schedule = data.monthly_schedule || [];
  const maxMonthly = Math.max(...schedule.map(s => Number(s.total_krw || 0)), 1);

  const w = 900, h = 240, pad = 30;
  const hBarArea = 170;
  const barWidth = 44;

  const bars = schedule.map((item, idx) => {
    const m = item.month;
    const val = Number(item.total_krw || 0);
    const x = pad + ((w - pad * 2) * (idx + 0.5)) / 12 - barWidth / 2;
    const barH = val > 0 ? Math.max(8, (val / maxMonthly) * (hBarArea - 25)) : 2;
    const y = hBarArea - barH;
    const isSelected = selectedDividendMonth === m;

    const itemCount = (item.items || []).length;
    const topText = val > 0 ? money(val) : "-";
    const barFill = isSelected ? "url(#divBarGradActive)" : (val > 0 ? "url(#divBarGrad)" : "#1c263d");

    return `
      <g class="dividend-bar-group" data-month="${m}">
        <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barH.toFixed(1)}" fill="${barFill}" rx="4" opacity="0.95">
          <title>${m}월 예상 배당금: ${money(val)} (${itemCount}개 종목)</title>
        </rect>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="${(y - 6).toFixed(1)}" fill="${val > 0 ? '#f3f5ff' : '#64748b'}" font-size="9.5" font-weight="700" text-anchor="middle">
          ${topText}
        </text>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="${(hBarArea + 16).toFixed(1)}" fill="${isSelected ? '#c4b5fd' : '#94a3b8'}" font-size="11" font-weight="${isSelected ? '700' : '600'}" text-anchor="middle">
          ${m}월
        </text>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="${(hBarArea + 28).toFixed(1)}" fill="${itemCount > 0 ? '#8e70fa' : '#475569'}" font-size="9" font-weight="600" text-anchor="middle">
          ${itemCount > 0 ? itemCount + '종목' : '-'}
        </text>
      </g>
    `;
  }).join('');

  const chartWrap = $("#dividendBarChartWrap");
  if (chartWrap) {
    chartWrap.innerHTML = `
      <svg class="record-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:240px;overflow:visible;">
        <defs>
          <linearGradient id="divBarGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#a78bfa" />
            <stop offset="100%" stop-color="#6366f1" />
          </linearGradient>
          <linearGradient id="divBarGradActive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#38bdf8" />
            <stop offset="100%" stop-color="#818cf8" />
          </linearGradient>
        </defs>
        <line x1="${pad}" y1="${hBarArea}" x2="${w - pad}" y2="${hBarArea}" stroke="#283758" stroke-width="1.2" />
        ${bars}
      </svg>
    `;
  }

  renderMonthlyDividendDetail(selectedDividendMonth);
}

function renderMonthlyDividendDetail(month = null) {
  const container = $("#dividendMonthlyDetail");
  if (!container || !dividendData) return;

  const schedule = dividendData.monthly_schedule || [];
  let title = "전체 배당 지급 종목 (연간 기준)";
  let items = [];

  if (month && month >= 1 && month <= 12) {
    const monthData = schedule.find(s => s.month === month);
    title = `📅 ${month}월 예상 배당 지급 종목 (${(monthData?.items || []).length}개 종목 · 합계 ${money(monthData?.total_krw || 0)})`;
    items = monthData?.items || [];
  } else {
    title = `📅 전체 배당 지급 종목 (${(dividendData.holding_dividends || []).filter(h => h.annual_payout_krw > 0).length}개 종목 · 연간 합계 ${money(dividendData.total_annual_dividend_krw || 0)})`;
    items = (dividendData.holding_dividends || []).filter(h => h.annual_payout_krw > 0).map(h => ({
      code: h.code,
      name: h.name,
      quantity: h.quantity,
      currency: h.currency,
      payout_krw: h.annual_payout_krw,
      payout_orig: h.annual_payout_orig,
      div_yield: h.div_yield,
      months: h.payout_months,
    }));
  }

  if (!items.length) {
    container.innerHTML = `
      <div class="div-detail-header">${title}</div>
      <div class="empty" style="padding:16px;">해당 월에 지급 예정인 배당금 내역이 없습니다.</div>
    `;
    return;
  }

  const cardsHtml = items.map(item => {
    const isUsd = item.currency === 'USD';
    const origText = isUsd ? `$${number(item.payout_orig, 2)}` : money(item.payout_krw);
    const cycleText = item.months ? (item.months.length === 12 ? '월배당' : (item.months.length === 4 ? '분기배당' : `${item.months.join(', ')}월`)) : '';

    return `
      <div class="div-item-card">
        <div class="div-item-info">
          <strong>${html(item.name)}</strong>
          <span>${html(item.code)} · ${number(item.quantity, 2)}주 ${cycleText ? '· ' + cycleText : ''}</span>
        </div>
        <div class="div-item-val">
          <strong>${money(item.payout_krw)}</strong>
          <small>${isUsd ? origText + ' · ' : ''}수익률 ${number(item.div_yield, 2)}%</small>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="div-detail-header">
      ${title}
      ${month ? '<button type="button" class="button text compact" id="clearDivMonthBtn" style="font-size:11px;margin-left:auto;">✕ 전체 보기</button>' : ''}
    </div>
    <div class="div-detail-grid">
      ${cardsHtml}
    </div>
  `;
}

function renderActualDividends(data) {
  if (!data) return;
  const fxUsd = (dashboard?.fx_rates?.USD) || 1385.0;

  $("#divCardLabel1") && ($("#divCardLabel1").textContent = "연간 실제 수령 배당금");
  $("#divCardLabel2") && ($("#divCardLabel2").textContent = "실제 수령 배당수익률");
  $("#divCardLabel3") && ($("#divCardLabel3").textContent = "월평균 실제 수령액");
  $("#divCardLabel4") && ($("#divCardLabel4").textContent = "실제 수령 종목 / 건수");
  $("#dividendChartTitle") && ($("#dividendChartTitle").textContent = "📊 1월 ~ 12월 월별 실제 배당금 입금 추이");

  const totalActual = Number(data.total_actual_dividend_krw || 0);
  const totalActualUsd = fxUsd > 0 ? (totalActual / fxUsd) : 0;
  const totalVal = Number(dashboard?.summary?.total_value_krw || 0);
  const actualYield = totalVal > 0 ? (totalActual / totalVal * 100) : 0;
  const monthlyAvg = Number(data.monthly_avg_dividend_krw || 0);
  const payingStockCount = Number(data.paying_stock_count || 0);
  const recordCount = Number(data.record_count || 0);

  $("#divTotalAnnual") && ($("#divTotalAnnual").textContent = money(totalActual));
  $("#divTotalAnnualUsd") && ($("#divTotalAnnualUsd").textContent = `$${number(totalActualUsd, 2)} 환산 포함`);
  $("#divYield") && ($("#divYield").textContent = `${number(actualYield, 2)}%`);
  $("#divYieldSub") && ($("#divYieldSub").textContent = "총 투자자산 대비");
  $("#divMonthlyAvg") && ($("#divMonthlyAvg").textContent = money(monthlyAvg));
  $("#divPayingCount") && ($("#divPayingCount").textContent = `${payingStockCount}종목`);
  $("#divTotalHoldings") && ($("#divTotalHoldings").textContent = `총 ${recordCount}건 입금`);

  // 1월~12월 실제 배당금 막대 차트 (에메랄드/그린 그라데이션)
  const schedule = data.monthly_schedule || [];
  const maxMonthly = Math.max(...schedule.map(s => Number(s.total_krw || 0)), 1);

  const w = 900, h = 240, pad = 30;
  const hBarArea = 170;
  const barWidth = 44;

  const bars = schedule.map((item, idx) => {
    const m = item.month;
    const val = Number(item.total_krw || 0);
    const x = pad + ((w - pad * 2) * (idx + 0.5)) / 12 - barWidth / 2;
    const barH = val > 0 ? Math.max(8, (val / maxMonthly) * (hBarArea - 25)) : 2;
    const y = hBarArea - barH;
    const isSelected = selectedDividendMonth === m;

    const itemCount = (item.items || []).length;
    const topText = val > 0 ? money(val) : "-";
    const barFill = isSelected ? "url(#actualDivBarGradActive)" : (val > 0 ? "url(#actualDivBarGrad)" : "#1c263d");

    return `
      <g class="dividend-bar-group" data-month="${m}">
        <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barH.toFixed(1)}" fill="${barFill}" rx="4" opacity="0.95">
          <title>${m}월 실제 입금액: ${money(val)} (${itemCount}건)</title>
        </rect>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="${(y - 6).toFixed(1)}" fill="${val > 0 ? '#f43f5e' : '#64748b'}" font-size="9.5" font-weight="700" text-anchor="middle">
          ${topText}
        </text>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="${(hBarArea + 16).toFixed(1)}" fill="${isSelected ? '#f43f5e' : '#94a3b8'}" font-size="11" font-weight="${isSelected ? '700' : '600'}" text-anchor="middle">
          ${m}월
        </text>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="${(hBarArea + 28).toFixed(1)}" fill="${itemCount > 0 ? '#fb7185' : '#475569'}" font-size="9" font-weight="600" text-anchor="middle">
          ${itemCount > 0 ? itemCount + '건' : '-'}
        </text>
      </g>
    `;
  }).join('');

  const chartWrap = $("#dividendBarChartWrap");
  if (chartWrap) {
    chartWrap.innerHTML = `
      <svg class="record-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:240px;overflow:visible;">
        <defs>
          <linearGradient id="actualDivBarGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#fb7185" />
            <stop offset="100%" stop-color="#e11d48" />
          </linearGradient>
          <linearGradient id="actualDivBarGradActive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#f43f5e" />
            <stop offset="100%" stop-color="#fda4af" />
          </linearGradient>
        </defs>
        <line x1="${pad}" y1="${hBarArea}" x2="${w - pad}" y2="${hBarArea}" stroke="#283758" stroke-width="1.2" />
        ${bars}
      </svg>
    `;
  }

  renderActualDividendDetail(selectedDividendMonth);
}

function renderActualDividendDetail(month = null) {
  const container = $("#dividendMonthlyDetail");
  if (!container || !actualDividendData) return;

  const records = actualDividendData.records || [];
  let title = "전체 실제 배당금 입금 내역";
  let items = [];

  if (month && month >= 1 && month <= 12) {
    const monthStr = String(month).padStart(2, '0');
    items = records.filter(r => (r.date || '').split('-')[1] === monthStr);
    const sumKrw = items.reduce((acc, cur) => acc + Number(cur.amount_krw || 0), 0);
    title = `📅 ${month}월 실제 배당금 입금 내역 (${items.length}건 · 합계 <span style="color:#f43f5e;">${money(sumKrw)}</span>)`;
  } else {
    items = records;
    const sumKrw = items.reduce((acc, cur) => acc + Number(cur.amount_krw || 0), 0);
    title = `📅 전체 실제 배당금 입금 내역 (${items.length}건 · 합계 <span style="color:#f43f5e;">${money(sumKrw)}</span>)`;
  }

  if (!items.length) {
    container.innerHTML = `
      <div class="div-detail-header">
        ${title}
        ${month ? '<button type="button" class="button text compact" id="clearDivMonthBtn" style="font-size:11px;margin-left:auto;">✕ 전체 보기</button>' : ''}
      </div>
      <div class="empty" style="padding:16px;">
        등록된 실제 배당금 내역이 없습니다. 상단의 <strong>[➕ 배당 추가]</strong> 또는 <strong>[📂 가져오기]</strong> 버튼으로 입금 내역을 기록해보세요.
      </div>
    `;
    return;
  }

  const rowsHtml = items.map(item => {
    const isUsd = item.currency === 'USD';
    const origAmt = isUsd ? `$${number(item.amount, 2)}` : money(item.amount_krw);
    const fxInfo = isUsd ? `<br><small class="td-fx-info">환율 ${number(item.fx_rate, 1)}원</small>` : '';

    return `
      <tr>
        <td class="center td-date">${html(item.date)}</td>
        <td class="center"><span class="td-owner-badge">${html(item.owner || '모두')}</span></td>
        <td class="td-stock-col">
          <strong class="td-stock-name">${html(item.name || item.code)}</strong>
          <div class="td-stock-code">${html(item.code || '')}</div>
        </td>
        <td class="center"><span class="td-currency">${html(item.currency || 'KRW')}</span></td>
        <td class="num td-orig-amt">${origAmt}${fxInfo}</td>
        <td class="num td-krw-amt pnl-gain-val" style="font-size:13.5px;font-weight:700;">${money(item.amount_krw)}</td>
        <td class="td-memo">${html(item.memo || '-')}</td>
        <td class="center" style="white-space:nowrap;">
          <div class="account-row-actions" style="justify-content:center;">
            <button class="account-action-button edit-actual-div-btn" data-id="${item.id}" title="배당 수정" type="button">✎</button>
            <button class="account-action-button mini-delete-button delete-actual-div-btn" data-id="${item.id}" title="배당 삭제" type="button">🗑️</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <div class="div-detail-header">
      ${title}
      ${month ? '<button type="button" class="button text compact" id="clearDivMonthBtn" style="font-size:11px;margin-left:auto;">✕ 전체 보기</button>' : ''}
    </div>
    <div class="detail-table-wrap">
      <table class="detail-table">
        <thead>
          <tr>
            <th class="center" style="width:90px;">입금일</th>
            <th class="center" style="width:70px;">소유자</th>
            <th>종목명 (코드)</th>
            <th class="center" style="width:60px;">통화</th>
            <th style="text-align:right;width:110px;">입금액</th>
            <th style="text-align:right;width:120px;">원화 환산금액</th>
            <th>메모 / 계좌</th>
            <th class="center" style="width:65px;">관리</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>
    </div>
  `;
}

function openDividendRecordDialog(record = null) {
  const dlg = document.getElementById("dividendRecordDialog");
  const form = document.getElementById("dividendRecordForm");
  if (!dlg || !form) return;

  form.reset();
  form.dataset.recordId = record ? record.id : "";
  $("#dividendDialogTitle") && ($("#dividendDialogTitle").textContent = record ? "실제 배당금 수정" : "실제 배당금 추가");

  populateStockDatalists();
  attachStockAutoFill("dividendRecordForm", updateDivFormFields);

  const today = new Date().toISOString().slice(0, 10);
  const fxUsd = (dashboard?.fx_rates?.USD) || 1385.0;

  const dateEl = form.querySelector("[name='date']");
  const ownerEl = form.querySelector("[name='owner']");
  const codeEl = form.querySelector("[name='code']");
  const nameEl = form.querySelector("[name='name']");
  const currEl = form.querySelector("[name='currency']");
  const amtEl = form.querySelector("[name='amount']");
  const fxEl = form.querySelector("[name='fx_rate']");
  const amtKrwEl = form.querySelector("[name='amount_krw']");
  const memoEl = form.querySelector("[name='memo']");

  if (dateEl) dateEl.value = record ? record.date : today;
  if (ownerEl) ownerEl.value = record ? (record.owner || "모두") : (currentOwner !== "모두" ? currentOwner : "모두");
  if (codeEl) codeEl.value = record ? record.code : "";
  if (nameEl) nameEl.value = record ? record.name : "";
  if (currEl) currEl.value = record ? record.currency : "KRW";
  if (amtEl) amtEl.value = record ? record.amount : "";
  if (fxEl) fxEl.value = record ? record.fx_rate : fxUsd;
  if (amtKrwEl) amtKrwEl.value = record ? record.amount_krw : "";
  if (memoEl) memoEl.value = record ? (record.memo || "") : "";

  updateDivFormFields();
  dlg.showModal();
}

function updateDivFormFields() {
  const form = document.getElementById("dividendRecordForm");
  if (!form) return;
  const isUsd = form.currency.value === "USD";
  const fxField = document.getElementById("fxRateField");
  const krwField = document.getElementById("amountKrwField");
  if (fxField) fxField.style.display = isUsd ? "flex" : "none";
  if (krwField) krwField.style.display = isUsd ? "flex" : "none";

  const amt = Number(form.amount.value || 0);
  const fx = Number(form.fx_rate.value || (dashboard?.fx_rates?.USD) || 1385.0);
  if (isUsd) {
    form.amount_krw.value = Math.round(amt * fx);
  } else {
    form.amount_krw.value = Math.round(amt);
  }
}

// ── 16. 주식 매도 실현손익 관리 (Realized PnL) ──────────────────────────────
let pnlData = null;
let selectedPnlMonth = null;
let selectedPnlYear = "2026";
let currentPnlTradeType = "all"; // 'all' | 'ipo'

async function loadRealizedPnl(owner = currentOwner, year = selectedPnlYear, tradeType = currentPnlTradeType) {
  try {
    const res = await api(`/api/realized-pnl?owner=${encodeURIComponent(owner)}&year=${encodeURIComponent(year || '')}&trade_type=${encodeURIComponent(tradeType || 'all')}`);
    pnlData = res;
    renderRealizedPnl(res);
    updatePnlYearOptions(res?.available_years || []);
  } catch (err) {
    console.error("매도 실현손익을 불러오지 못했습니다.", err);
  }
}

function updatePnlYearOptions(years) {
  const sel = document.getElementById("pnlYearSelect");
  if (!sel) return;
  const currentVal = selectedPnlYear;
  const allYears = Array.from(new Set([new Date().getFullYear().toString(), ...years])).sort().reverse();
  
  const opts = allYears.map(y => `<option value="${y}">${y}년</option>`);
  opts.push('<option value="all">전체 기간</option>');
  sel.innerHTML = opts.join('');
  if (allYears.includes(currentVal) || currentVal === 'all') {
    sel.value = currentVal;
  }
}

function renderRealizedPnl(data) {
  if (!data) return;

  const totalPnl = Number(data.total_pnl_krw || 0);
  const totalWin = Number(data.total_win_krw || 0);
  const winCount = Number(data.win_count || 0);
  const totalLoss = Number(data.total_loss_krw || 0);
  const lossCount = Number(data.loss_count || 0);
  const winRate = Number(data.win_rate || 0);
  const recordCount = Number(data.record_count || 0);

  // 1. 4대 요약 카드
  const totalEl = $("#pnlTotal");
  if (totalEl) {
    totalEl.textContent = `${totalPnl > 0 ? '+' : ''}${money(totalPnl)}`;
    totalEl.className = `div-card-val ${totalPnl > 0 ? 'gain' : (totalPnl < 0 ? 'loss' : '')}`;
  }
  $("#pnlTotalCount") && ($("#pnlTotalCount").textContent = `총 ${recordCount}건 매도`);

  $("#pnlTotalWin") && ($("#pnlTotalWin").textContent = `+${money(totalWin)}`);
  $("#pnlWinCount") && ($("#pnlWinCount").textContent = `${winCount}건 실현`);

  $("#pnlTotalLoss") && ($("#pnlTotalLoss").textContent = `${money(totalLoss)}`);
  $("#pnlLossCount") && ($("#pnlLossCount").textContent = `${lossCount}건 실현`);

  const winRateEl = $("#pnlWinRate");
  if (winRateEl) {
    winRateEl.textContent = `${number(winRate, 1)}%`;
    winRateEl.className = `div-card-val ${winRate >= 50 ? 'gain' : ''}`;
  }

  // 핵심 요약 패널의 전체 실현손익 갱신
  const summaryPnlEl = $("#summaryRealizedPnl");
  if (summaryPnlEl) {
    summaryPnlEl.textContent = `${totalPnl > 0 ? '+' : ''}${money(totalPnl)}`;
    summaryPnlEl.className = `${totalPnl > 0 ? 'gain up' : (totalPnl < 0 ? 'loss down' : '')}`;
  }
  $("#summaryRealizedPnlSub") && ($("#summaryRealizedPnlSub").textContent = `승률 ${number(winRate, 1)}% · 총 ${recordCount}건 실현`);

  // 2. 1월~12월 양방향 막대그래프 (SVG Bar Chart)
  const schedule = data.monthly_schedule || [];
  const maxAbsPnl = Math.max(
    ...schedule.map(s => Math.abs(Number(s.total_krw || 0))),
    100000
  );

  const w = 900, h = 240, pad = 30;
  const zeroY = 120; // 0원 기준선 중앙
  const maxBarH = 80;
  const barWidth = 44;

  const bars = schedule.map((item, idx) => {
    const m = item.month;
    const val = Number(item.total_krw || 0);
    const x = pad + ((w - pad * 2) * (idx + 0.5)) / 12 - barWidth / 2;
    const isSelected = selectedPnlMonth === m;
    const itemCount = (item.items || []).length;

    let barH = 2, y = zeroY - 1;
    let barFill = "#1c263d";
    let textY = zeroY - 8;

    if (val > 0) {
      barH = Math.max(6, (val / maxAbsPnl) * maxBarH);
      y = zeroY - barH;
      barFill = isSelected ? "url(#pnlGainBarGradActive)" : "url(#pnlGainBarGrad)";
      textY = y - 6;
    } else if (val < 0) {
      barH = Math.max(6, (Math.abs(val) / maxAbsPnl) * maxBarH);
      y = zeroY;
      barFill = isSelected ? "url(#pnlLossBarGradActive)" : "url(#pnlLossBarGrad)";
      textY = y + barH + 12;
    }

    const topText = val !== 0 ? `${val > 0 ? '+' : ''}${money(val)}` : '-';
    const textColor = val > 0 ? '#f43f5e' : (val < 0 ? '#38bdf8' : '#64748b');

    return `
      <g class="pnl-bar-group" data-month="${m}">
        <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barH.toFixed(1)}" fill="${barFill}" rx="4" opacity="0.95">
          <title>${m}월 실현손익: ${money(val)} (${itemCount}건)</title>
        </rect>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="${textY.toFixed(1)}" fill="${textColor}" font-size="9.5" font-weight="700" text-anchor="middle">
          ${topText}
        </text>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="215" fill="${isSelected ? '#f59e0b' : '#94a3b8'}" font-size="11" font-weight="${isSelected ? '700' : '600'}" text-anchor="middle">
          ${m}월
        </text>
        <text x="${(x + barWidth / 2).toFixed(1)}" y="228" fill="${itemCount > 0 ? '#fbbf24' : '#475569'}" font-size="9" font-weight="600" text-anchor="middle">
          ${itemCount > 0 ? itemCount + '건' : '-'}
        </text>
      </g>
    `;
  }).join('');

  const chartWrap = $("#pnlBarChartWrap");
  if (chartWrap) {
    chartWrap.innerHTML = `
      <svg class="record-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:240px;overflow:visible;">
        <defs>
          <linearGradient id="pnlGainBarGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#fb7185" />
            <stop offset="100%" stop-color="#e11d48" />
          </linearGradient>
          <linearGradient id="pnlGainBarGradActive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#f43f5e" />
            <stop offset="100%" stop-color="#fda4af" />
          </linearGradient>
          <linearGradient id="pnlLossBarGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#0284c7" />
            <stop offset="100%" stop-color="#0369a1" />
          </linearGradient>
          <linearGradient id="pnlLossBarGradActive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#38bdf8" />
            <stop offset="100%" stop-color="#7dd3fc" />
          </linearGradient>
        </defs>
        <!-- 0원 기준 중심선 -->
        <line x1="${pad}" y1="${zeroY}" x2="${w - pad}" y2="${zeroY}" stroke="#334155" stroke-dasharray="3 3" stroke-width="1.2" />
        <line x1="${pad}" y1="200" x2="${w - pad}" y2="200" stroke="#1e293b" stroke-width="1" />
        ${bars}
      </svg>
    `;
  }

  renderPnlMonthlyDetail(selectedPnlMonth);
}

function renderPnlMonthlyDetail(month = null) {
  const container = $("#pnlMonthlyDetail");
  if (!container || !pnlData) return;

  const records = pnlData.records || [];
  let title = "전체 매도 실현손익 내역";
  let items = [];

  if (month && month >= 1 && month <= 12) {
    const monthStr = String(month).padStart(2, '0');
    items = records.filter(r => (r.date || '').split('-')[1] === monthStr);
    const sumKrw = items.reduce((acc, cur) => acc + Number(cur.pnl_krw || 0), 0);
    title = `📅 ${month}월 매도 실현손익 내역 (${items.length}건 · 합계 ${sumKrw > 0 ? '+' : ''}${money(sumKrw)})`;
  } else {
    items = records;
    const sumKrw = items.reduce((acc, cur) => acc + Number(cur.pnl_krw || 0), 0);
    title = `📅 전체 매도 실현손익 내역 (${items.length}건 · 총합 ${sumKrw > 0 ? '+' : ''}${money(sumKrw)})`;
  }

  if (!items.length) {
    container.innerHTML = `
      <div class="div-detail-header">
        ${title}
        ${month ? '<button type="button" class="button text compact" id="clearPnlMonthBtn" style="font-size:11px;margin-left:auto;">✕ 전체 보기</button>' : ''}
      </div>
      <div class="empty" style="padding:16px;">
        등록된 매도 실현손익 내역이 없습니다. 상단의 <strong>[➕ 손익 추가]</strong> 또는 <strong>[📂 가져오기]</strong> 버튼으로 매도 기록을 등록해보세요.
      </div>
    `;
    return;
  }

  const rowsHtml = items.map(item => {
    const isUsd = item.currency === 'USD';
    const pnlVal = Number(item.pnl_krw || 0);
    const sign = pnlVal > 0 ? '+' : '';
    const colorClass = pnlVal > 0 ? 'pnl-gain-val' : (pnlVal < 0 ? 'pnl-loss-val' : 'pnl-zero-val');
    const origText = isUsd ? `${Number(item.pnl) > 0 ? '+' : ''}$${number(item.pnl, 2)}` : '';
    const fxInfo = isUsd ? `<br><small style="color:#8da0c7;">환율 ${number(item.fx_rate, 1)}원</small>` : '';

    return `
      <tr>
        <td class="center td-date">${html(item.date)}</td>
        <td class="center"><span class="td-owner-badge">${html(item.owner || '모두')}</span></td>
        <td class="td-stock-col">
          <strong class="td-stock-name">${html(item.name || item.code)}</strong>
          <div class="td-stock-code">${html(item.code || '')}</div>
        </td>
        <td class="center">
          ${item.is_ipo ? '<span class="td-ipo-badge">📦 공모주</span>' : '<span class="td-normal-badge">일반거래</span>'}
        </td>
        <td class="center"><span class="td-currency">${html(item.currency || 'KRW')}</span></td>
        <td class="num td-orig-amt">${isUsd ? origText : sign + money(item.pnl_krw)}${fxInfo}</td>
        <td class="num ${colorClass}" style="font-size:13.5px;font-weight:700;">${sign}${money(item.pnl_krw)}</td>
        <td class="td-memo">${html(item.memo || '-')}</td>
        <td class="center" style="white-space:nowrap;">
          <div class="account-row-actions" style="justify-content:center;">
            <button class="account-action-button edit-pnl-btn" data-id="${item.id}" title="손익 수정" type="button">✎</button>
            <button class="account-action-button mini-delete-button delete-pnl-btn" data-id="${item.id}" title="손익 삭제" type="button">🗑️</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <div class="div-detail-header">
      ${title}
      ${month ? '<button type="button" class="button text compact" id="clearPnlMonthBtn" style="font-size:11px;margin-left:auto;">✕ 전체 보기</button>' : ''}
    </div>
    <div class="detail-table-wrap">
      <table class="detail-table">
        <thead>
          <tr>
            <th class="center" style="width:90px;">매도일</th>
            <th class="center" style="width:70px;">소유자</th>
            <th>종목명 (코드)</th>
            <th class="center" style="width:80px;">유형</th>
            <th class="center" style="width:60px;">통화</th>
            <th style="text-align:right;width:110px;">실현손익</th>
            <th style="text-align:right;width:120px;">원화 환산손익</th>
            <th>메모 / 계좌</th>
            <th class="center" style="width:65px;">관리</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>
    </div>
  `;
}

function openPnlRecordDialog(record = null) {
  const dlg = document.getElementById("pnlRecordDialog");
  const form = document.getElementById("pnlRecordForm");
  if (!dlg || !form) return;

  form.reset();
  form.dataset.recordId = record ? record.id : "";
  $("#pnlDialogTitle") && ($("#pnlDialogTitle").textContent = record ? "매도 실현손익 수정" : "매도 실현손익 추가");

  populateStockDatalists();
  attachStockAutoFill("pnlRecordForm", updatePnlFormFields);

  const today = new Date().toISOString().slice(0, 10);
  const fxUsd = (dashboard?.fx_rates?.USD) || 1385.0;

  const dateEl = form.querySelector("[name='date']");
  const ownerEl = form.querySelector("[name='owner']");
  const brokerEl = form.querySelector("[name='broker']");
  const accEl = form.querySelector("[name='account_name']");
  const codeEl = form.querySelector("[name='code']");
  const nameEl = form.querySelector("[name='name']");
  const currEl = form.querySelector("[name='currency']");
  const pnlEl = form.querySelector("[name='pnl']");
  const fxEl = form.querySelector("[name='fx_rate']");
  const pnlKrwEl = form.querySelector("[name='pnl_krw']");
  const isIpoEl = form.querySelector("[name='is_ipo']");
  const memoEl = form.querySelector("[name='memo']");

  if (dateEl) dateEl.value = record ? record.date : today;
  if (ownerEl) ownerEl.value = record ? (record.owner || "모두") : (currentOwner !== "모두" ? currentOwner : "모두");
  if (brokerEl) brokerEl.value = record ? (record.broker || "") : "";
  if (accEl) accEl.value = record ? (record.account_name || "") : "";
  if (codeEl) codeEl.value = record ? record.code : "";
  if (nameEl) nameEl.value = record ? record.name : "";
  if (currEl) currEl.value = record ? record.currency : "KRW";
  if (pnlEl) pnlEl.value = record ? record.pnl : "";
  if (fxEl) fxEl.value = record ? record.fx_rate : fxUsd;
  if (pnlKrwEl) pnlKrwEl.value = record ? record.pnl_krw : "";
  if (isIpoEl) isIpoEl.value = (record && record.is_ipo) ? "true" : "false";
  if (memoEl) memoEl.value = record ? (record.memo || "") : "";

  updatePnlFormFields();
  dlg.showModal();
}

function updatePnlFormFields() {
  const form = document.getElementById("pnlRecordForm");
  if (!form) return;
  const isUsd = form.currency.value === "USD";
  const fxField = document.getElementById("pnlFxRateField");
  const krwField = document.getElementById("pnlAmountKrwField");
  if (fxField) fxField.style.display = isUsd ? "flex" : "none";
  if (krwField) krwField.style.display = isUsd ? "flex" : "none";

  const pnl = Number(form.pnl.value || 0);
  const fx = Number(form.fx_rate.value || (dashboard?.fx_rates?.USD) || 1385.0);
  if (isUsd) {
    form.pnl_krw.value = Math.round(pnl * fx);
  } else {
    form.pnl_krw.value = Math.round(pnl);
  }
}

// 실현손익 단건 등록 폼 이벤트
let isSubmittingPnl = false;
async function saveRealizedPnlRecord() {
  if (isSubmittingPnl) return;
  const form = document.getElementById("pnlRecordForm");
  if (!form) return;
  const rId = form.dataset.recordId;
  const dateVal = (form.querySelector("[name='date']")?.value || "").trim();
  const ownerVal = (form.querySelector("[name='owner']")?.value || "모두").trim();
  const brokerVal = (form.querySelector("[name='broker']")?.value || "").trim();
  const accountNameVal = (form.querySelector("[name='account_name']")?.value || "").trim();
  const codeVal = (form.querySelector("[name='code']")?.value || "").trim().toUpperCase();
  const nameVal = (form.querySelector("[name='name']")?.value || "").trim();
  const currVal = (form.querySelector("[name='currency']")?.value || "KRW").toUpperCase();
  const pnlInputStr = form.querySelector("[name='pnl']")?.value;
  const pnlVal = Number(pnlInputStr || 0);
  const fxVal = Number(form.querySelector("[name='fx_rate']")?.value || 1385.0);
  let pnlKrwVal = Number(form.querySelector("[name='pnl_krw']")?.value || 0);
  if (!pnlKrwVal && pnlVal) {
    pnlKrwVal = currVal === "USD" ? Math.round(pnlVal * fxVal) : Math.round(pnlVal);
  }
  const isIpoVal = form.querySelector("[name='is_ipo']")?.value === "true";
  const memoVal = (form.querySelector("[name='memo']")?.value || "").trim();

  if (!dateVal) {
    toast("매도일을 선택해 주세요.", true);
    return;
  }
  if (!codeVal) {
    toast("종목코드를 입력해 주세요.", true);
    return;
  }
  if (pnlInputStr === '' || pnlInputStr == null) {
    toast("실현손익을 입력해 주세요.", true);
    return;
  }

  const payload = {
    date: dateVal,
    owner: ownerVal,
    broker: brokerVal,
    account_name: accountNameVal,
    code: codeVal,
    name: nameVal || codeVal,
    currency: currVal,
    pnl: pnlVal,
    fx_rate: fxVal,
    pnl_krw: pnlKrwVal,
    is_ipo: isIpoVal,
    memo: memoVal,
  };

  isSubmittingPnl = true;
  try {
    const url = rId ? `/api/realized-pnl/${rId}` : "/api/realized-pnl";
    const method = rId ? "PUT" : "POST";
    const res = await api(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    document.getElementById("pnlRecordDialog")?.close();
    toast(res.message || "매도 실현손익이 저장되었습니다.");
    await loadRealizedPnl(currentOwner, selectedPnlYear, currentPnlTradeType);
    if (typeof loadDashboard === 'function') await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  } finally {
    isSubmittingPnl = false;
  }
}

document.querySelector("#pnlRecordForm [name='code']")?.addEventListener("input", (e) => {
  const form = document.getElementById("pnlRecordForm");
  if (!form) return;
  const val = e.target.value.trim().toUpperCase();
  const match = (dashboard?.holdings || []).find(h => h.code.toUpperCase() === val || h.name === val);
  if (match) {
    const nameEl = form.querySelector("[name='name']");
    const currEl = form.querySelector("[name='currency']");
    if (nameEl) nameEl.value = match.name;
    if (currEl) currEl.value = match.currency || "KRW";
    if (typeof updatePnlFormFields === 'function') updatePnlFormFields();
  }
});

document.querySelector("#pnlRecordForm [name='currency']")?.addEventListener("change", () => {
  if (typeof updatePnlFormFields === 'function') updatePnlFormFields();
});
document.querySelector("#pnlRecordForm [name='pnl']")?.addEventListener("input", () => {
  if (typeof updatePnlFormFields === 'function') updatePnlFormFields();
});
document.querySelector("#pnlRecordForm [name='fx_rate']")?.addEventListener("input", () => {
  if (typeof updatePnlFormFields === 'function') updatePnlFormFields();
});

// 실현손익 파일 가져오기 폼 이벤트
const pnlImportForm = document.getElementById("pnlImportForm");
if (pnlImportForm) {
  pnlImportForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("pnlImportFileInput");
    if (!fileInput || !fileInput.files.length) {
      toast("가져올 엑셀 또는 CSV 파일을 선택하세요.", true);
      return;
    }
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
      const res = await api("/api/import-realized-pnl", {
        method: "POST",
        body: formData,
      });
      pnlImportForm.closest("dialog")?.close();
      fileInput.value = "";
      toast(res.message || "실현손익 내역을 성공적으로 가져왔습니다.");
      await loadRealizedPnl(currentOwner, selectedPnlYear, currentPnlTradeType);
    } catch (err) {
      toast(err.message || "실현손익 파일 처리 실패", true);
    }
  });
}

// 배당 연도 셀렉트 변경 이벤트
document.getElementById("dividendYearSelect")?.addEventListener("change", (e) => {
  selectedDividendYear = e.target.value;
  selectedDividendMonth = null;
  loadActualDividends(currentOwner, selectedDividendYear);
});

// 실현손익 연도 셀렉트 변경 이벤트
document.getElementById("pnlYearSelect")?.addEventListener("change", (e) => {
  selectedPnlYear = e.target.value;
  selectedPnlMonth = null;
  loadRealizedPnl(currentOwner, selectedPnlYear, currentPnlTradeType);
});

// ── 화면 테마 관리 (Theme Switcher) ────────────────────────────────────────
function setAppTheme(theme) {
  const validThemes = ['purple', 'oled', 'white'];
  if (!validThemes.includes(theme)) theme = 'purple';

  if (theme === 'purple') {
    document.documentElement.removeAttribute('data-theme');
  } else {
    document.documentElement.setAttribute('data-theme', theme);
  }

  document.querySelectorAll('#themeSwitcherTabs .theme-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.theme === theme);
  });

  try {
    localStorage.setItem('app_theme', theme);
  } catch (e) {}
}

function initAppTheme() {
  let savedTheme = 'purple';
  try {
    savedTheme = localStorage.getItem('app_theme') || 'purple';
  } catch (e) {}
  setAppTheme(savedTheme);
}

// ── 섹션 접기 / 펼치기 관리 (Accordion / Collapse) ───────────────────────────
const SECTION_MAP = {
  summary: '#summaryPanel',
  allocation: '#allocationPanel',
  records: '#recordsPanel',
  heatmap: '#assetHeatmapPanel',
  dividend: '#dividendPanel',
  pnl: '#realizedPnlPanel',
  market: '#marketPanel',
  accounts: '#accountsPanel',
  holdings: '#holdingsPanel'
};

function getCollapsedSections() {
  try {
    return JSON.parse(localStorage.getItem('collapsed_sections') || '[]');
  } catch (e) {
    return [];
  }
}

function saveCollapsedSections(list) {
  try {
    localStorage.setItem('collapsed_sections', JSON.stringify(list));
  } catch (e) {}
}

function toggleSection(sectionKey) {
  if (!sectionKey) return;
  let list = getCollapsedSections();
  const isNowCollapsed = list.includes(sectionKey);

  if (isNowCollapsed) {
    list = list.filter(k => k !== sectionKey);
  } else {
    list.push(sectionKey);
  }
  saveCollapsedSections(list);

  applySectionCollapsedState(sectionKey, !isNowCollapsed);
}

function applySectionCollapsedState(sectionKey, isCollapsed) {
  const selector = SECTION_MAP[sectionKey];
  const panel = selector ? document.querySelector(selector) : null;
  const btn = document.querySelector(`.section-collapse-btn[data-section="${sectionKey}"]`);

  if (btn) {
    btn.classList.toggle('is-collapsed', isCollapsed);
    btn.textContent = isCollapsed ? '▶' : '▼';
  }

  if (panel) {
    panel.classList.toggle('is-collapsed', isCollapsed);
  }
}

function initCollapsedSections() {
  const list = getCollapsedSections();
  list.forEach(key => {
    applySectionCollapsedState(key, true);
  });
}

// ── APP BOOTSTRAP ─────────────────────────────────────────────────────────────
async function bootstrap() {
  initAppTheme();
  initCollapsedSections();
  try { await loadFamilyMembers(); } catch (e) {}
  try { await loadDashboard(); } catch (e) { toast(e.message || "대시보드를 불러오지 못했습니다.", true); }
  try { await loadMarkets(); } catch (e) {}
  try { await loadAssetRecords('모두'); } catch (e) {}
  try { await loadDividends('모두'); } catch (e) {}
  try { await loadActualDividends('모두', selectedDividendYear); } catch (e) {}
  try { await loadRealizedPnl('모두', selectedPnlYear, currentPnlTradeType); } catch (e) {}
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}