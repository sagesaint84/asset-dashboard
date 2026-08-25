#!/usr/bin/env python3
# -*- coding: utf-8 -*-
with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    js = f.read()

funcs = ["renderSummary", "renderClassifications", "renderAccounts", "renderHeatmaps", "renderHoldings", "renderAssetRecords"]
for fn in funcs:
    idx = js.find(f"function {fn}")
    print(f"{fn}: found at {idx}")
