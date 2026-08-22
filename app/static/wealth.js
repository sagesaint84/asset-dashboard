const $ = (selector) => document.querySelector(selector);
let dashboard = null;
let rawDashboard = null; // 필터링 전 원본 서버 데이터
let currentOwner = '모두'; // 선택된 가족 구성원

// ── 가족 구성원 선택 – 탑바 + ACCOUNTS 탭 동기화 ─────────────────────────────
function selectOwner(owner) {
  currentOwner = owner || '모두';
  // ACCOUNTS 탭 업데이트
  document.querySelectorAll('#familyTabs .family-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.owner === currentOwner);
  });
  // 탑바 탭 업데이트
  document.querySelectorAll('#topbarFamilyTabs .family-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.owner === currentOwner);
  });
  if (rawDashboard) renderWithOwner(rawDashboard, currentOwner);
}

document.addEventListener('click', (e) => {
  // ACCOUNTS 탭
  const accountsTab = e.target.closest('#familyTabs .family-tab');
  if (accountsTab) { selectOwner(accountsTab.dataset.owner); return; }
  // 탑바 탭
  const topbarTab = e.target.closest('#topbarFamilyTabs .family-tab');
  if (topbarTab) { selectOwner(topbarTab.dataset.owner); return; }
});

// ── 필터링된 데이터로 핵심 요약 재계산 ──────────────────────────────────────
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

// 서버 분류 로직과 동일하게 ETF/주식/해외 구분
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
    filteredData.classifications  = computeFilteredClassifications(filteredData.holdings, filteredData.accounts, src.fx_rates);
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
}

// 다이얼로그의 X/취소 버튼은 항상 명시적으로 창을 닫습니다.
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
  const gradId = `spark-grad-${Math.random().toString(36).slice(2, 8)}`;

  return `
    <svg class="sparkline" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.32" />
          <stop offset="100%" stop-color="${color}" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <polyline points="${polylineStr} ${w - pad},${h} ${pad},${h}" fill="url(#${gradId})" stroke="none" />
      <polyline points="${polylineStr}" fill="none" stroke="${color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="${lastX}" cy="${lastY}" r="2.8" fill="${color}" stroke="#0b1120" stroke-width="1.2" />
    </svg>
  `;
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || result.message || "요청을 처리하지 못했습니다.");
  return result;
}

