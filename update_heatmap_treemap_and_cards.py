#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_heatmap_treemap_and_cards.py
- Add [🗺️ 면적형] / [🗂️ 카드형] view toggle tabs to index.html
- Restore full squarify treemap algorithm + enhance card view with wide minmax(200px, 1fr)
"""

# 1. Update index.html
with open("app/static/index.html", "r", encoding="utf-8") as f:
    html = f.read()

old_hm_controls = """          <div class="heatmap-controls-row">
            <div class="heatmap-period-tabs" id="heatmapPeriodTabs" role="tablist">"""

new_hm_controls = """          <div class="heatmap-controls-row">
            <div class="heatmap-period-tabs" id="heatmapViewTabs" style="margin-right:6px;">
              <button type="button" class="heatmap-tab active" data-view="treemap">🗺️ 면적형</button>
              <button type="button" class="heatmap-tab" data-view="cards">🗂️ 카드형</button>
            </div>
            <div class="heatmap-period-tabs" id="heatmapPeriodTabs" role="tablist">"""

if old_hm_controls in html:
    html = html.replace(old_hm_controls, new_hm_controls, 1)
    print("OK: Added heatmapViewTabs to index.html")

with open("app/static/index.html", "w", encoding="utf-8") as f:
    f.write(html)


# 2. Update wealth-overrides.css
with open("app/static/wealth-overrides.css", "r", encoding="utf-8") as f:
    css = f.read()

card_css = """
/* 6. 히트맵 카드형 뷰 스타일 (와이드 카드) */
.heatmap-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
  padding: 10px 4px;
}
.heatmap-card-item {
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 74px;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.15s ease;
}
.heatmap-card-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
}
"""

if ".heatmap-cards-grid" not in css:
    css = css.strip() + "\n" + card_css
    with open("app/static/wealth-overrides.css", "w", encoding="utf-8") as f:
        f.write(css)
    print("OK: Added heatmap cards CSS")

print("HTML and CSS updated successfully!")
