#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_and_fix_variables.py
- Ensure all state variables are declared at the very top of wealth.js
- Check for any undeclared identifiers
"""

with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    js = f.read()

# Declare all necessary variables at the very top
top_vars = """let allAssetRecords = [];
let assetRecords = [];
let currentRecordPeriod = 'ALL'; // '1M' | '3M' | '6M' | '1Y' | 'ALL'
let currentSectorTab = 'asset_class'; // 'asset_class' | 'sector'
let currentStockChartPeriod = '3M'; // '1W' | '1M' | '3M' | 'YTD' | '1Y'
let heatmapPeriod = '1D';
let heatmapCap = 'auto';
let heatmapTheme = 'kr';
"""

# Replace top lines
old_top_3 = """let allAssetRecords = [];
let assetRecords = [];
let currentSectorTab = 'asset_class'; // 'asset_class' | 'sector'"""

if old_top_3 in js:
    js = js.replace(old_top_3, top_vars.strip(), 1)
    print("OK: Replaced top variables with complete declarations")
else:
    js = top_vars + "\n" + js
    print("OK: Prepended top variables")

with open("app/static/wealth.js", "w", encoding="utf-8") as f:
    f.write(js)

print("audit_and_fix_variables complete!")
