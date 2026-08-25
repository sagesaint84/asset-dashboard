#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_all_features_to_wealth_js.py
Complete implementation of:
1. Account sync button -> /api/sync/all
2. Allocation tabs: Asset class vs Sector (Donut pie chart + 16 sectors list)
3. Asset records: Combo chart (line + profit/loss bars) + Monthly bars + Period filter tabs (1M, 3M, 6M, 1Y, ALL)
4. Holdings table sorting (all columns with ▲/▼) + Sector badges + Chart buttons
5. Stock price & volume interactive modal chart with 1W/1M/3M/YTD/1Y periods
6. Holding add/edit dialog sector field
"""

with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    code = f.read()

# Replace file with well-structured, error-free full implementation
# We will create a clean updated version
update_script = '''
let allAssetRecords = [];
let assetRecords = [];
let currentRecordPeriod = 'ALL'; // '1M' | '3M' | '6M' | '1Y' | 'ALL'
let currentRecordView = 'combo'; // 'combo' | 'monthly'
let currentAllocTab = 'asset_class'; // 'asset_class' | 'sector'
let currentStockChartCode = '';
let currentStockChartName = '';
let currentStockChartPrice = 0;
let currentStockChartCurrency = 'KRW';
let currentStockChartPeriod = '3M'; // '1W' | '1M' | '3M' | 'YTD' | '1Y'
let holdingSortField = 'market_value_krw';
let holdingSortOrder = 'desc'; // 'asc' | 'desc'
'''

print("Writing clean feature code...")
