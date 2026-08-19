const $ = (selector) => document.querySelector(selector);
let dashboard = null;

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
  if (!points || points.length < 2) return "<span class=\"spark-empty\">—</span>";
  const min = Math.min(...points), max = Math.max(...points), span = max - min || 1;
  const coords = points.map((point, index) => `${(index / (points.length - 1)) * 100},${34 - ((point - min) / span) * 28}`).join(" ");
  const color = Number(change) < 0 ? "#4f9dff" : "#ff5c77";
  return `<svg class="sparkline" viewBox="0 0 100 38" preserveAspectRatio="none" aria-hidden="true"><polyline points="${coords}" fill="none" stroke="${color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="0,37 ${coords} 100,37" fill="${color}18" stroke="none"/></svg>`;
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
        <b>${money(item.day_profit_krw || 0)}</b>
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
  const rows = [...result.markets, {
    symbol: "USD/KRW", label: "달러/원", note: "토스 실시간 환율", price: result.exchange_rate.rate,
    currency: "KRW", change: result.exchange_rate.change, change_rate: result.exchange_rate.change_rate, note: "토스 1일 변동", updated_at: result.exchange_rate.valid_until, series: result.exchange_rate.series || [result.exchange_rate.rate],
  }];
  $("#marketGrid").innerHTML = rows.map((item) => {
    const currency = item.symbol === "KOSPI" || item.symbol === "USD/KRW" ? null : item.currency;
    const price = currency ? money(item.price, currency) : number(item.price);
    const change = item.change_rate == null ? "실시간 기준가" : item.change != null ? `${item.change >= 0 ? "+" : ""}${number(item.change, 1)} (${item.change_rate >= 0 ? "+" : ""}${number(item.change_rate)}%)` : `${item.change_rate >= 0 ? "+" : ""}${number(item.change_rate)}%`;
    const chart = item.symbol === "USD/KRW" ? "" : `<div class="spark-wrap">${sparkline(item.series, item.change_rate)}</div>`;
    return `<article class="market-card"><div class="market-copy"><span class="symbol">${html(item.symbol)}</span><p>${html(item.label)}</p><strong>${price}</strong><small class="${item.change_rate == null ? "" : signClass(item.change_rate)}">${change} · ${html(item.note)}</small></div>${chart}</article>`;
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

function getHeatmapColor(rate, maxRate = 20) {
  const clamped = Math.max(-maxRate, Math.min(maxRate, rate));
  const t = Math.abs(clamped) / maxRate;

  if (clamped >= 0) {
    // 상승/이익: 붉은색 그라데이션
    const r = Math.round(52 + (225 - 52) * Math.pow(t, 0.75));
    const g = Math.round(65 + (48 - 65) * t);
    const b = Math.round(92 + (68 - 92) * t);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    // 하락/손실: 푸른색 그라데이션
    const r = Math.round(52 + (32 - 52) * t);
    const g = Math.round(65 + (118 - 65) * t);
    const b = Math.round(92 + (245 - 92) * Math.pow(t, 0.75));
    return `rgb(${r}, ${g}, ${b})`;
  }
}

function renderTreemapContainer(container, items, mode = "cumulative") {
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="empty">평가금액이 있는 보유종목이 없습니다.</div>';
    return;
  }

  const isDaily = mode === "daily";
  const maxCap = isDaily ? 10 : 20;

  const totalVal = items.reduce((s, it) => s + it.value, 0);
  items.forEach((it) => {
    it.weight = totalVal > 0 ? (it.value / totalVal) * 100 : 0;
  });

  const width = container.clientWidth || 920;
  const height = Math.max(360, Math.min(500, Math.round(width * 0.44)));
  container.style.height = `${height}px`;

  const tiles = squarify(items, 0, 0, width, height);

  container.innerHTML = tiles.map((tile) => {
    const rateVal = isDaily ? Number(tile.day_change_rate || 0) : Number(tile.rate || 0);
    const color = getHeatmapColor(rateVal, maxCap);
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
      mode,
      name: tile.name,
      code: tile.code,
      market: tile.market || tile.currency,
      value: tile.market_value_krw,
      cost: tile.cost_value_krw,
      profit: tile.profit_krw,
      rate: tile.rate,
      day_change_rate: tile.day_change_rate || 0,
      weight: tile.weight,
    }).replace(/"/g, "&quot;");

    return `<div class="heatmap-tile" data-symbol="${html(tile.name)}" data-info="${infoStr}" style="left:${tile.x}px;top:${tile.y}px;width:${tile.w}px;height:${tile.h}px;background-color:${color};"><div class="heatmap-tile-inner">${inner}</div></div>`;
  }).join("");
}

