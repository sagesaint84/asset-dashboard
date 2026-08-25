#!/usr/bin/env python3
# -*- coding: utf-8 -*-
with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    js = f.read()

vars_to_check = [
    'allAssetRecords', 'assetRecords', 'currentRecordPeriod', 'currentSectorTab',
    'currentStockChartPeriod', 'heatmapPeriod', 'heatmapCap', 'heatmapTheme',
    'dashboard', 'rawDashboard', 'currentOwner'
]

for v in vars_to_check:
    print(f"{v}: declared = {'let ' + v in js or 'var ' + v in js or 'const ' + v in js}")
