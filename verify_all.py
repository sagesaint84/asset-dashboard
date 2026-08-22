import sys
sys.path.insert(0, '.')

checks = []

# ── wealth.js checks ──────────────────────────────────────────────────────────
with open('app/static/wealth.js', encoding='utf-8') as f:
    js = f.read()

checks += [
    ('rawDashboard variable',          'let rawDashboard = null'),
    ('computeFilteredSummary fn',      'function computeFilteredSummary'),
    ('computeFilteredClassifications', 'function computeFilteredClassifications'),
    ('computeFilteredCurrencySummary', 'function computeFilteredCurrencySummary'),
    ('computeFilteredDayChange',       'function computeFilteredDayChange'),
    ('renderWithOwner recalc',         'filteredData.summary = computeFilteredSummary'),
    ('loadAssetRecords owner param',   'ownerParam'),
    ('loadFamilyMembers fn',           'async function loadFamilyMembers'),
    ('renderFamilyTabs fn',            'function renderFamilyTabs'),
    ('family tab click delegation',    "target.closest('#familyTabs .family-tab')"),
    ('openFamilyManager fn',           'async function openFamilyManager'),
    ('addMemberBtn delegation',        "target.closest('#addMemberBtn')"),
    ('family-rename-btn delegation',   "target.closest('.family-rename-btn')"),
    ('family-delete-btn delegation',   "target.closest('.family-delete-btn')"),
    ('bootstrap loads family',         'await loadFamilyMembers()'),
    ('addAccountBtn handler',          "_addAccountBtn"),
    ('accountAddForm submit',          "getElementById('accountAddForm')"),
]

# ── main.py checks ────────────────────────────────────────────────────────────
with open('app/main.py', encoding='utf-8') as f:
    main = f.read()

checks += [
    ('POST /api/accounts',             'async def create_account'),
    ('GET /api/accounts owner param',  'owner: str = "모두"'),
    ('GET /api/accounts owner filter', 'a.get("owner"'),
    ('PUT /api/accounts owner save',   'owner_val'),
    ('GET /api/family-members',        'async def list_family_members'),
    ('POST /api/family-members',       'async def add_family_member'),
    ('PUT /api/family-members',        'async def rename_family_member'),
    ('DELETE /api/family-members',     'async def delete_family_member'),
    ('GET /api/asset-records owner',   'if owner and owner != "모두"'),
    ('POST /api/asset-records owner',  'payload["owner"]'),
    ('HoldingCreate owner field',      'owner: str = "모두"'),
]

# ── index.html checks ────────────────────────────────────────────────────────
with open('app/static/index.html', encoding='utf-8') as f:
    html = f.read()

import re
script_idx = html.find('<script src="/static/wealth.js')
dialog_idx = html.find('id="familyManagerDialog"')
checks += [
    ('familyTabs container in HTML',       'id="familyTabs"'),
    ('manageFamilyBtn in HTML',            'id="manageFamilyBtn"'),
    ('familyManagerDialog in HTML',        'id="familyManagerDialog"'),
    ('addMemberBtn in HTML',               'id="addMemberBtn"'),
    ('dialog is BEFORE script',            str(0 < dialog_idx < script_idx)),
    ('owner select in accountEditDialog',  'accountEditDialog' in html and 'name="owner"' in html),
    ('owner select in holdingDialog',      'holdingForm' in html and 'name="owner"' in html),
    ('addAccountBtn in HTML',              'id="addAccountBtn"'),
    ('accountAddDialog in HTML',           'id="accountAddDialog"'),
]

# ── Print results ─────────────────────────────────────────────────────────────
ok = 0; fail = 0
for name, check in checks:
    # check is either a string (presence check) or a bool
    if isinstance(check, bool):
        result = check
    else:
        result = check in (js + main + html)
    mark = 'OK  ' if result else 'MISS'
    if result: ok += 1
    else: fail += 1
    print(f'[{mark}] {name}')

print(f'\n{ok}/{ok+fail} checks passed')
