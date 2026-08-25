#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_index_html.py
- Update topbar sync button to single [🔗 계좌 연결]
- Add Allocation [자산군별] / [섹터별] tabs & donut container
- Add Asset Records [📈 콤보 차트] / [📊 월별 자산] view tabs & [1M, 3M, 6M, 1Y, ALL] period tabs
- Add sortable table headers with sector column
- Add stock chart interactive modal (#stockChartDialog)
- Add sector select field to holding form dialog
"""

with open("app/static/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Top actions buttons
old_top_actions = """        <div class="top-actions">
          <button id="syncKbButton" class="button secondary" type="button">KB</button>
          <button id="syncTossButton" class="button secondary" type="button">토스</button>
          <button id="syncNamooButton" class="button secondary" type="button">나무</button>
          <button id="refreshButton" class="button primary compact" type="button">🔄 갱신</button>

        </div>"""

new_top_actions = """        <div class="top-actions">
          <button id="syncAccountsButton" class="button secondary compact" type="button">🔗 계좌 연결</button>
          <button id="refreshButton" class="button primary compact" type="button">🔄 갱신</button>
        </div>"""

if old_top_actions in html:
    html = html.replace(old_top_actions, new_top_actions, 1)
    print("OK: Top actions updated to [🔗 계좌 연결] & [🔄 갱신]")

# 2. Allocation panel
old_alloc = """        <article class="panel classification-panel overview-right">
          <div class="panel-head">
            <div><p class="eyebrow">ALLOCATION</p><h2>투자자산 분류</h2></div>
            <span class="muted">수익률 · 비중</span>
          </div>
          <div id="classificationList" class="classification-list"></div>
        </article>"""

new_alloc = """        <article class="panel classification-panel overview-right">
          <div class="panel-head" style="flex-wrap:wrap;gap:0.5rem;align-items:center;">
            <div><p class="eyebrow">ALLOCATION</p><h2>투자자산 분류</h2></div>
            <div class="heatmap-period-tabs" id="allocTabs">
              <button type="button" class="heatmap-tab active" data-tab="asset_class">자산군별</button>
              <button type="button" class="heatmap-tab" data-tab="sector">섹터별</button>
            </div>
            <span class="muted" style="margin-left:auto;font-size:11px;">수익률 · 비중</span>
          </div>
          <div id="sectorDonutWrap" style="display:none;margin:10px 0 16px;"></div>
          <div id="classificationList" class="classification-list"></div>
        </article>"""

if old_alloc in html:
    html = html.replace(old_alloc, new_alloc, 1)
    print("OK: Allocation panel tabs & sector donut container added")

# 3. Asset records panel
old_records = """      <!-- 2. 자산기록 -->
      <section class="panel records-panel">
        <div class="panel-head records-head">
          <div><p class="eyebrow">ASSET RECORDS</p><h2>자산기록</h2></div>
          <div class="toolbar">
            <span id="recordCount" class="muted">0개 기록</span>
            <button id="snapshotButton" class="button secondary compact" type="button">오늘 기록 저장</button>
            <button id="addRecordButton" class="button primary compact" type="button">+ 자산기록 추가</button>
          </div>
        </div>
        <div class="records-grid">
          <div id="assetChart" class="record-chart-wrap"></div>
          <div class="record-side">
            <div class="record-side-summary"><span>전체 변화</span><strong id="recordSummary">0원</strong><small>저장된 날짜별 자산 추이</small></div>
            <div id="assetRecordList" class="record-list"></div>
          </div>
        </div>
      </section>"""

new_records = """      <!-- 2. 자산기록 -->
      <section class="panel records-panel">
        <div class="panel-head records-head" style="flex-wrap:wrap;gap:0.5rem;align-items:center;">
          <div><p class="eyebrow">ASSET RECORDS</p><h2>자산기록</h2></div>
          <div class="heatmap-period-tabs" id="recordViewTabs" style="margin-right:6px;">
            <button type="button" class="heatmap-tab active" data-view="combo">📈 콤보 차트</button>
            <button type="button" class="heatmap-tab" data-view="monthly">📊 월별 자산</button>
          </div>
          <div class="heatmap-period-tabs" id="recordPeriodTabs">
            <button type="button" class="heatmap-tab" data-period="1M">1개월</button>
            <button type="button" class="heatmap-tab" data-period="3M">3개월</button>
            <button type="button" class="heatmap-tab" data-period="6M">6개월</button>
            <button type="button" class="heatmap-tab" data-period="1Y">1년</button>
            <button type="button" class="heatmap-tab active" data-period="ALL">전체</button>
          </div>
          <div class="toolbar" style="margin-left:auto;">
            <span id="recordCount" class="muted">0개 기록</span>
            <button id="snapshotButton" class="button secondary compact" type="button">오늘 기록 저장</button>
            <button id="addRecordButton" class="button primary compact" type="button">+ 자산기록 추가</button>
          </div>
        </div>
        <div class="records-grid">
          <div id="assetChart" class="record-chart-wrap"></div>
          <div class="record-side">
            <div class="record-side-summary"><span>전체 변화</span><strong id="recordSummary">0원</strong><small>저장된 날짜별 자산 추이</small></div>
            <div id="assetRecordList" class="record-list"></div>
          </div>
        </div>
      </section>"""

if old_records in html:
    html = html.replace(old_records, new_records, 1)
    print("OK: Asset records view tabs & period tabs added")

# 4. Holdings table headers with sector and sorting
old_table = """        <div class="table-wrap"><table><thead><tr><th>종목</th><th>분류</th><th>계좌</th><th>수량</th><th>평가금액</th><th>평가이익</th><th>수익률</th><th>등락률</th><th></th></tr></thead><tbody id="holdingsBody"></tbody></table></div>"""

new_table = """        <div class="table-wrap"><table><thead><tr>
          <th data-sort="name" class="sortable-th">종목 <span class="sort-icon"></span></th>
          <th data-sort="sector" class="sortable-th">섹터 <span class="sort-icon"></span></th>
          <th data-sort="account" class="sortable-th">계좌 <span class="sort-icon"></span></th>
          <th data-sort="quantity" class="sortable-th">수량 <span class="sort-icon"></span></th>
          <th data-sort="market_value_krw" class="sortable-th">평가금액 <span class="sort-icon"></span></th>
          <th data-sort="profit_krw" class="sortable-th">평가손익 <span class="sort-icon"></span></th>
          <th data-sort="return_rate" class="sortable-th">수익률 <span class="sort-icon"></span></th>
          <th data-sort="day_change_rate" class="sortable-th">등락률 <span class="sort-icon"></span></th>
          <th style="text-align:center;">차트/관리</th>
        </tr></thead><tbody id="holdingsBody"></tbody></table></div>"""

if old_table in html:
    html = html.replace(old_table, new_table, 1)
    print("OK: Holdings table headers updated with sortable columns and sector")

# 5. Holding dialog sector select field
old_holding_dialog = """<label>거래소<input name="market" placeholder="KRX, NAS, NYS 등" /></label><label>소유자<select name="owner"><option value="모두">모두</option><option value="아빠">아빠</option><option value="엄마">엄마</option><option value="자녀">자녀</option></select></label>"""

new_holding_dialog = """<label>거래소<input name="market" placeholder="KRX, NAS, NYS 등" /></label><label>섹터 분류<select name="sector">
  <option value="">자동 판별 (기본값)</option>
  <option value="반도체">반도체</option>
  <option value="IT·빅테크">IT·빅테크</option>
  <option value="2차전지">2차전지</option>
  <option value="금융·지주">금융·지주</option>
  <option value="전력·인프라">전력·인프라</option>
  <option value="방산·우주">방산·우주</option>
  <option value="조선·기계">조선·기계</option>
  <option value="바이오·헬스케어">바이오·헬스케어</option>
  <option value="소비재·뷰티">소비재·뷰티</option>
  <option value="엔터·미디어">엔터·미디어</option>
  <option value="자동차·운송">자동차·운송</option>
  <option value="리츠·부동산">리츠·부동산</option>
  <option value="미국 대표지수">미국 대표지수</option>
  <option value="국내 대표지수">국내 대표지수</option>
  <option value="채권·안전자산">채권·안전자산</option>
  <option value="기타">기타</option>
</select></label><label>소유자<select name="owner"><option value="모두">모두</option><option value="아빠">아빠</option><option value="엄마">엄마</option><option value="자녀">자녀</option></select></label>"""

if old_holding_dialog in html:
    html = html.replace(old_holding_dialog, new_holding_dialog, 1)
    print("OK: Holding form dialog sector select added")

# 6. Add stock chart modal if not present
if "id=\"stockChartDialog\"" not in html:
    chart_modal = """
    <!-- 종목 가격 & 거래량 인터랙티브 차트 모달 -->
    <dialog id="stockChartDialog" class="dialog" style="max-width:760px;width:95vw;">
      <div class="dialog-head" style="flex-wrap:wrap;gap:8px;align-items:center;">
        <div>
          <h2 id="stockChartTitle" style="margin:0;font-size:18px;">종목 차트</h2>
          <small id="stockChartCode" class="muted" style="font-size:12px;"></small>
        </div>
        <div class="heatmap-period-tabs" id="stockChartPeriodTabs" style="margin-left:auto;margin-right:10px;">
          <button type="button" class="heatmap-tab" data-period="1W">1주</button>
          <button type="button" class="heatmap-tab" data-period="1M">1개월</button>
          <button type="button" class="heatmap-tab active" data-period="3M">3개월</button>
          <button type="button" class="heatmap-tab" data-period="YTD">YTD</button>
          <button type="button" class="heatmap-tab" data-period="1Y">1년</button>
        </div>
        <button value="cancel" class="close" aria-label="닫기">×</button>
      </div>
      <div id="stockChartPriceRow" style="padding:10px 24px 0;display:flex;align-items:baseline;gap:12px;">
        <strong id="stockChartPrice" style="font-size:22px;"></strong>
        <span id="stockChartChange" class="sub-rate" style="font-size:14px;"></span>
      </div>
      <div id="stockChartContainer" style="padding:12px 24px 20px;min-height:300px;"></div>
    </dialog>
"""
    html = html.replace("  </body>", chart_modal + "\n  </body>")
    print("OK: Stock chart dialog modal added")

with open("app/static/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("index.html updated successfully!")
