#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_wealth_js_features.py
- Fix renderMarkets field handling
- Add Sector Portfolio Tab support
- Add Sortable Holdings Table logic
- Add Stock Chart (Price & Volume) Modal rendering
- Add Asset Records Multi-Line Chart (Total / Cost / Profit) & Period Filtering
"""

JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

FEATURE_EXTENSIONS = '''
// =========================================================================
// 전역 상태 변수 (정렬, 섹터 탭, 종목 차트, 자산기록 기간)
// =========================================================================
let currentAllocTab = 'class'; // 'class' | 'sector'
let currentSortKey = 'market_value_krw';
let currentSortOrder = 'desc';
let currentStockChartCode = '';
let currentStockChartPeriod = '1M';
let currentRecordPeriod = 'ALL'; // '1M' | '3M' | '6M' | '1Y' | 'ALL'

// ── 1. 투자자산 분류 (자산군별 / 섹터별) 탭 전환 ────────────────────────────
function renderClassifications(items) {
  const isSector = currentAllocTab === 'sector';
  let targetItems = [];

  if (isSector) {
    targetItems = dashboard?.sector_classifications || [];
    if (!targetItems.length && dashboard?.holdings) {
      // 클라이언트 측 실시간 섹터 계산 fallback
      const secMap = {};
      const totalVal = Number(dashboard.summary?.total_value_krw || 0);
      (dashboard.holdings || []).forEach(h => {
        const sec = h.sector || '기타';
        const obj = secMap[sec] = secMap[sec] || { name: sec, market_value_krw: 0, cost_value_krw: 0, profit_krw: 0, holding_count: 0 };
        obj.market_value_krw += Number(h.market_value_krw || 0);
        obj.cost_value_krw += Number(h.cost_value_krw || 0);
        obj.profit_krw += Number(h.profit_krw || 0);
        obj.holding_count += 1;
      });
      const cashVal = Number(dashboard.summary?.total_cash_krw || 0);
      if (cashVal > 0) {
        secMap['현금·예수금'] = { name: '현금·예수금', market_value_krw: cashVal, cost_value_krw: cashVal, profit_krw: 0, holding_count: 0 };
      }
      targetItems = Object.values(secMap).map(s => ({
        ...s,
        return_rate: s.cost_value_krw ? (s.profit_krw / s.cost_value_krw) * 100 : 0,
        weight: totalVal ? (s.market_value_krw / totalVal) * 100 : 0,
      })).sort((a, b) => b.market_value_krw - a.market_value_krw);
    }
  } else {
    targetItems = items || [];
  }

  const list = $("#classificationList");
  if (!targetItems.length) {
    list.innerHTML = `<div class="empty" style="padding:20px 0;">${isSector ? '섹터 정보가 없습니다.' : '분류 데이터가 없습니다.'}</div>`;
    return;
  }

  list.innerHTML = targetItems.map((item) => {
    const rate = Number(item.return_rate ?? item.rate ?? 0);
    const weight = Number(item.weight ?? 0);
    const countText = item.holding_count ? `${number(item.holding_count, 0)}종목` : '';
    const label = item.name || item.label || item.key || '기타';
    return `
      <div class="classification-row">
        <div class="classification-title">
          <strong>${html(label)}</strong>
          <span>${countText ? countText + ' · ' : ''}${number(weight, 1)}%</span>
        </div>
        <div class="classification-value">
          <span>${money(item.market_value_krw)}</span>
          <b class="${signClass(rate)}">${rate >= 0 ? "+" : ""}${number(rate)}%</b>
        </div>
        <div class="bar"><i style="width: ${Math.min(Math.max(weight, 0), 100)}%;"></i></div>
      </div>`;
  }).join("");
}

document.getElementById('allocTabs')?.addEventListener('click', (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab) return;
  document.querySelectorAll('#allocTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentAllocTab = tab.dataset.alloc || 'class';
  renderClassifications(dashboard?.classifications || []);
});


// ── 2. 보유종목 테이블 정렬 및 렌더링 ─────────────────────────────────────────
function sortHoldings(holdings) {
  if (!holdings || !holdings.length) return [];
  const list = [...holdings];
  const factor = currentSortOrder === 'asc' ? 1 : -1;

  list.sort((a, b) => {
    let valA = a[currentSortKey];
    let valB = b[currentSortKey];

    if (currentSortKey === 'name') {
      return factor * String(valA || '').localeCompare(String(valB || ''), 'ko');
    }
    if (currentSortKey === 'sector') {
      return factor * String(valA || '').localeCompare(String(valB || ''), 'ko');
    }
    if (currentSortKey === 'rate') {
      valA = Number(a.return_rate ?? (a.cost_value_krw ? (a.profit_krw / a.cost_value_krw * 100) : 0));
      valB = Number(b.return_rate ?? (b.cost_value_krw ? (b.profit_krw / b.cost_value_krw * 100) : 0));
    } else {
      valA = Number(valA || 0);
      valB = Number(valB || 0);
    }
    return factor * (valA - valB);
  });
  return list;
}

function updateSortIcons() {
  document.querySelectorAll('th[data-sort]').forEach(th => {
    const icon = th.querySelector('.sort-icon');
    if (!icon) return;
    if (th.dataset.sort === currentSortKey) {
      icon.textContent = currentSortOrder === 'asc' ? '▲' : '▼';
      th.classList.add('active-sort');
    } else {
      icon.textContent = '';
      th.classList.remove('active-sort');
    }
  });
}

document.addEventListener('click', (e) => {
  const th = e.target.closest('th[data-sort]');
  if (!th) return;
  const key = th.dataset.sort;
  if (currentSortKey === key) {
    currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
  } else {
    currentSortKey = key;
    currentSortOrder = 'desc';
  }
  updateSortIcons();
  if (dashboard) renderHoldings(dashboard);
});


// ── 3. 보유종목 행 렌더링 (섹터 뱃지 & 차트 버튼 & 클릭 차트 열기) ───────────
function renderHoldings(data) {
  const sorted = sortHoldings(data.holdings || []);
  const body = $("#holdingsBody");
  if (!body) return;

  body.innerHTML = sorted.map((item) => {
    const rate = item.return_rate ?? (item.cost_value_krw ? (item.profit_krw / item.cost_value_krw * 100) : 0);
    const dayRate = Number(item.day_change_rate || 0);
    const sec = item.sector || '기타';

    return `<tr class="holding-row" data-holding-id="${item.id}" data-code="${item.code}">
      <td class="holding-name-cell" style="cursor:pointer;" title="차트 보기">
        <div style="display:flex;align-items:center;gap:6px;">
          <strong>${html(item.name)}</strong>
          <small class="muted" style="font-size:10px;">${html(item.code)}</small>
        </div>
      </td>
      <td><span class="sector-badge">${html(sec)}</span></td>
      <td>${html(item.account_name || item.broker)}</td>
      <td>${number(item.quantity, 4)}</td>
      <td>${money(item.market_value_krw)}</td>
      <td class="${signClass(item.profit_krw)}">${item.profit_krw >= 0 ? "+" : ""}${money(item.profit_krw)}</td>
      <td class="${signClass(rate)}">${rate >= 0 ? "+" : ""}${number(rate)}%</td>
      <td class="${signClass(dayRate)}">${dayRate >= 0 ? "+" : ""}${number(dayRate)}%</td>
      <td>
        <button class="button secondary tiny stock-chart-btn" data-code="${item.code}" data-name="${html(item.name)}" data-price="${item.current_price}" data-currency="${item.currency}" title="가격 및 거래량 차트" type="button" style="padding:2px 6px;font-size:11px;">📊</button>
      </td>
      <td>
        <button class="icon-button holding-edit-btn" data-holding-id="${item.id}" title="종목 수정" type="button">✎</button>
        <button class="icon-button holding-del-btn" data-holding-id="${item.id}" title="종목 삭제" type="button">×</button>
      </td>
    </tr>`;
  }).join("");

  $("#emptyHoldings").hidden = sorted.length > 0;
  $(".table-wrap").hidden = sorted.length === 0;
}


// ── 4. 종목별 가격 & 거래량 인터랙티브 차트 모달 ──────────────────────────────
async function openStockChart(code, name, price, currency = 'KRW') {
  if (!code) return;
  currentStockChartCode = code;
  const dlg = document.getElementById('stockChartDialog');
  if (!dlg) return;

  document.getElementById('stockChartTitle').textContent = name || code;
  document.getElementById('stockChartCode').textContent = code;
  document.getElementById('stockChartPrice').textContent = money(price, currency);

  dlg.showModal();
  await loadStockChartData(code, currentStockChartPeriod);
}

async function loadStockChartData(code, period) {
  const container = document.getElementById('stockChartBody');
  if (!container) return;
  container.innerHTML = '<div class="empty" style="padding:100px 0;">차트 데이터를 불러오는 중입니다…</div>';

  try {
    const res = await api(`/api/stock-chart/${encodeURIComponent(code)}?period=${encodeURIComponent(period)}`);
    renderStockSvgChart(res, container);
  } catch (err) {
    container.innerHTML = `<div class="empty" style="padding:80px 0;color:#ff6b81;">차트 로드 실패: ${html(err.message)}</div>`;
  }
}

function renderStockSvgChart(data, container) {
  const candles = data.candles || [];
  if (!candles.length) {
    container.innerHTML = '<div class="empty" style="padding:80px 0;">해당 기간의 캔들 데이터가 없습니다.</div>';
    return;
  }

  const prices = candles.map(c => Number(c.close || 0));
  const volumes = candles.map(c => Number(c.volume || 0));
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const spanP = maxP - minP || (minP * 0.01) || 1;

  const maxV = Math.max(...volumes) || 1;

  const w = 700;
  const hPrice = 180;
  const hVol = 70;
  const pad = 12;

  // 가격 라인 좌표
  const pricePoints = candles.map((c, i) => {
    const x = pad + (i / Math.max(candles.length - 1, 1)) * (w - pad * 2);
    const y = pad + (hPrice - pad * 2) * (1 - (c.close - minP) / spanP);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const lineStr = pricePoints.join(' ');
  const baseAreaStr = `${lineStr} ${(w - pad)},${hPrice} ${pad},${hPrice}`;

  // 거래량 바 좌표
  const barW = Math.max(2, Math.min(12, (w - pad * 2) / candles.length - 2));
  const volBars = candles.map((c, i) => {
    const x = pad + (i / Math.max(candles.length - 1, 1)) * (w - pad * 2) - barW / 2;
    const barH = Math.max(2, (c.volume / maxV) * (hVol - 10));
    const y = hPrice + 30 + (hVol - barH);
    const isUp = c.close >= (c.open || c.close);
    const col = isUp ? '#ff5c77' : '#4f9dff';
    return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${barH.toFixed(1)}" fill="${col}" opacity="0.65" rx="1.5" />`;
  }).join('');

  const firstP = prices[0];
  const lastP = prices[prices.length - 1];
  const diffP = lastP - firstP;
  const diffRate = firstP ? (diffP / firstP * 100) : 0;
  const isUp = diffRate >= 0;
  const color = isUp ? '#ff5c77' : '#4f9dff';

  // 변경치 업데이트
  const changeEl = document.getElementById('stockChartChange');
  if (changeEl) {
    changeEl.textContent = `${isUp ? '+' : ''}${money(diffP, data.currency)} (${isUp ? '+' : ''}${diffRate.toFixed(2)}%)`;
    changeEl.className = isUp ? 'up' : 'down';
  }

  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:11px;color:#91a0c1;">
      <span>최저 ${money(minP, data.currency)}</span>
      <span>기간 수익률: <b class="${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${diffRate.toFixed(2)}%</b></span>
      <span>최고 ${money(maxP, data.currency)}</span>
    </div>
    <svg viewBox="0 0 ${w} ${hPrice + 30 + hVol}" style="width:100%;height:auto;display:block;" preserveAspectRatio="none">
      <defs>
        <linearGradient id="chartGradArea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.3" />
          <stop offset="100%" stop-color="${color}" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <!-- 그리드 라인 -->
      <line x1="${pad}" y1="${pad}" x2="${w-pad}" y2="${pad}" stroke="#1f2c4d" stroke-dasharray="3,3" />
      <line x1="${pad}" y1="${hPrice/2}" x2="${w-pad}" y2="${hPrice/2}" stroke="#1f2c4d" stroke-dasharray="3,3" />
      <line x1="${pad}" y1="${hPrice}" x2="${w-pad}" y2="${hPrice}" stroke="#263558" stroke-width="1.2" />

      <!-- 가격 영역 & 선 -->
      <polygon points="${baseAreaStr}" fill="url(#chartGradArea)" />
      <polyline points="${lineStr}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />

      <!-- 거래량 섹션 구분선 -->
      <line x1="${pad}" y1="${hPrice + 25}" x2="${w-pad}" y2="${hPrice + 25}" stroke="#263558" stroke-width="1" />
      <text x="${pad}" y="${hPrice + 20}" fill="#7182a6" font-size="10" font-weight="700">거래량 (VOLUME)</text>

      <!-- 거래량 바 -->
      ${volBars}
    </svg>
    <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:10px;color:#7182a6;">
      <span>${candles[0].date}</span>
      <span>최대 거래량: ${number(maxV, 0)}</span>
      <span>${candles[candles.length - 1].date}</span>
    </div>
  `;
}

// 종목 차트 탭 클릭 이벤트
document.getElementById('stockChartPeriodTabs')?.addEventListener('click', async (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab || !currentStockChartCode) return;
  document.querySelectorAll('#stockChartPeriodTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentStockChartPeriod = tab.dataset.period || '1M';
  await loadStockChartData(currentStockChartCode, currentStockChartPeriod);
});

// 보유종목 클릭 시 차트 오픈 이벤트 위임
document.addEventListener('click', (e) => {
  const chartBtn = e.target.closest('.stock-chart-btn');
  if (chartBtn) {
    const code = chartBtn.dataset.code;
    const name = chartBtn.dataset.name;
    const price = chartBtn.dataset.price;
    const currency = chartBtn.dataset.currency;
    openStockChart(code, name, price, currency);
    return;
  }
  const nameCell = e.target.closest('.holding-name-cell');
  if (nameCell) {
    const row = nameCell.closest('tr');
    const code = row?.dataset.code;
    const item = (dashboard?.holdings || []).find(h => h.code === code);
    if (item) openStockChart(item.code, item.name, item.current_price, item.currency);
  }
});


// ── 5. 자산기록 멀티 라인 차트 (총자산 + 투자원금 + 손익) & 기간 필터 ─────────
function filterRecordsByPeriod(records, period) {
  if (!records || !records.length || period === 'ALL') return records;
  const now = new Date();
  let days = 30;
  if (period === '1M') days = 30;
  else if (period === '3M') days = 90;
  else if (period === '6M') days = 180;
  else if (period === '1Y') days = 365;

  const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  return records.filter(r => r.date && r.date >= cutoff);
}

function renderAssetRecords(records) {
  window.assetRecords = records || [];
  allAssetRecords = records || [];

  const rawList = [...records].sort((a, b) => String(a.date || '').localeCompare(String(b.date || '')));
  const filtered = filterRecordsByPeriod(rawList, currentRecordPeriod);
  const wrap = $("#assetChart");

  if (!filtered.length) {
    wrap.innerHTML = '<div class="empty">선택한 기간의 자산기록이 없습니다.</div>';
    $("#assetRecordList").innerHTML = "";
    $("#recordCount").textContent = "0개 기록";
    return;
  }

  const values = filtered.map(item => Number(item.total_value_krw || 0));
  const costs = filtered.map(item => Number(item.total_cost_krw || 0));
  const minVal = Math.min(...values, ...costs.filter(c => c > 0));
  const maxVal = Math.max(...values, ...costs);
  const span = maxVal - minVal || 1;

  const w = 900;
  const h = 260;
  const pad = 24;

  // 총자산 라인 (보라색)
  const totalPoints = filtered.map((pt, i) => {
    const x = pad + ((w - pad * 2) * i) / Math.max(filtered.length - 1, 1);
    const y = h - pad - ((Number(pt.total_value_krw || 0) - minVal) / span) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const totalPath = totalPoints.join(" ");

  // 투자원금 라인 (청록색)
  const hasCosts = costs.some(c => c > 0);
  const costPoints = hasCosts ? filtered.map((pt, i) => {
    const cVal = Number(pt.total_cost_krw || pt.total_value_krw || 0);
    const x = pad + ((w - pad * 2) * i) / Math.max(filtered.length - 1, 1);
    const y = h - pad - ((cVal - minVal) / span) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }) : [];
  const costPath = costPoints.join(" ");

  const baseline = `${24},${h - pad} ${w - pad},${h - pad}`;
  const first = filtered[0];
  const last = filtered.at(-1);

  wrap.innerHTML = `
    <div style="display:flex;justify-content:flex-end;gap:12px;margin-bottom:8px;font-size:11px;">
      <span style="display:flex;align-items:center;gap:4px;"><i style="display:inline-block;width:10px;height:3px;background:#8e70fa;border-radius:2px;"></i> 총 투자자산</span>
      ${hasCosts ? '<span style="display:flex;align-items:center;gap:4px;"><i style="display:inline-block;width:10px;height:3px;background:#42d5a3;border-radius:2px;border:1px dashed #42d5a3;"></i> 총 투자원금</span>' : ''}
    </div>
    <svg class="record-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-label="자산 기록 차트">
      <defs>
        <linearGradient id="recordFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#8e70fa" stop-opacity="0.3" />
          <stop offset="100%" stop-color="#8e70fa" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <line x1="${pad}" y1="${h - pad}" x2="${w - pad}" y2="${h - pad}" stroke="#2a3557" stroke-width="1" />
      <polygon points="${totalPath} ${baseline}" fill="url(#recordFill)" stroke="none" />
      ${hasCosts ? `<polyline points="${costPath}" fill="none" stroke="#42d5a3" stroke-width="2" stroke-dasharray="4,3" stroke-linecap="round" stroke-linejoin="round" />` : ''}
      <polyline points="${totalPath}" fill="none" stroke="#8e70fa" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    <div class="record-chart-meta">
      <div><span>기간 시작</span><strong>${html(first.date)}</strong><small>${money(first.total_value_krw)}</small></div>
      <div><span>최근 기록</span><strong>${html(last.date)}</strong><small>${money(last.total_value_krw)}</small></div>
      <div><span>최저 / 최고</span><strong>${money(minVal)} / ${money(maxVal)}</strong><small>해당 기간 ${number(filtered.length, 0)}개 기록</small></div>
    </div>`;

  const delta = Number(last.total_value_krw || 0) - Number(first.total_value_krw || 0);
  const deltaRate = Number(first.total_value_krw || 0) ? delta / Number(first.total_value_krw || 0) * 100 : 0;
  $("#recordSummary").textContent = `${money(delta)} (${deltaRate >= 0 ? "+" : ""}${number(deltaRate)}%)`;
  $("#recordSummary").className = signClass(delta);
  $("#recordCount").textContent = `${number(filtered.length, 0)}개 기록`;

  // 리스트는 최신순 표시
  const descRecords = [...filtered].reverse();
  $("#assetRecordList").innerHTML = descRecords.map((item) => `
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

// 자산기록 기간 탭 클릭 이벤트
document.getElementById('recordPeriodTabs')?.addEventListener('click', (e) => {
  const tab = e.target.closest('.heatmap-tab');
  if (!tab) return;
  document.querySelectorAll('#recordPeriodTabs .heatmap-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentRecordPeriod = tab.dataset.period || 'ALL';
  renderAssetRecords(window.assetRecords || []);
});
'''

# 1. Update renderMarkets in wealth.js
OLD_RENDER_MARKETS = '''function renderMarkets(result) {
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
}'''

NEW_RENDER_MARKETS = '''function renderMarkets(result) {
  const mkts = result.markets || [];
  const fx = result.exchange_rate || {};
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
}'''

if OLD_RENDER_MARKETS in js:
    js = js.replace(OLD_RENDER_MARKETS, NEW_RENDER_MARKETS, 1)
    print("OK 1. Replaced renderMarkets in wealth.js")

# Insert FEATURE_EXTENSIONS before loadDashboard
SW_INSERT_POS = js.find('// ── 데이터 저장 / 불러오기')
if SW_INSERT_POS != -1:
    js = js[:SW_INSERT_POS] + FEATURE_EXTENSIONS + '\n\n' + js[SW_INSERT_POS:]
    print("OK 2. Inserted feature extensions into wealth.js")
else:
    js = js + '\n\n' + FEATURE_EXTENSIONS
    print("OK 2. Appended feature extensions to wealth.js")

# Update openHoldingDialog to support sector field
OLD_OHD = 'form.market.value = record?.market || "";'
NEW_OHD = '''form.market.value = record?.market || "";
  if (form.sector) form.sector.value = record?.sector || "";'''

if OLD_OHD in js and 'form.sector' not in js:
    js = js.replace(OLD_OHD, NEW_OHD, 1)
    print("OK 3. Added sector field mapping to openHoldingDialog")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print("wealth.js updates complete!")
