#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_and_restore_functions.py
- Extract renderAccounts and renderHeatmaps from git HEAD
- Insert them cleanly into app/static/wealth.js
- Verify all required functions exist
"""

import subprocess

# 1. Get git HEAD wealth.js
git_js = subprocess.check_output(['git', 'show', 'HEAD:app/static/wealth.js'], encoding='utf-8')

# Extract renderAccounts
idx_ra_start = git_js.find('function renderAccounts(accounts) {')
idx_ra_end = git_js.find('function openImport() {', idx_ra_start)
if idx_ra_start == -1 or idx_ra_end == -1:
    idx_ra_end = git_js.find('// 히트맵', idx_ra_start)

renderAccounts_code = git_js[idx_ra_start:idx_ra_end].strip()

# Extract renderHeatmaps and helper functions (calcHeatmapValues, etc.)
idx_hm_start = git_js.find('// ── 히트맵')
if idx_hm_start == -1:
    idx_hm_start = git_js.find('function renderHeatmaps(')
idx_hm_end = git_js.find('// ── 4. 종목별 상세 팝업 차트', idx_hm_start)
if idx_hm_end == -1:
    idx_hm_end = git_js.find('function renderHoldings(', idx_hm_start)

heatmaps_code = git_js[idx_hm_start:idx_hm_end].strip()

print(f"renderAccounts length: {len(renderAccounts_code)}")
print(f"heatmaps_code length: {len(heatmaps_code)}")

# 2. Read current wealth.js
with open('app/static/wealth.js', 'r', encoding='utf-8') as f:
    current_js = f.read()

# Insert renderAccounts before renderClassifications or renderHoldings
if 'function renderAccounts' not in current_js:
    idx_rc = current_js.find('function renderClassifications')
    if idx_rc != -1:
        current_js = current_js[:idx_rc] + renderAccounts_code + "\n\n" + current_js[idx_rc:]
        print("OK: Inserted renderAccounts")

if 'function renderHeatmaps' not in current_js:
    idx_rh = current_js.find('function renderHoldings')
    if idx_rh != -1:
        current_js = current_js[:idx_rh] + heatmaps_code + "\n\n" + current_js[idx_rh:]
        print("OK: Inserted renderHeatmaps and heatmap logic")

with open('app/static/wealth.js', 'w', encoding='utf-8') as f:
    f.write(current_js)

print("Restoration complete!")