function renderHeatmaps(data) {
  const holdings = data.holdings || [];
  const assetContainer = $("#assetHeatmapContainer");
  const dailyContainer = $("#dailyHeatmapContainer");

  if (!holdings.length) {
    if (assetContainer) assetContainer.innerHTML = '<div class="empty">보유종목이 없습니다. 증권사 동기화 후 히트맵이 표시됩니다.</div>';
    if (dailyContainer) dailyContainer.innerHTML = '<div class="empty">보유종목이 없습니다. 증권사 동기화 후 히트맵이 표시됩니다.</div>';
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
      day_change_rate: Number(item.day_change_rate || 0),
    };
    group.quantity += Number(item.quantity || 0);
    group.market_value_krw += Number(item.market_value_krw || 0);
    group.cost_value_krw += Number(item.cost_value_krw || 0);
    group.profit_krw += Number(item.profit_krw || 0);
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

  // 1. 자산 히트맵 (진입가 대비 누적 손익률)
  renderTreemapContainer(assetContainer, items, "cumulative");

  // 2. 히트맵 (전날 대비 일간 등락)
  renderTreemapContainer(dailyContainer, items, "daily");
}

function renderHoldings(data) {
  const query = $("#searchInput").value.trim().toLowerCase();
  const rows = data.holdings.filter((item) => [item.name, item.code, item.broker, item.account_name].join(" ").toLowerCase().includes(query));
  const groups = new Map();
  rows.forEach((item) => {
    const key = `${item.code}|${item.currency}|${item.name}`;
    const group = groups.get(key) || { ...item, quantity: 0, market_value_krw: 0, cost_value_krw: 0, profit_krw: 0, items: [] };
    group.quantity += Number(item.quantity || 0); group.market_value_krw += Number(item.market_value_krw || 0);
    group.cost_value_krw += Number(item.cost_value_krw || 0); group.profit_krw += Number(item.profit_krw || 0); group.items.push(item); groups.set(key, group);
  });
  $("#holdingsBody").innerHTML = [...groups.values()].map((item) => {
    const rate = item.cost_value_krw ? item.profit_krw / item.cost_value_krw * 100 : 0;
    const accounts = item.items.map((detail) => `<span class="holding-account-detail">${html(detail.broker)} ${html(detail.account_name)} ${number(detail.quantity, 4)}주 <button class="mini-edit-button edit-button" data-id="${detail.id}" title="수정" type="button">✎</button><button class="mini-edit-button delete-button" data-id="${detail.id}" title="삭제" type="button">×</button></span>`).join("");
    return `<tr><td><strong>${html(item.name)}</strong><small>${html(item.code)} · ${html(item.market || item.currency)}</small></td><td>${html(item.currency === "KRW" ? "국내 자산" : "해외 자산")}</td><td class="holding-accounts">${accounts}</td><td>${number(item.quantity, 4)}</td><td>${money(item.market_value_krw)}</td><td class="${signClass(item.profit_krw)}">${item.profit_krw >= 0 ? "+" : ""}${money(item.profit_krw)}</td><td class="${signClass(rate)}">${rate >= 0 ? "+" : ""}${number(rate)}%</td><td></td></tr>`;
  }).join("");
  $("#emptyHoldings").hidden = data.holdings.length > 0; $(".table-wrap").hidden = data.holdings.length === 0;
}

function render(data) {
  dashboard = data;
  renderSummary(data);
  renderClassifications(data.classifications || []);
  renderAccounts(data.accounts);
  renderHeatmaps(data);
  renderHoldings(data);
}

async function loadDashboard() { render(await api("/api/dashboard")); }
async function loadAssetRecords() { renderAssetRecords((await api("/api/asset-records")).records || []); }

function openImport() { $("#importDialog").showModal(); }
function openHoldingDialog(record = null) {
  const form = $("#holdingForm"); form.reset(); form.dataset.recordId = record ? String(record.id) : "";
  form.broker.value = record?.broker || "기타 증권사"; form.account_name.value = record?.account_name || "내 주식 계좌";
  form.code.value = record?.code || ""; form.name.value = record?.name || ""; form.quantity.value = record?.quantity ?? "";
  form.avg_price.value = record?.avg_price ?? ""; form.current_price.value = record?.current_price ?? "";
  form.currency.value = record?.currency || "KRW"; form.market.value = record?.market || "";
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
      holding_count: s.holding_count, source: "snapshot", memo: "수동 스냅샷"
    }) });
  }
}, async () => { await loadDashboard(); await loadAssetRecords(); }));

