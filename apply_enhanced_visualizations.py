#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_enhanced_visualizations.py
1. Fix holding edit/delete button event delegation
2. Add Sector Donut Chart (원그래프) to renderClassifications
3. Add Line + Bar Combo Chart (총자산 선 + 일간/누적 손익 막대) to renderAssetRecords
"""

JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Fix holding edit / delete button click delegation
OLD_HB_CLICK = '$("#holdingsBody").addEventListener("click", (e) => { const edit = e.target.closest(".edit-button"); const button = e.target.closest(".delete-button"); if (edit) { const item = dashboard?.holdings.find((row) => row.id === edit.dataset.id); if (item) openHoldingDialog(item); return; } if (button && confirm("이 보유종목을 삭제할까요?")) action(button, () => api(`/api/holdings/${button.dataset.id}`, { method: "DELETE" })); });'

NEW_HB_CLICK = '''$("#holdingsBody").addEventListener("click", (e) => {
  const editBtn = e.target.closest(".holding-edit-btn, .edit-button");
  const delBtn = e.target.closest(".holding-del-btn, .delete-button");
  if (editBtn) {
    const hid = editBtn.dataset.holdingId || editBtn.dataset.id;
    const item = dashboard?.holdings.find((row) => row.id === hid);
    if (item) openHoldingDialog(item);
    return;
  }
  if (delBtn) {
    const hid = delBtn.dataset.holdingId || delBtn.dataset.id;
    if (confirm("이 보유종목을 삭제할까요?")) {
      action(delBtn, () => api(`/api/holdings/${hid}`, { method: "DELETE" }));
    }
  }
});'''

if OLD_HB_CLICK in js:
    js = js.replace(OLD_HB_CLICK, NEW_HB_CLICK, 1)
    print("OK 1. Fixed holdingsBody edit/delete click delegation")

# 2. Sector Donut Chart Palette
SECTOR_PALETTE = [
    "#8e70fa", "#4f9dff", "#42d5a3", "#ff718c", "#fbbf24",
    "#a78bfa", "#38bdf8", "#34d399", "#f43f5e", "#f59e0b",
    "#c084fc", "#60a5fa", "#4ade80", "#fb7185", "#eab308", "#94a3b8"
]

NEW_RENDER_CLASSIFICATIONS = '''// ── 1. 투자자산 분류 (자산군별 프로그레스 바 / 섹터별 도넛 원그래프) ───────────────
const SECTOR_PALETTE = [
  "#8e70fa", "#4f9dff", "#42d5a3", "#ff718c", "#fbbf24",
  "#a78bfa", "#38bdf8", "#34d399", "#f43f5e", "#f59e0b",
  "#c084fc", "#60a5fa", "#4ade80", "#fb7185", "#eab308", "#94a3b8"
];

function renderClassifications(items) {
  const isSector = currentAllocTab === 'sector';
  let targetItems = [];
  const totalVal = Number(dashboard?.summary?.total_value_krw || 0);

  if (isSector) {
    targetItems = dashboard?.sector_classifications || [];
    if (!targetItems.length && dashboard?.holdings) {
      const secMap = {};
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

  if (isSector) {
    // ── 섹터별 원그래프 (SVG 도넛 차트) 렌더링 ──
    const size = 180;
    const center = size / 2;
    const radius = 72;
    const innerRadius = 46;
    let accumulatedAngle = -Math.PI / 2; // 12시 방향부터 시작

    const slices = targetItems.map((item, idx) => {
      const w = Math.max(Number(item.weight || 0), 0);
      const angle = (w / 100) * (Math.PI * 2);
      const startAngle = accumulatedAngle;
      const endAngle = accumulatedAngle + angle;
      accumulatedAngle = endAngle;

      const color = SECTOR_PALETTE[idx % SECTOR_PALETTE.length];

      // 각도에 따른 호 좌표 계산
      const x1 = center + radius * Math.cos(startAngle);
      const y1 = center + radius * Math.sin(startAngle);
      const x2 = center + radius * Math.cos(endAngle);
      const y2 = center + radius * Math.sin(endAngle);

      const ix1 = center + innerRadius * Math.cos(endAngle);
      const iy1 = center + innerRadius * Math.sin(endAngle);
      const ix2 = center + innerRadius * Math.cos(startAngle);
      const iy2 = center + innerRadius * Math.sin(startAngle);

      const largeArcFlag = angle > Math.PI ? 1 : 0;

      // 아주 작은 각도는 선 표시
      if (angle <= 0.001) return '';

      const pathData = `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${ix2} ${iy2} Z`;
      return `<path d="${pathData}" fill="${color}" stroke="#0d1326" stroke-width="1.5" title="${html(item.name || item.label)}: ${number(w, 1)}%"><title>${html(item.name || item.label)} (${number(w, 1)}%) - ${money(item.market_value_krw)}</title></path>`;
    }).join("");

    const donutHtml = `
      <div style="display:flex;align-items:center;justify-content:center;gap:18px;margin-bottom:16px;padding:10px 0;border-bottom:1px solid #1c2848;flex-wrap:wrap;">
        <div style="position:relative;width:${size}px;height:${size}px;flex-shrink:0;">
          <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
            ${slices}
          </svg>
          <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;pointer-events:none;">
            <div style="font-size:10px;color:#91a0c1;font-weight:700;">섹터 비중</div>
            <div style="font-size:13px;font-weight:800;color:#f3f5ff;">${targetItems.length}개</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(2, 1fr);gap:6px 12px;font-size:11px;max-width:260px;">
          ${targetItems.slice(0, 8).map((it, idx) => `
            <div style="display:flex;align-items:center;gap:5px;">
              <i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${SECTOR_PALETTE[idx % SECTOR_PALETTE.length]};"></i>
              <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:85px;" title="${html(it.name || it.label)}">${html(it.name || it.label)}</span>
              <b style="margin-left:auto;color:#c4b5fd;">${number(it.weight, 1)}%</b>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    const listHtml = targetItems.map((item, idx) => {
      const rate = Number(item.return_rate ?? item.rate ?? 0);
      const weight = Number(item.weight ?? 0);
      const countText = item.holding_count ? `${number(item.holding_count, 0)}종목` : '';
      const label = item.name || item.label || item.key || '기타';
      const color = SECTOR_PALETTE[idx % SECTOR_PALETTE.length];
      return `
        <div class="classification-row">
          <div class="classification-title">
            <strong style="display:flex;align-items:center;gap:6px;">
              <i style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${color};"></i>
              ${html(label)}
            </strong>
            <span>${countText ? countText + ' · ' : ''}${number(weight, 1)}%</span>
          </div>
          <div class="classification-value">
            <span>${money(item.market_value_krw)}</span>
            <b class="${signClass(rate)}">${rate >= 0 ? "+" : ""}${number(rate)}%</b>
          </div>
          <div class="bar"><i style="width: ${Math.min(Math.max(weight, 0), 100)}%; background: ${color};"></i></div>
        </div>`;
    }).join("");

    list.innerHTML = donutHtml + listHtml;
  } else {
    // 자산군별 기본 프로그레스 바 목록
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
}'''

# Replace renderClassifications
OLD_RC_START = '// ── 1. 투자자산 분류 (자산군별 / 섹터별) 탭 전환'
idx_rc = js.find(OLD_RC_START)
if idx_rc != -1:
    idx_rc_end = js.find('document.getElementById(\'allocTabs\')', idx_rc)
    if idx_rc_end != -1:
        js = js[:idx_rc] + NEW_RENDER_CLASSIFICATIONS + '\n\n' + js[idx_rc_end:]
        print("OK 2. Replaced renderClassifications with Donut chart")

# 3. Combo Chart (Line for Total Asset + Bar for Day/Total Profit)
NEW_RENDER_ASSET_RECORDS = '''// ── 5. 자산기록 콤보 차트 (총자산 선그래프 + 일간/누적 손익 위/아래 막대그래프) ────────
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
  const profits = filtered.map(item => Number(item.day_profit_krw || 0));

  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const spanVal = maxVal - minVal || (minVal * 0.05) || 1;

  const maxAbsProfit = Math.max(...profits.map(Math.abs), 100000);

  const w = 900;
  const h = 280;
  const pad = 24;

  // 상단 60% 영역: 총자산 선 그래프
  const hLineArea = 160;
  const linePoints = filtered.map((pt, i) => {
    const x = pad + ((w - pad * 2) * i) / Math.max(filtered.length - 1, 1);
    const y = pad + (hLineArea - pad) * (1 - (Number(pt.total_value_krw || 0) - minVal) / spanVal);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const linePath = linePoints.join(" ");
  const lineAreaPath = `${linePath} ${(w - pad)},${hLineArea} ${pad},${hLineArea}`;

  // 하단 40% 영역: 0선 기준 위/아래 손익 막대그래프
  const hBarAreaTop = hLineArea + 25;
  const hBarAreaHeight = h - hBarAreaTop - pad;
  const zeroY = hBarAreaTop + (hBarAreaHeight / 2); // 0원 기준선

  const barWidth = Math.max(3, Math.min(18, (w - pad * 2) / filtered.length - 3));
  const bars = filtered.map((pt, i) => {
    const x = pad + ((w - pad * 2) * i) / Math.max(filtered.length - 1, 1) - barWidth / 2;
    const p = Number(pt.day_profit_krw || 0);
    const isGain = p >= 0;
    const barH = Math.max(2, (Math.abs(p) / maxAbsProfit) * (hBarAreaHeight / 2 - 4));
    const y = isGain ? (zeroY - barH) : zeroY;
    const color = isGain ? '#ff5c77' : '#4f9dff';
    return `
      <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barH.toFixed(1)}"
        fill="${color}" opacity="0.8" rx="1.5">
        <title>${pt.date}: ${isGain ? '+' : ''}${money(p)}</title>
      </rect>
    `;
  }).join('');

  const first = filtered[0];
  const last = filtered.at(-1);

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

      <!-- 총자산 상단 영역 -->
      <line x1="${pad}" y1="${hLineArea}" x2="${w - pad}" y2="${hLineArea}" stroke="#1f2c4d" stroke-dasharray="3,3" />
      <polygon points="${lineAreaPath}" fill="url(#recordComboGrad)" stroke="none" />
      <polyline points="${linePath}" fill="none" stroke="#8e70fa" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" />

      <!-- 하단 손익 막대 영역 (0선 기준선) -->
      <line x1="${pad}" y1="${zeroY}" x2="${w - pad}" y2="${zeroY}" stroke="#334673" stroke-width="1.2" />
      <text x="${pad}" y="${hLineArea + 18}" fill="#7182a6" font-size="10" font-weight="700">일간 손익 (PROFIT / LOSS)</text>
      <text x="${w - pad}" y="${zeroY - 4}" fill="#7182a6" font-size="9" text-anchor="end">0원</text>

      ${bars}
    </svg>
    <div class="record-chart-meta">
      <div><span>기간 시작</span><strong>${html(first.date)}</strong><small>${money(first.total_value_krw)}</small></div>
      <div><span>최근 기록</span><strong>${html(last.date)}</strong><small>${money(last.total_value_krw)}</small></div>
      <div><span>최저 / 최고 자산</span><strong>${money(minVal)} / ${money(maxVal)}</strong><small>해당 기간 ${number(filtered.length, 0)}개 기록</small></div>
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
}'''

OLD_RAR_START = '// ── 5. 자산기록 멀티 라인 차트'
idx_rar = js.find(OLD_RAR_START)
if idx_rar != -1:
    idx_rar_end = js.find('// 자산기록 기간 탭 클릭 이벤트', idx_rar)
    if idx_rar_end != -1:
        js = js[:idx_rar] + NEW_RENDER_ASSET_RECORDS + '\n\n' + js[idx_rar_end:]
        print("OK 3. Replaced renderAssetRecords with Combo chart (Line + Bar)")

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print("Visualization updates complete!")