let toastTimer;
let assetRecords = [];
function toast(message, isError = false) {
  const element = $("#toast"); element.textContent = message; element.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { element.className = "toast"; }, 3600);
}
function busy(button, enabled) {
  if (!button) return;
  button.dataset.label ??= button.textContent;
  button.disabled = enabled; button.textContent = enabled ? "처리 중…" : button.dataset.label;
}
async function action(button, request, after = loadDashboard) {
  busy(button, true);
  try { const result = await request(); toast(result.message || "반영했습니다."); if (after) await after(); }
  catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

function chartPath(points, width = 900, height = 260, pad = 24) {
  if (!points.length) return "";
  const values = points.map((point) => Number(point.total_value_krw ?? point.value_krw ?? 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return points.map((point, index) => {
    const x = pad + ((width - pad * 2) * index) / Math.max(points.length - 1, 1);
    const y = height - pad - ((Number(point.total_value_krw ?? point.value_krw ?? 0) - min) / span) * (height - pad * 2);
    return `${x},${y}`;
  }).join(" ");
}

function renderAssetRecords(records) {
  assetRecords = [...records].sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
  const wrap = $("#assetChart");
  if (!assetRecords.length) {
    wrap.innerHTML = '<div class="empty">아직 자산기록이 없습니다. 오늘 기록을 저장해 보세요.</div>';
    $("#assetRecordList").innerHTML = "";
    $("#recordCount").textContent = "0개 기록";
    return;
  }
  const chartRecords = [...assetRecords].sort((a, b) => String(a.date || "").localeCompare(String(b.date || "")));
  const values = chartRecords.map((item) => Number(item.total_value_krw || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const path = chartPath(chartRecords);
  const baseline = `${24},${236} ${876},${236}`;
  const first = chartRecords[0];
  const last = chartRecords.at(-1);
  wrap.innerHTML = `
    <svg class="record-chart" viewBox="0 0 900 260" preserveAspectRatio="none" aria-label="자산 기록 차트">
      <defs>
        <linearGradient id="recordFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#8e70fa" stop-opacity="0.35" />
          <stop offset="100%" stop-color="#8e70fa" stop-opacity="0" />
        </linearGradient>
      </defs>
      <line x1="24" y1="236" x2="876" y2="236" stroke="#2a3557" stroke-width="1" />
      <polyline points="${path}" fill="none" stroke="#8e70fa" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" />
      <polyline points="${path} ${baseline}" fill="url(#recordFill)" stroke="none" />
    </svg>
    <div class="record-chart-meta">
      <div><span>최초 기록</span><strong>${html(first.date)}</strong><small>${money(first.total_value_krw)}</small></div>
      <div><span>최근 기록</span><strong>${html(last.date)}</strong><small>${money(last.total_value_krw)}</small></div>
      <div><span>최저 / 최고</span><strong>${money(min)} / ${money(max)}</strong><small>총 ${number(assetRecords.length, 0)}개</small></div>
    </div>`;
  const delta = Number(last.total_value_krw || 0) - Number(first.total_value_krw || 0);
  const deltaRate = Number(first.total_value_krw || 0) ? delta / Number(first.total_value_krw || 0) * 100 : 0;
  $("#recordSummary").textContent = `${money(delta)} (${deltaRate >= 0 ? "+" : ""}${number(deltaRate)}%)`;
  $("#recordSummary").className = signClass(delta);
  $("#recordCount").textContent = `${number(assetRecords.length, 0)}개 기록`;
  $("#assetRecordList").innerHTML = assetRecords.map((item) => `
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

function renderMarkets(result) {
  const rows = [
    ...result.markets,
    {
      symbol: "USD/KRW",
      label: "달러 환율",
      note: "달러/원 환율",
      price: result.exchange_rate.rate,
      currency: "KRW",
      change: result.exchange_rate.change,
      change_rate: result.exchange_rate.change_rate,
      updated_at: result.exchange_rate.valid_until,
      series: result.exchange_rate.series || [result.exchange_rate.rate],
    },
  ];

  $("#marketGrid").innerHTML = rows.map((item) => {
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
            <span class="market-symbol-tag">${html(item.symbol)}</span>
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
  catch (error) { $("#marketGrid").innerHTML = `<article class="market-card"><p>시장 스냅샷을 불러오지 못했습니다.</p><small>${html(error.message)}</small></article>`; }
}

function renderSummary(data) {
  const s = data.summary, currencies = data.currency_summary || {};
  const krw = currencies.KRW || {}, usd = currencies.USD || {};

  // 1. 총 투자자산
  $("#totalValue").textContent = money(s.total_value_krw);
  const cashNote = s.total_cash_krw ? `주식 ${money(s.total_stock_value_krw || (s.total_value_krw - s.total_cash_krw))} · 예수금 ${money(s.total_cash_krw)}` : `보유 종목 ${number(s.holding_count, 0)}개 · ${number(s.account_count, 0)}개 계좌`;
  $("#holdingCaption").textContent = cashNote;

  // 2. 총 수익
  $("#totalProfit").textContent = money(s.profit_krw);
  $("#totalProfit").className = signClass(s.profit_krw);
  const profitRateEl = $("#profitRate");
  if (profitRateEl) {
    profitRateEl.textContent = `(${s.return_rate >= 0 ? "+" : ""}${number(s.return_rate)}%)`;
    profitRateEl.className = `sub-rate ${signClass(s.profit_krw)}`;
  }
  $("#profitCaption").textContent = `총 매입 ${money(s.total_cost_krw)}`;

  // 3. 일간 수익
  const day = data.day_change || {};
  $("#dayProfit").textContent = day.change_krw == null ? "—" : `${day.change_krw >= 0 ? "+" : ""}${money(day.change_krw)}`;
  $("#dayProfit").className = day.change_krw == null ? "" : signClass(day.change_krw);
  const dayRateEl = $("#dayRate");
  if (dayRateEl) {
    dayRateEl.textContent = day.change_rate == null ? "" : `(${day.change_rate >= 0 ? "+" : ""}${number(day.change_rate)}%)`;
    dayRateEl.className = day.change_rate == null ? "sub-rate" : `sub-rate ${signClass(day.change_krw)}`;
  }
  $("#dayCaption").textContent = day.change_krw == null ? "전일 기준 데이터 수집 중" : `${day.date} 대비`;

  // 4. 원화 자산
  const krwStock = krw.stock_value_krw || (Number(krw.market_value_krw || 0) - Number(krw.cash || 0));
  $("#krwValue").textContent = money(krw.market_value_krw || 0);
  const krwCashBadgeEl = $("#krwCashBadge");
  if (krwCashBadgeEl) {
    krwCashBadgeEl.textContent = `(예수금 ${money(krw.cash || 0)})`;
  }
  $("#krwCaption").textContent = `주식 평가 ${money(krwStock)}`;

  // 5. 달러 자산
  const usdStock = usd.stock_value || (Number(usd.market_value || 0) - Number(usd.cash || 0));
  $("#usdValue").textContent = money(usd.market_value || 0, "USD");
  const usdCashBadgeEl = $("#usdCashBadge");
  if (usdCashBadgeEl) {
    usdCashBadgeEl.textContent = `(예수금 ${money(usd.cash || 0, "USD")})`;
  }
  $("#usdCaption").textContent = `주식 평가 ${money(usdStock, "USD")} (환산 ${money(usd.market_value_krw || 0)})`;

  // 6. 메타 정보
  $("#updatedAt").textContent = data.updated_at ? `마지막 자산 반영 ${new Date(data.updated_at).toLocaleString("ko-KR")}` : "아직 보유종목이 없습니다.";
  const cashSuffix = s.total_cash_krw ? ` (예수금 ${money(s.total_cash_krw)} 포함)` : "";
  $("#accountCaption").textContent = `전체 ${number(s.account_count, 0)}개 계좌 통합${cashSuffix}`;
  $("#accountCount").textContent = `${number(s.account_count, 0)}개 계좌`;
}

function renderClassifications(items) {
  const list = $("#classificationList");
  list.innerHTML = items.length ? items.map((item) => `<div class="classification-row"><div class="classification-title"><strong>${html(item.name)}</strong><span>${number(item.holding_count, 0)}종목 · ${number(item.weight)}%</span></div><div class="classification-value"><span>${money(item.market_value_krw)}</span><b class="${signClass(item.profit_krw)}">${item.return_rate >= 0 ? "+" : ""}${number(item.return_rate)}%</b></div><div class="bar"><i style="width:${Math.min(item.weight, 100)}%"></i></div></div>`).join("") : '<div class="empty">자산을 불러오면 분류별 수익률을 표시합니다.</div>';
}

function renderAccounts(items) {
  if (!items.length) { $("#accountList").innerHTML = '<div class="empty">동기화된 계좌가 없습니다.</div>'; return; }
  const groups = new Map();
  items.forEach((item) => {
    const group = groups.get(item.broker) || {
      broker: item.broker,
      accounts: [],
      market_value_krw: 0,
      stock_value_krw: 0,
      cash_krw: 0,
      cash_usd: 0,
      cash_total_krw: 0,
      profit_krw: 0,
      holding_count: 0,
    };
    group.accounts.push(item);
    group.market_value_krw += Number(item.market_value_krw || 0);
    group.stock_value_krw += Number(item.stock_value_krw || 0);
    group.cash_krw += Number(item.cash_krw || 0);
    group.cash_usd += Number(item.cash_usd || 0);
    group.cash_total_krw += Number(item.cash_total_krw || 0);
    group.profit_krw += Number(item.profit_krw || 0);
    group.holding_count += Number(item.holding_count || 0);
    groups.set(item.broker, group);
  });

  $("#accountList").innerHTML = [...groups.values()].map((group) => {
    const cashBadges = [];
    if (group.cash_krw) cashBadges.push(`원화 예수금 ${money(group.cash_krw)}`);
    if (group.cash_usd) cashBadges.push(`달러 예수금 ${money(group.cash_usd, "USD")}`);
    const groupCashTag = cashBadges.length ? `<small class="account-group-cash">${cashBadges.join(" · ")}</small>` : "";

    return `<div class="account-group">
      <div class="account-group-title">
        <div>
          <span>${html(group.broker)} <small>${number(group.holding_count, 0)}종목</small></span>
          ${groupCashTag}
        </div>
        <span>${money(group.market_value_krw)}</span>
      </div>
      ${group.accounts.map((item) => {
        const subNotes = [];
        if (item.holding_count > 0) subNotes.push(`${number(item.holding_count, 0)}종목 (${money(item.stock_value_krw || 0)})`);
        if (item.cash_krw) subNotes.push(`예수금 ${money(item.cash_krw)}`);
        if (item.cash_usd) subNotes.push(`예수금 ${money(item.cash_usd, "USD")}`);
        const subText = subNotes.join(" · ") || `${number(item.holding_count, 0)}종목`;

        return `<div class="account-subrow">
          <div class="account-subrow-info">
            <span class="account-name">${html(item.name)}</span>
            <small class="account-subrow-detail">${html(subText)}</small>
          </div>
          <strong>${money(item.market_value_krw)}</strong>
          <div class="account-actions">
            <button class="icon-button account-cash-button" data-account-id="${item.id}" title="예수금 직접 입력/수정 (원화·달러)" type="button">💵</button>
            <button class="icon-button account-edit-button" data-account-id="${item.id}" title="증권사 및 계좌 이름 수정" type="button">✎</button>
            <button class="icon-button account-delete-button" data-account-id="${item.id}" title="계좌 삭제" type="button">×</button>
          </div>
        </div>`;
      }).join("")}
    </div>`;
  }).join("");
}

// =========================================================================
// Squarified Treemap 알고리즘 및 히트맵 렌더링
// =========================================================================

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

let heatmapPeriod = localStorage.getItem("heatmap_period") || "1D";
let heatmapTheme = localStorage.getItem("heatmap_theme") || "kr";
let heatmapMaxCap = localStorage.getItem("heatmap_max_cap") || "auto";

const PERIOD_LABELS = {
  "1D": "일간 (전일 대비)",
  "1W": "주간 (1주 전 대비)",
  "1M": "월간 (1개월 전 대비)",
  "YTD": "연초부터 (올해 초 대비)",
  "1Y": "연간 (1년 전 대비)",
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

function getEffectiveCap(period, capSetting) {
  if (capSetting && capSetting !== "auto" && !isNaN(Number(capSetting)) && Number(capSetting) > 0) {
    return Number(capSetting);
  }
  return PERIOD_CAPS[period] || 15;
}

function getHeatmapColor(rate, maxRate = 15, theme = "kr") {
  const clamped = Math.max(-maxRate, Math.min(maxRate, rate));
  const t = Math.pow(Math.abs(clamped) / maxRate, 0.72);

  if (theme === "us") {
    // 글로벌/미국형: 상승=초록, 하락=빨강
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
    // 네온/모던형: 상승=바이올렛, 하락=사이언
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
    // 한국형 (기본): 상승=빨강, 하락=파랑
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

function updateHeatmapLegendUI(period, theme, maxCap) {
  const cap = getEffectiveCap(period, maxCap);
  const legLeft = $("#legendCapLeft");
  const legRight = $("#legendCapRight");
  const legBar = $("#legendBar");
  const legText = $("#legendText");
  const tipNote = $("#heatmapTipNote");

  if (legLeft) legLeft.textContent = `-${cap}%`;
  if (legRight) legRight.textContent = `+${cap}%`;
  if (legBar) {
    legBar.className = `legend-bar theme-${theme}`;
  }
  if (legText) {
    if (theme === "us") {
      legText.textContent = "하락(Red) ← 0 → 상승(Green)";
    } else if (theme === "neon") {
      legText.textContent = "하락(Cyan) ← 0 → 상승(Violet)";
    } else {
      legText.textContent = "하락(Blue) ← 0 → 상승(Red)";
    }
  }
  if (tipNote) {
    tipNote.textContent = `면적 = 포지션 규모 · 색 = ${PERIOD_LABELS[period] || period} 손익률 (범위 ±${cap}%) · 클릭하면 종목 검색`;
  }
}

function renderTreemapContainer(container, items, period = "1D", theme = "kr", capSetting = "auto") {
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="empty">평가금액이 있는 보유종목이 없습니다.</div>';
    return;
  }

  const maxCap = getEffectiveCap(period, capSetting);
  const totalVal = items.reduce((s, it) => s + it.value, 0);
  items.forEach((it) => {
    it.weight = totalVal > 0 ? (it.value / totalVal) * 100 : 0;
  });

  const width = container.clientWidth || 920;
  const height = Math.max(360, Math.min(520, Math.round(width * 0.44)));
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

    const infoStr = JSON.stringify({
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
    }).replace(/"/g, "&quot;");

    return `<div class="heatmap-tile" data-symbol="${html(tile.name)}" data-info="${infoStr}" style="left:${tile.x}px;top:${tile.y}px;width:${tile.w}px;height:${tile.h}px;background-color:${color};"><div class="heatmap-tile-inner">${inner}</div></div>`;
  }).join("");

  updateHeatmapLegendUI(period, theme, capSetting);
}

function renderHeatmaps(data) {
  const holdings = data.holdings || [];
  const assetContainer = $("#assetHeatmapContainer");

  if (!holdings.length) {
    if (assetContainer) assetContainer.innerHTML = '<div class="empty">보유종목이 없습니다. 증권사 동기화 후 히트맵이 표시됩니다.</div>';
    return;
  }

  // 종목별 통합 집계
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
      day_change_rate: 0,
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
    } else if (group.day_change_rate === 0 && item.day_change_rate != null) {
      group.day_change_rate = Number(item.day_change_rate);
    }
    if (item.period_changes) {
      group.period_changes = item.period_changes;
    }
    groups.set(key, group);
  });

  const items = [...groups.values()]
    .filter((it) => it.market_value_krw > 0)
    .map((it) => {
      const rate = it.cost_value_krw ? (it.profit_krw / it.cost_value_krw) * 100 : 0;
      return {
        ...it,
        value: it.market_value_krw,
        rate: rate,
      };
    });

  // 활성 히트맵 렌더링
  if (assetContainer) {
    renderTreemapContainer(assetContainer, items, heatmapPeriod, heatmapTheme, heatmapMaxCap);
  }
}

function renderHoldings(data) {
  const query = $("#searchInput").value.trim().toLowerCase();
  const rows = data.holdings.filter((item) => [item.name, item.code, item.broker, item.account_name].join(" ").toLowerCase().includes(query));
  const groups = new Map();
  rows.forEach((item) => {
    const key = `${item.code}|${item.currency}|${item.name}`;
    const group = groups.get(key) || {
      ...item,
      quantity: 0,
      market_value_krw: 0,
      cost_value_krw: 0,
      profit_krw: 0,
      day_change_rate: 0,
      items: [],
    };
    group.quantity += Number(item.quantity || 0);
    group.market_value_krw += Number(item.market_value_krw || 0);
    group.cost_value_krw += Number(item.cost_value_krw || 0);
    group.profit_krw += Number(item.profit_krw || 0);
    if (item.day_change_rate != null && Number(item.day_change_rate) !== 0) {
      group.day_change_rate = Number(item.day_change_rate);
    } else if (group.day_change_rate === 0 && item.day_change_rate != null) {
      group.day_change_rate = Number(item.day_change_rate);
    }
    group.items.push(item);
    groups.set(key, group);
  });
  $("#holdingsBody").innerHTML = [...groups.values()].map((item) => {
    const rate = item.cost_value_krw ? (item.profit_krw / item.cost_value_krw) * 100 : 0;
    const dayRate = Number(item.day_change_rate || 0);
    const accounts = item.items.map((detail) => `<span class="holding-account-detail">${html(detail.broker)} ${html(detail.account_name)} ${number(detail.quantity, 4)}주 <button class="mini-edit-button edit-button" data-id="${detail.id}" title="수정" type="button">✎</button><button class="mini-edit-button delete-button" data-id="${detail.id}" title="삭제" type="button">×</button></span>`).join("");
    return `<tr>
      <td><strong>${html(item.name)}</strong><small>${html(item.code)} · ${html(item.market || item.currency)}</small></td>
      <td>${html(item.currency === "KRW" ? "국내 자산" : "해외 자산")}</td>
      <td class="holding-accounts">${accounts}</td>
      <td>${number(item.quantity, 4)}</td>
      <td>${money(item.market_value_krw)}</td>
      <td class="${signClass(item.profit_krw)}">${item.profit_krw >= 0 ? "+" : ""}${money(item.profit_krw)}</td>
      <td class="${signClass(rate)}">${rate >= 0 ? "+" : ""}${number(rate)}%</td>
      <td class="${signClass(dayRate)}">${dayRate >= 0 ? "+" : ""}${number(dayRate)}%</td>
      <td></td>
    </tr>`;
  }).join("");
  $("#emptyHoldings").hidden = data.holdings.length > 0;
  $(".table-wrap").hidden = data.holdings.length === 0;
}

function render(data) {
  dashboard = data;
  // rawDashboard is set only by loadDashboard (not by filtered renders)
  renderSummary(data);
  renderClassifications(data.classifications || []);
  renderAccounts(data.accounts);
  renderHeatmaps(data);
  renderHoldings(data);
}

async function loadDashboard() { const data = await api("/api/dashboard"); rawDashboard = data; dashboard = data; renderWithOwner(data, currentOwner); }
async function loadAssetRecords(owner) {
  // 항상 owner로 필터링 ("모두"도 owner=모두 레코드만 표시)
  const o = owner || currentOwner || '모두';
  renderAssetRecords((await api(`/api/asset-records?owner=${encodeURIComponent(o)}`)).records || []);
}

function openImport() { $("#importDialog").showModal(); }
function openHoldingDialog(record = null) {
  const form = $("#holdingForm"); form.reset(); form.dataset.recordId = record ? String(record.id) : "";
  form.broker.value = record?.broker || "기타 증권사"; form.account_name.value = record?.account_name || "내 주식 계좌";
  form.code.value = record?.code || ""; form.name.value = record?.name || ""; form.quantity.value = record?.quantity ?? "";
  form.avg_price.value = record?.avg_price ?? ""; form.current_price.value = record?.current_price ?? "";
  form.currency.value = record?.currency || "KRW"; form.market.value = record?.market || "";
  if (form.owner) {
    // Try to find owner from linked account
    const linkedAcct = dashboard?.accounts?.find(a => a.id === record?.account_id);
    form.owner.value = linkedAcct?.owner || record?.owner || "모두";
  }
  $("#holdingDialog").showModal();
}
function openAssetRecordDialog(record = null) {
  const form = $("#assetRecordForm");
  form.reset();
  form.dataset.recordId = record?.id || "";
  $("#assetRecordDialogTitle").textContent = record ? "자산기록 수정" : "자산기록 추가";
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
  // owner: 기존 레코드의 owner 또는 현재 선택된 구성원
  if (form.owner) form.owner.value = record?.owner || currentOwner || "모두";
  $("#assetRecordDialog").showModal();
}

function openAccountCashDialog(account) {
  const form = $("#accountCashForm");
  if (!form || !account) return;
  form.reset();
  form.dataset.accountId = account.id;
  $("#accountCashDialogTitle").textContent = `[${account.broker} · ${account.name}] 예수금 입력 / 수정`;
  form.cash_krw.value = account.cash_krw || "";
  form.cash_usd.value = account.cash_usd || "";
  $("#accountCashDialog").showModal();
}

function openAccountEditDialog(account) {
  const form = $("#accountEditForm");
  if (!form || !account) return;
  form.reset();
  form.dataset.accountId = account.id;
  form.broker.value = account.broker || "";
  form.name.value = account.name || "";
  if (form.owner) form.owner.value = account.owner || "모두";
  $("#accountEditDialog").showModal();
}

$("#syncKbButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/sync/kb", { method: "POST" })));
$("#syncTossButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/sync/toss", { method: "POST" })));
$("#syncNamooButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/sync/namoo", { method: "POST" })));
$("#refreshButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" })));
$("#refreshFxButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/fx/refresh", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));
$("#refreshMarketButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/market-overview"), async () => { await loadMarkets(); }));
$("#demoButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/demo", { method: "POST" })));
$("#addButton").addEventListener("click", () => openHoldingDialog()); $("#importButton").addEventListener("click", openImport);
$("#addRecordButton").addEventListener("click", () => openAssetRecordDialog());
$("#snapshotButton").addEventListener("click", (e) => action(e.currentTarget, async () => {
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
}, async () => { await loadDashboard(); await loadAssetRecords(currentOwner); }));

$("#searchInput").addEventListener("input", () => dashboard && renderHoldings(dashboard));
$("#clearButton").addEventListener("click", () => { if (confirm("저장된 보유내역을 모두 지울까요?")) action($("#clearButton"), () => api("/api/clear", { method: "POST" })); });
$("#holdingsBody").addEventListener("click", (e) => { const edit = e.target.closest(".edit-button"); const button = e.target.closest(".delete-button"); if (edit) { const item = dashboard?.holdings.find((row) => row.id === edit.dataset.id); if (item) openHoldingDialog(item); return; } if (button && confirm("이 보유종목을 삭제할까요?")) action(button, () => api(`/api/holdings/${button.dataset.id}`, { method: "DELETE" })); });


// ── 계좌 추가 버튼 ───────────────────────────────────────────────────────────
const _addAccountBtn = document.getElementById('addAccountBtn');
if (_addAccountBtn) {
  _addAccountBtn.addEventListener('click', () => {
    const dlg = document.getElementById('accountAddDialog');
    if (dlg) {
      document.getElementById('accountAddForm')?.reset();
      dlg.showModal();
    }
  });
}

document.getElementById('accountAddForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const payload = {
    broker: form.broker.value.trim(),
    account_name: form.account_name.value.trim(),
    owner: form.owner.value,
  };
  try {
    const result = await api('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    form.closest('dialog')?.close();
    toast(result.message || '계좌가 추가되었습니다.');
    await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  }
});

// 히트맵 툴팁 및 클릭 필터 상호작용
const tooltip = $("#heatmapTooltip");

function bindHeatmapInteractions(container) {
  if (!container || !tooltip) return;
  container.addEventListener("mousemove", (e) => {
    const tile = e.target.closest(".heatmap-tile");
    if (!tile || !tile.dataset.info) {
      tooltip.style.display = "none";
      return;
    }
        try {
      const info = JSON.parse(tile.dataset.info);
      const period = info.period || heatmapPeriod || "1D";
      const selRate = Number(info.selected_rate != null ? info.selected_rate : (period === "TOTAL" ? info.rate : (info.period_changes?.[period] || info.day_change_rate || 0)));
      const sign = selRate >= 0 ? "+" : "";
      const rateClass = selRate >= 0 ? "up" : "down";
      const periodLabel = PERIOD_LABELS[period] || period;

      tooltip.innerHTML = `
        <div class="heatmap-tooltip-title">
          <strong>${html(info.name)}</strong>
          <span>${html(info.code)} · ${html(info.market)}</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">포지션 규모:</span>
          <span class="val">${money(info.value)} (${number(info.weight, 1)}%)</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">${periodLabel}:</span>
          <span class="val ${rateClass}">${sign}${number(selRate, 2)}%</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">누적 수익률:</span>
          <span class="val ${info.rate >= 0 ? "up" : "down"}">${info.rate >= 0 ? "+" : ""}${number(info.rate, 2)}% (${money(info.profit)})</span>
        </div>
      `;
      tooltip.style.display = "block";
      const tx = Math.min(window.innerWidth - 140, Math.max(120, e.clientX));
      const ty = Math.max(40, e.clientY);
      tooltip.style.left = `${tx}px`;
      tooltip.style.top = `${ty}px`;
    } catch {
      tooltip.style.display = "none";
    }
  });

  container.addEventListener("mouseleave", () => {
    tooltip.style.display = "none";
  });

  container.addEventListener("click", (e) => {
    const tile = e.target.closest(".heatmap-tile");
    if (!tile || !tile.dataset.symbol) return;
    const searchInput = $("#searchInput");
    if (searchInput) {
      searchInput.value = tile.dataset.symbol;
      if (dashboard) renderHoldings(dashboard);
      const panel = $("#holdingsPanel");
      if (panel) panel.scrollIntoView({ behavior: "smooth" });
    }
  });
}

bindHeatmapInteractions($("#assetHeatmapContainer"));

// 윈도우 리사이즈 시 히트맵 반응형 재계산
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (dashboard) renderHeatmaps(dashboard);
  }, 150);
});

$("#accountList").addEventListener("click", async (e) => {
  const cashBtn = e.target.closest(".account-cash-button");
  if (cashBtn) {
    const acc = dashboard?.accounts.find((a) => a.id === cashBtn.dataset.accountId);
    if (acc) openAccountCashDialog(acc);
    return;
  }

  const editBtn = e.target.closest(".account-edit-button");
  if (editBtn) {
    const acc = dashboard?.accounts.find((item) => item.id === editBtn.dataset.accountId);
    if (acc) openAccountEditDialog(acc);
    return;
  }

  const delBtn = e.target.closest(".account-delete-button");
  if (delBtn && confirm("이 계좌와 연결된 보유종목을 모두 삭제할까요?")) {
    await action(delBtn, () => api(`/api/accounts/${delBtn.dataset.accountId}`, { method: "DELETE" }));
  }
});

$("#accountCashForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const id = form.dataset.accountId;
  if (!id) return;
  const payload = {
    cash_krw: Number(form.cash_krw.value) || 0,
    cash_usd: Number(form.cash_usd.value) || 0,
  };
  try {
    const result = await api(`/api/accounts/${id}/cash`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    form.closest("dialog")?.close();
    toast(result.message);
    await loadDashboard();
  } catch (error) {
    toast(error.message, true);
  }
});

$("#accountEditForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const id = form.dataset.accountId;
  if (!id) return;
  const payload = {
    broker: form.broker.value.trim(),
    name: form.name.value.trim(),
    owner: form.owner ? form.owner.value : "모두",
  };
  try {
    const result = await api(`/api/accounts/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    form.closest("dialog")?.close();
    toast(result.message);
    await loadDashboard();
  } catch (error) {
    toast(error.message, true);
  }
});

$("#assetRecordList").addEventListener("click", async (e) => {
  const editButton = e.target.closest("[data-record-edit]");
  const deleteButton = e.target.closest("[data-record-delete]");
  if (editButton) {
    const record = assetRecords.find((item) => item.id === editButton.dataset.recordEdit);
    if (record) openAssetRecordDialog(record);
  }
  if (deleteButton && confirm("이 자산기록을 삭제할까요?")) {
    await action(deleteButton, () => api(`/api/asset-records/${deleteButton.dataset.recordDelete}`, { method: "DELETE" }), loadAssetRecords);
  }
});

$("#holdingForm").addEventListener("submit", async (e) => { e.preventDefault(); const form = e.currentTarget, payload = Object.fromEntries(new FormData(form)); if (!payload.owner) payload.owner = "모두"; ["quantity", "avg_price", "current_price"].forEach((key) => { payload[key] = Number(payload[key]); }); try { const id = form.dataset.recordId; const result = await api(id ? `/api/holdings/${id}` : "/api/holdings", { method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); form.closest("dialog").close(); toast(result.message); await loadDashboard(); } catch (error) { toast(error.message, true); } });
$("#importForm").addEventListener("submit", async (e) => { e.preventDefault(); const form = e.currentTarget; const file = $("#importFile").files[0]; if (!file) return; const formData = new FormData(); formData.append("file", file); try { const result = await api(`/api/import?broker=${encodeURIComponent($("#importBroker").value || "기타 증권사")}`, { method: "POST", body: formData }); form.closest("dialog")?.close(); toast(result.message); await loadDashboard(); } catch (error) { toast(error.message, true); } });
$("#assetRecordForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  ["total_value_krw", "total_cost_krw", "profit_krw", "return_rate", "day_profit_krw", "krw_value_krw", "usd_value_krw", "holding_count"].forEach((key) => {
    payload[key] = Number(payload[key] || 0);
  });
  payload.memo = payload.memo || "";
  payload.owner = payload.owner || currentOwner || "모두";
  try {
    const method = form.dataset.recordId ? "PUT" : "POST";
    const url = form.dataset.recordId ? `/api/asset-records/${form.dataset.recordId}` : "/api/asset-records";
    const result = await api(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    form.closest("dialog").close();
    toast(result.message);
    await loadAssetRecords(currentOwner);
  } catch (error) {
    toast(error.message, true);
  }
});
async function bootstrap() { await loadFamilyMembers(); await loadDashboard().catch((error) => toast(error.message, true)); await loadMarkets(); await loadAssetRecords('모두'); }
bootstrap();


// 히트맵 기간 탭 클릭 이벤트 바인딩
const periodTabsWrap = document.getElementById("heatmapPeriodTabs");
if (periodTabsWrap) {
  // 초기 활성 탭 표시
  periodTabsWrap.querySelectorAll(".heatmap-tab").forEach((tab) => {
    if (tab.dataset.period === heatmapPeriod) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });

  periodTabsWrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".heatmap-tab");
    if (!btn || !btn.dataset.period) return;
    periodTabsWrap.querySelectorAll(".heatmap-tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    heatmapPeriod = btn.dataset.period;
    localStorage.setItem("heatmap_period", heatmapPeriod);
    if (dashboard) renderHeatmaps(dashboard);
  });
}

// 히트맵 색상 테마 선택 이벤트 바인딩
const themeSelectElem = document.getElementById("heatmapThemeSelect");
if (themeSelectElem) {
  themeSelectElem.value = heatmapTheme;
  themeSelectElem.addEventListener("change", (e) => {
    heatmapTheme = e.target.value || "kr";
    localStorage.setItem("heatmap_theme", heatmapTheme);
    if (dashboard) renderHeatmaps(dashboard);
  });
}

// 히트맵 최대 등락률 범위(Max Cap) 선택 이벤트 바인딩
const capSelectElem = document.getElementById("heatmapCapSelect");
if (capSelectElem) {
  capSelectElem.value = heatmapMaxCap;
  capSelectElem.addEventListener("change", (e) => {
    heatmapMaxCap = e.target.value || "auto";
    localStorage.setItem("heatmap_max_cap", heatmapMaxCap);
    if (dashboard) renderHeatmaps(dashboard);
  });
}



// ── 가족 구성원 탭 동적 렌더링 ────────────────────────────────────────────────
async function loadFamilyMembers() {
  try {
    const res = await api('/api/family-members');
    renderFamilyTabs(res.members || []);
    updateOwnerSelects(res.members || []);
  } catch (e) {
    renderFamilyTabs(['아빠', '엄마', '자녀']);
    updateOwnerSelects(['아빠', '엄마', '자녀']);
  }
}

// 다이얼로그 내 owner <select>들을 현재 구성원 목록으로 동기화
function updateOwnerSelects(members) {
  const opts = ['<option value="모두">모두</option>']
    .concat(members.map(m => `<option value="${m}">${m}</option>`))
    .join('');
  document.querySelectorAll('select[name="owner"]').forEach(sel => {
    const prev = sel.value;
    sel.innerHTML = opts;
    if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
  });
}

function renderFamilyTabs(members) {
  const allBtn = (containerId) => '<button type="button" class="family-tab' + (currentOwner === '모두' ? ' active' : '') + '" data-owner="모두">모두</button>';
  const memberBtns = members.map(m =>
    '<button type="button" class="family-tab' + (currentOwner === m ? ' active' : '') + '" data-owner="' + m + '">' + m + '</button>'
  ).join('');
  const inner = allBtn() + memberBtns;
  // ACCOUNTS 탭
  const container = document.getElementById('familyTabs');
  if (container) container.innerHTML = inner;
  // 탑바 탭
  const topbar = document.getElementById('topbarFamilyTabs');
  if (topbar) topbar.innerHTML = inner;
}

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

// ── 가족 구성원 관리 – 이벤트 위임으로 구현 (dialog 내부 버튼 안전하게 처리) ──
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

document.addEventListener('click', async (e) => {
  // 관리 버튼 열기
  if (e.target.closest('#manageFamilyBtn')) {
    await openFamilyManager();
    return;
  }

  // 추가 버튼
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
      updateOwnerSelects(res.members || []);
      renderFamilyMemberList(res.members || []);
    } catch(err) { toast(err.message, true); }
    return;
  }

  // 이름 변경 버튼
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
      toast(res.message || '이름을 변경했습니다.');
      if (currentOwner === oldName) currentOwner = newName;
      renderFamilyTabs(res.members || []);
      renderFamilyMemberList(res.members || []);
      await loadDashboard();
    } catch(err) { toast(err.message, true); }
    return;
  }

  // 삭제 버튼
  const deleteBtn = e.target.closest('.family-delete-btn');
  if (deleteBtn) {
    const name = deleteBtn.dataset.name;
    if (!confirm(`'${name}' 구성원을 삭제할까요?`)) return;
    try {
      const res = await api(`/api/family-members/${encodeURIComponent(name)}`, { method: 'DELETE' });
      toast(res.message || '삭제했습니다.');
      if (currentOwner === name) currentOwner = '모두';
      renderFamilyTabs(res.members || []);
      renderFamilyMemberList(res.members || []);
      await loadDashboard();
    } catch(err) { toast(err.message, true); }
    return;
  }
});

// Enter 키로 구성원 추가
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && document.activeElement?.id === 'newMemberName') {
    document.getElementById('addMemberBtn')?.click();
  }
});


// ── 데이터 저장 / 불러오기 ───────────────────────────────────────────────────
document.getElementById('exportButton')?.addEventListener('click', async () => {
  try {
    const response = await fetch('/api/export', { credentials: 'include' });
    if (response.status === 401) {
      toast('로그인 세션이 만료됐습니다. 페이지를 새로고침 후 다시 시도해주세요.', true);
      return;
    }
    if (!response.ok) throw new Error(`서버 오류: ${response.status}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const ts = new Date().toISOString().slice(0,19).replace(/[-:T]/g,'').slice(0,14);
    a.download = `dashboard_backup_${ts}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('데이터를 저장했습니다.');
  } catch (err) {
    toast(err.message || '저장 실패', true);
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

// PWA 서비스 워커 등록 (주소창 없는 독립형 앱 실행 지원)
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}