$("#searchInput").addEventListener("input", () => dashboard && renderHoldings(dashboard));
$("#clearButton").addEventListener("click", () => { if (confirm("저장된 보유내역을 모두 지울까요?")) action($("#clearButton"), () => api("/api/clear", { method: "POST" })); });
$("#holdingsBody").addEventListener("click", (e) => { const edit = e.target.closest(".edit-button"); const button = e.target.closest(".delete-button"); if (edit) { const item = dashboard?.holdings.find((row) => row.id === edit.dataset.id); if (item) openHoldingDialog(item); return; } if (button && confirm("이 보유종목을 삭제할까요?")) action(button, () => api(`/api/holdings/${button.dataset.id}`, { method: "DELETE" })); });

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
      const isDaily = info.mode === "daily";
      const rateVal = isDaily ? Number(info.day_change_rate || 0) : Number(info.rate || 0);
      const sign = rateVal >= 0 ? "+" : "";
      const rateClass = rateVal >= 0 ? "up" : "down";

      const subRow = isDaily ? `
        <div class="heatmap-tooltip-row">
          <span class="label">전날 대비 등락:</span>
          <span class="val ${rateClass}">${sign}${number(rateVal, 2)}%</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">누적 수익률:</span>
          <span class="val ${info.rate >= 0 ? "up" : "down"}">${info.rate >= 0 ? "+" : ""}${number(info.rate, 2)}%</span>
        </div>
      ` : `
        <div class="heatmap-tooltip-row">
          <span class="label">손익금액:</span>
          <span class="val ${rateClass}">${sign}${money(info.profit)}</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">진입가 대비 손익률:</span>
          <span class="val ${rateClass}">${sign}${number(info.rate, 2)}%</span>
        </div>
      `;

      tooltip.innerHTML = `
        <div class="heatmap-tooltip-title">
          <strong>${html(info.name)}</strong>
          <span>${html(info.code)} · ${html(info.market)}</span>
        </div>
        <div class="heatmap-tooltip-row">
          <span class="label">포지션 규모:</span>
          <span class="val">${money(info.value)} (${number(info.weight, 1)}%)</span>
        </div>
        ${subRow}
      `;
      tooltip.style.display = "block";
      const tx = Math.min(window.innerWidth - 110, Math.max(110, e.clientX));
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
bindHeatmapInteractions($("#dailyHeatmapContainer"));

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

$("#holdingForm").addEventListener("submit", async (e) => { e.preventDefault(); const form = e.currentTarget, payload = Object.fromEntries(new FormData(form)); ["quantity", "avg_price", "current_price"].forEach((key) => { payload[key] = Number(payload[key]); }); try { const id = form.dataset.recordId; const result = await api(id ? `/api/holdings/${id}` : "/api/holdings", { method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); form.closest("dialog").close(); toast(result.message); await loadDashboard(); } catch (error) { toast(error.message, true); } });
$("#importForm").addEventListener("submit", async (e) => { e.preventDefault(); const form = e.currentTarget; const file = $("#importFile").files[0]; if (!file) return; const formData = new FormData(); formData.append("file", file); try { const result = await api(`/api/import?broker=${encodeURIComponent($("#importBroker").value || "기타 증권사")}`, { method: "POST", body: formData }); form.closest("dialog")?.close(); toast(result.message); await loadDashboard(); } catch (error) { toast(error.message, true); } });
$("#assetRecordForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  ["total_value_krw", "total_cost_krw", "profit_krw", "return_rate", "day_profit_krw", "krw_value_krw", "usd_value_krw", "holding_count"].forEach((key) => {
    payload[key] = Number(payload[key] || 0);
  });
  payload.memo = payload.memo || "";
  try {
    const method = form.dataset.recordId ? "PUT" : "POST";
    const url = form.dataset.recordId ? `/api/asset-records/${form.dataset.recordId}` : "/api/asset-records";
    const result = await api(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    form.closest("dialog").close();
    toast(result.message);
    await loadAssetRecords();
  } catch (error) {
    toast(error.message, true);
  }
});
async function bootstrap() { await loadDashboard().catch((error) => toast(error.message, true)); await loadMarkets(); await loadAssetRecords(); }
bootstrap();
