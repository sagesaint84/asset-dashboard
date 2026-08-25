#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reorganize_wealth_js.py
- Move all variable declarations to the top of wealth.js (eliminate Temporal Dead Zone bugs)
- Place bootstrap() at the very bottom of wealth.js
- Ensure loadAssetRecords and renderAssetRecords work flawlessly
"""

with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Remove early bootstrap() call around line 800
early_bootstrap = """async function bootstrap() { await loadFamilyMembers(); await loadDashboard().catch((error) => toast(error.message, true)); await loadMarkets(); await loadAssetRecords('모두'); }
bootstrap();"""
if early_bootstrap in code:
    code = code.replace(early_bootstrap, "")
    print("OK: Removed early bootstrap() call")

# 2. Check if currentRecordPeriod is declared at top
if "let currentRecordPeriod" not in code[:1000]:
    # Add top variables
    top_anchor = "let allAssetRecords = [];"
    new_top_vars = """let allAssetRecords = [];
let assetRecords = [];
let currentRecordPeriod = 'ALL'; // '1M' | '3M' | '6M' | '1Y' | 'ALL'
let currentSectorTab = 'asset_class'; // 'asset_class' | 'sector'
"""
    code = code.replace(top_anchor, new_top_vars, 1)
    # Remove later duplicate declarations of currentRecordPeriod
    code = code.replace("let currentRecordPeriod = 'ALL'; // '1M' | '3M' | '6M' | '1Y' | 'ALL'\n", "")
    print("OK: Moved currentRecordPeriod and assetRecords to top")

# 3. In renderAssetRecords, ensure allAssetRecords is NOT overwritten
old_rar_top = """function renderAssetRecords(records) {
  window.assetRecords = records || [];
  allAssetRecords = records || [];"""

new_rar_top = """function renderAssetRecords(records) {
  assetRecords = records || [];
  window.assetRecords = records || [];"""

if old_rar_top in code:
    code = code.replace(old_rar_top, new_rar_top, 1)
    print("OK: Fixed allAssetRecords overwrite in renderAssetRecords")

# 4. Append bootstrap() at the very end if not already at bottom
if not code.strip().endswith("bootstrap();"):
    bootstrap_code = """

// ── APP BOOTSTRAP ─────────────────────────────────────────────────────────────
async function bootstrap() {
  try {
    await loadFamilyMembers();
  } catch (e) {
    console.error("loadFamilyMembers failed:", e);
  }
  try {
    await loadDashboard();
  } catch (e) {
    console.error("loadDashboard failed:", e);
    toast(e.message || "대시보드를 불러오지 못했습니다.", true);
  }
  try {
    await loadMarkets();
  } catch (e) {
    console.error("loadMarkets failed:", e);
  }
  try {
    await loadAssetRecords('모두');
  } catch (e) {
    console.error("loadAssetRecords failed:", e);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}
"""
    code = code.strip() + bootstrap_code
    print("OK: Appended safe bootstrap() at the bottom of wealth.js")

with open("app/static/wealth.js", "w", encoding="utf-8") as f:
    f.write(code)

print("wealth.js reorganization complete!")
