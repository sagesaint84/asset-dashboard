#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_responsive_topbar_tabs.py
- Remove inline style from topbarFamilyTabs in index.html
- Update wealth-overrides.css for mobile narrow & mobile wide layouts
"""

# 1. index.html inline style 제거
HTML_PATH = 'app/static/index.html'
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

OLD_TAG = '<div class="family-tabs topbar-family-tabs" id="topbarFamilyTabs" style="display:flex;gap:0.3rem;align-items:center;flex-wrap:wrap;">'
NEW_TAG = '<div class="family-tabs topbar-family-tabs" id="topbarFamilyTabs">'

if OLD_TAG in html:
    html = html.replace(OLD_TAG, NEW_TAG, 1)
    print("OK: Removed inline style from index.html")
else:
    print("INFO: Inline style already clean or different")

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

# 2. wealth-overrides.css 업데이트
CSS_PATH = 'app/static/wealth-overrides.css'
with open(CSS_PATH, 'r', encoding='utf-8') as f:
    css = f.read()

# 기존 탑바 가족 탭 관련 구문 수정
OLD_TOPBAR_FAMILY_CSS = '''/* ── 탑바 가족 탭 (더 컴팩트하게) ─────────────────────────────────────────── */
.topbar-family-tabs {
  margin-left: 12px;
}
.topbar-family-tabs .family-tab {
  padding: 3px 10px;
  font-size: 12px;
}
.topbar-brand-wrap {
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: wrap;
}'''

NEW_TOPBAR_FAMILY_CSS = '''/* ── 탑바 가족 탭 반응형 레이아웃 ───────────────────────────────────────── */
.topbar-brand-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1 1 auto;
}

.topbar-family-tabs {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-left: auto; /* 기본: 우측 정렬 */
}

.topbar-family-tabs .family-tab {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 7px;
  text-align: center;
}

/* 태블릿 및 넓은 모바일 (가로 화면, 601px ~ 1080px) */
@media (min-width: 601px) and (max-width: 1080px) {
  .topbar-brand-wrap {
    width: 100%;
    justify-content: space-between;
  }
  .topbar-family-tabs {
    margin-left: auto;
    justify-content: flex-end;
  }
  .topbar-family-tabs .family-tab {
    padding: 6px 14px;
    font-size: 13px;
  }
}

/* 모바일 좁은 화면 (세로 화면, 600px 이하) */
@media (max-width: 600px) {
  .topbar-brand-wrap {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }
  .topbar-family-tabs {
    width: 100%;
    margin-left: 0;
    margin-top: 4px;
    display: flex;
    gap: 6px;
    justify-content: stretch;
  }
  .topbar-family-tabs .family-tab {
    flex: 1 1 0;
    min-width: 0;
    padding: 8px 4px;
    font-size: 13px;
    text-align: center;
  }
}'''

if OLD_TOPBAR_FAMILY_CSS in css:
    css = css.replace(OLD_TOPBAR_FAMILY_CSS, NEW_TOPBAR_FAMILY_CSS, 1)
    print("OK: Replaced old topbar-family-tabs CSS")
else:
    # 없으면 파일 끝에 추가
    css = css.rstrip() + "\n\n" + NEW_TOPBAR_FAMILY_CSS + "\n"
    print("OK: Appended new topbar-family-tabs CSS")

with open(CSS_PATH, 'w', encoding='utf-8') as f:
    f.write(css)

print("All CSS & HTML updates complete!")
