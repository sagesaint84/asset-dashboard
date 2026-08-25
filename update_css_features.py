#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_css_features.py
Add CSS for:
- Sortable table headers (▲/▼ icons, hover states)
- Sector badges & donut chart layout
- Asset records combo & monthly bar charts
- Interactive stock chart modal styling
"""

with open("app/static/wealth-overrides.css", "r", encoding="utf-8") as f:
    css = f.read()

new_styles = """
/* =========================================================================
   추가 기능 스타일 (테이블 정렬, 섹터 도넛, 자산기록 콤보/월별, 종목 차트)
   ========================================================================= */

/* 1. 테이블 컬럼 정렬 */
.sortable-th {
  cursor: pointer;
  user-select: none;
  transition: color 0.15s ease, background-color 0.15s ease;
}
.sortable-th:hover {
  color: #c4b5fd !important;
  background-color: rgba(142, 112, 250, 0.08);
}
.sort-icon {
  display: inline-block;
  margin-left: 4px;
  font-size: 10px;
  color: #7182a6;
}
.sortable-th.sort-asc .sort-icon {
  color: #8e70fa;
}
.sortable-th.sort-asc .sort-icon::after {
  content: "▲";
}
.sortable-th.sort-desc .sort-icon {
  color: #8e70fa;
}
.sortable-th.sort-desc .sort-icon::after {
  content: "▼";
}

/* 2. 섹터 뱃지 */
.sector-badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(142, 112, 250, 0.14);
  color: #c4b5fd;
  border: 1px solid rgba(142, 112, 250, 0.28);
  white-space: nowrap;
}

/* 3. 종목 상세 차트 버튼 */
.stock-chart-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 7px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  background: #192545;
  color: #8fa0c5;
  border: 1px solid #2a3c66;
  cursor: pointer;
  transition: all 0.15s ease;
}
.stock-chart-btn:hover {
  background: #8e70fa;
  color: #fff;
  border-color: #8e70fa;
  transform: translateY(-1px);
}
.holding-name-link {
  cursor: pointer;
  transition: color 0.15s;
}
.holding-name-link:hover {
  color: #8e70fa;
  text-decoration: underline;
}

/* 4. 섹터 도넛 차트 컨테이너 & 범례 */
.sector-donut-container {
  display: flex;
  align-items: center;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px;
  background: #090e1d;
  border: 1px solid #1a2542;
  border-radius: 10px;
}
.sector-donut-svg-wrap {
  width: 140px;
  height: 140px;
  flex-shrink: 0;
  position: relative;
}
.sector-donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.sector-legend-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 160px;
  max-height: 140px;
  overflow-y: auto;
}
.sector-legend-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  gap: 8px;
}
.sector-legend-color {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex-shrink: 0;
}

/* 5. 자산기록 월별 막대 차트 뷰 */
.monthly-records-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 10px;
  padding: 10px;
}
.monthly-bar-card {
  background: #090e1d;
  border: 1px solid #1a2542;
  border-radius: 8px;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.monthly-bar-card .month-label {
  font-size: 12px;
  font-weight: 700;
  color: #aebbd7;
}
.monthly-bar-card .month-val {
  font-size: 13px;
  font-weight: 800;
  color: #f3f5ff;
}
.monthly-bar-card .month-delta {
  font-size: 11px;
  font-weight: 700;
}
"""

if "추가 기능 스타일" not in css:
    css = css.strip() + "\n" + new_styles
    with open("app/static/wealth-overrides.css", "w", encoding="utf-8") as f:
        f.write(css)
    print("OK: wealth-overrides.css updated with all new feature styles")
else:
    print("Notice: Styles already present")
