#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_index_html_features.py
- Add [자산군별 / 섹터별] tabs to allocation panel
- Add [1M / 3M / 6M / 1Y / ALL] tabs to asset records panel
- Add sector column and sortable headers to holdings table
- Add sector field to holdingDialog
- Add #stockChartDialog modal for stock price & volume charts
"""

HTML_PATH = 'app/static/index.html'
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Allocation panel tabs
OLD_ALLOC_HEAD = '''        <article class="panel classification-panel overview-right">
          <div class="panel-head">
            <div><p class="eyebrow">ALLOCATION</p><h2>투자자산 분류</h2></div>
            <span class="muted">수익률 · 비중</span>
          </div>
          <div id="classificationList" class="classification-list"></div>
        </article>'''

NEW_ALLOC_HEAD = '''        <article class="panel classification-panel overview-right">
          <div class="panel-head" style="flex-wrap:wrap;gap:0.5rem;align-items:center;">
            <div><p class="eyebrow">ALLOCATION</p><h2>투자자산 분류</h2></div>
            <div class="heatmap-period-tabs" id="allocTabs" style="margin-left:auto;">
              <button type="button" class="heatmap-tab active" data-alloc="class">자산군별</button>
              <button type="button" class="heatmap-tab" data-alloc="sector">섹터별</button>
            </div>
            <span class="muted" style="font-size:11px;">수익률 · 비중</span>
          </div>
          <div id="classificationList" class="classification-list"></div>
        </article>'''

if OLD_ALLOC_HEAD in html:
    html = html.replace(OLD_ALLOC_HEAD, NEW_ALLOC_HEAD, 1)
    print("OK 1. Added allocation tabs (자산군별/섹터별)")

# 2. Asset records period tabs & legend
OLD_RECORDS_HEAD = '''        <div class="panel-head records-head">
          <div><p class="eyebrow">ASSET RECORDS</p><h2>자산기록</h2></div>
          <div class="toolbar">
            <span id="recordCount" class="muted">0개 기록</span>
            <button id="snapshotButton" class="button secondary compact" type="button">오늘 기록 저장</button>
            <button id="addRecordButton" class="button primary compact" type="button">+ 자산기록 추가</button>
          </div>
        </div>'''

NEW_RECORDS_HEAD = '''        <div class="panel-head records-head" style="flex-wrap:wrap;gap:0.5rem;align-items:center;">
          <div><p class="eyebrow">ASSET RECORDS</p><h2>자산기록</h2></div>
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
        </div>'''

if OLD_RECORDS_HEAD in html:
    html = html.replace(OLD_RECORDS_HEAD, NEW_RECORDS_HEAD, 1)
    print("OK 2. Added asset record period tabs")

# 3. Sortable Holdings table headers with sector column
OLD_TABLE_HEAD = '<tr><th>종목</th><th>분류</th><th>계좌</th><th>수량</th><th>평가금액</th><th>평가이익</th><th>수익률</th><th>등락률</th><th></th></tr>'
NEW_TABLE_HEAD = '''<tr>
              <th data-sort="name" style="cursor:pointer;" title="종목명 정렬">종목 <span class="sort-icon"></span></th>
              <th data-sort="sector" style="cursor:pointer;" title="섹터 정렬">섹터 <span class="sort-icon"></span></th>
              <th>계좌</th>
              <th data-sort="quantity" style="cursor:pointer;" title="보유수량 정렬">수량 <span class="sort-icon"></span></th>
              <th data-sort="market_value_krw" style="cursor:pointer;" title="평가금액 정렬">평가금액 <span class="sort-icon">▼</span></th>
              <th data-sort="profit_krw" style="cursor:pointer;" title="평가손익 정렬">평가이익 <span class="sort-icon"></span></th>
              <th data-sort="rate" style="cursor:pointer;" title="수익률 정렬">수익률 <span class="sort-icon"></span></th>
              <th data-sort="day_change_rate" style="cursor:pointer;" title="일간등락률 정렬">등락률 <span class="sort-icon"></span></th>
              <th>차트</th>
              <th></th>
            </tr>'''

if OLD_TABLE_HEAD in html:
    html = html.replace(OLD_TABLE_HEAD, NEW_TABLE_HEAD, 1)
    print("OK 3. Added sortable headers and sector column to holdings table")

# 4. Add sector input to holdingDialog
OLD_HOLDING_FORM = '<label>종목명<input name="name" required /></label>'
NEW_HOLDING_FORM = '''<label>종목명<input name="name" required /></label>
        <label>섹터 (업종 분류)
          <input name="sector" list="sectorOptions" placeholder="반도체, IT·빅테크, 2차전지 등" />
          <datalist id="sectorOptions">
            <option value="반도체"></option>
            <option value="IT·빅테크"></option>
            <option value="2차전지"></option>
            <option value="금융·지주"></option>
            <option value="전력·인프라"></option>
            <option value="방산·우주"></option>
            <option value="조선·기계"></option>
            <option value="바이오·헬스케어"></option>
            <option value="소비재·뷰티"></option>
            <option value="엔터·미디어"></option>
            <option value="자동차·운송"></option>
            <option value="리츠·부동산"></option>
            <option value="미국 대표지수"></option>
            <option value="국내 대표지수"></option>
            <option value="채권·안전자산"></option>
          </datalist>
        </label>'''

if OLD_HOLDING_FORM in html and 'name="sector"' not in html:
    html = html.replace(OLD_HOLDING_FORM, NEW_HOLDING_FORM, 1)
    print("OK 4. Added sector field to holdingDialog")

# 5. Add #stockChartDialog modal
CHART_DIALOG = '''
    <!-- 종목별 가격 & 거래량 인터랙티브 차트 다이얼로그 -->
    <dialog id="stockChartDialog" class="dialog" style="max-width:760px;width:calc(100vw - 32px);">
      <div class="dialog-head" style="padding:18px 22px 10px;border-bottom:1px solid #1c2848;">
        <div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;">
          <h2 id="stockChartTitle" style="font-size:19px;margin:0;">종목 차트</h2>
          <span id="stockChartCode" class="muted" style="font-size:12px;font-weight:700;"></span>
          <span id="stockChartPrice" style="font-size:17px;font-weight:800;margin-left:auto;"></span>
          <span id="stockChartChange" style="font-size:13px;font-weight:700;"></span>
        </div>
        <button value="cancel" class="close" aria-label="닫기">×</button>
      </div>
      <div style="padding:14px 22px 20px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
          <div class="heatmap-period-tabs" id="stockChartPeriodTabs">
            <button type="button" class="heatmap-tab" data-period="1W">1주</button>
            <button type="button" class="heatmap-tab active" data-period="1M">1개월</button>
            <button type="button" class="heatmap-tab" data-period="3M">3개월</button>
            <button type="button" class="heatmap-tab" data-period="YTD">연초대비</button>
            <button type="button" class="heatmap-tab" data-period="1Y">1년</button>
          </div>
          <span class="muted" style="font-size:11px;">상단: 가격 추세 선 · 하단: 거래량 바</span>
        </div>
        <div id="stockChartBody" style="min-height:300px;position:relative;background:#090e1d;border-radius:10px;padding:12px;border:1px solid #1a2542;">
          <div class="empty" style="padding:100px 0;">차트 데이터를 불러오는 중입니다…</div>
        </div>
      </div>
    </dialog>
'''

if 'id="stockChartDialog"' not in html:
    idx_end = html.find('</main>')
    if idx_end != -1:
        html = html[:idx_end] + CHART_DIALOG + '\n' + html[idx_end:]
        print("OK 5. Added stockChartDialog modal to index.html")

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print("index.html updates complete!")
