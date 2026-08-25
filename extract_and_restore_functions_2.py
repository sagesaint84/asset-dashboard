#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess

git_js = subprocess.check_output(['git', 'show', 'HEAD:app/static/wealth.js'], encoding='utf-8')

# Extract renderAccounts
idx1 = git_js.find('function renderAccounts(items) {')
idx2 = git_js.find('function openImport() {', idx1)
renderAccounts_code = git_js[idx1:idx2].strip()

# Extract renderHeatmaps and its entire block
idx_hm1 = git_js.find('// ── 3. 포트폴리오 히트맵')
if idx_hm1 == -1:
    idx_hm1 = git_js.find('function renderHeatmaps(')
idx_hm2 = git_js.find('// ── 4. 종목별 상세 팝업 차트', idx_hm1)
if idx_hm2 == -1:
    idx_hm2 = git_js.find('function renderHoldings(', idx_hm1)
heatmaps_code = git_js[idx_hm1:idx_hm2].strip()

print(f"renderAccounts length: {len(renderAccounts_code)}")
print(f"heatmaps_code length: {len(heatmaps_code)}")

with open('app/static/wealth.js', 'r', encoding='utf-8') as f:
    current_js = f.read()

# Replace or add renderAccounts
if 'function renderAccounts' not in current_js:
    idx_rc = current_js.find('function renderClassifications')
    current_js = current_js[:idx_rc] + renderAccounts_code + "\n\n" + current_js[idx_rc:]
    print("OK: Inserted renderAccounts")

if 'function renderHeatmaps' not in current_js:
    idx_rh = current_js.find('function renderHoldings')
    current_js = current_js[:idx_rh] + heatmaps_code + "\n\n" + current_js[idx_rh:]
    print("OK: Inserted renderHeatmaps")

with open('app/static/wealth.js', 'w', encoding='utf-8') as f:
    f.write(current_js)

print("Insertion finished!")
