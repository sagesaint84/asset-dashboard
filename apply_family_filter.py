#!/usr/bin/env python3
"""
apply_family_filter.py
Applies all family-owner filter changes:
  1. index.html  – add family tabs + owner fields to dialogs
  2. main.py     – owner filter on GET /api/accounts, owner saved on PUT
  3. wealth.js   – family tab logic, openAccountEditDialog owner, holdingDialog owner
"""

import re, sys

# ──────────────────────────────────────────────────────────────────────────────
# 1. index.html
# ──────────────────────────────────────────────────────────────────────────────
HTML_PATH = r'app\static\index.html'
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# 1a. Add family-tabs to ACCOUNTS panel-head (after the h2 closing tag, before addAccountBtn)
OLD_ACCT_HEAD = '<div class="panel-head"><div><p class="eyebrow">ACCOUNTS</p><h2>증권사 통합 현황</h2></div><button id="addAccountBtn"'
NEW_ACCT_HEAD = (
    '<div class="panel-head" style="flex-wrap:wrap;gap:0.5rem;">'
    '<div><p class="eyebrow">ACCOUNTS</p><h2>증권사 통합 현황</h2></div>'
    '<div class="family-tabs" id="familyTabs" style="display:flex;gap:0.35rem;align-items:center;">'
    '<button type="button" class="family-tab active" data-owner="모두">모두</button>'
    '<button type="button" class="family-tab" data-owner="아빠">아빠</button>'
    '<button type="button" class="family-tab" data-owner="엄마">엄마</button>'
    '<button type="button" class="family-tab" data-owner="자녀">자녀</button>'
    '</div>'
    '<button id="addAccountBtn"'
)
if OLD_ACCT_HEAD in html:
    html = html.replace(OLD_ACCT_HEAD, NEW_ACCT_HEAD, 1)
    print('✅ 1a. Family tabs added to ACCOUNTS panel')
else:
    print('⚠️  1a. ACCOUNTS panel-head not found – skipping')

# 1b. Add owner <select> to accountEditDialog (after the <label>계좌 이름 block)
OLD_EDIT_GRID = (
    '<label>계좌 이름\n'
    '            <input name="name" placeholder="종합계좌, ISA, IRP 등" required />\n'
    '          </label>\n'
    '        </div>'
)
NEW_EDIT_GRID = (
    '<label>계좌 이름\n'
    '            <input name="name" placeholder="종합계좌, ISA, IRP 등" required />\n'
    '          </label>\n'
    '          <label>소유자\n'
    '            <select name="owner">\n'
    '              <option value="모두">모두</option>\n'
    '              <option value="아빠">아빠</option>\n'
    '              <option value="엄마">엄마</option>\n'
    '              <option value="자녀">자녀</option>\n'
    '            </select>\n'
    '          </label>\n'
    '        </div>'
)
if OLD_EDIT_GRID in html:
    html = html.replace(OLD_EDIT_GRID, NEW_EDIT_GRID, 1)
    print('✅ 1b. Owner select added to accountEditDialog')
else:
    print('⚠️  1b. accountEditDialog form-grid not found – skipping')

# 1c. Add owner <select> to holdingDialog (append after market label, before </div><div class="dialog-actions">)
# The holdingDialog is all on one line, so we search inline
OLD_HOLDING_MARKET = '<label>거래소<input name="market" placeholder="KRX, NAS, NYS 등" /></label></div><div class="dialog-actions">'
NEW_HOLDING_MARKET = (
    '<label>거래소<input name="market" placeholder="KRX, NAS, NYS 등" /></label>'
    '<label>소유자<select name="owner">'
    '<option value="모두">모두</option>'
    '<option value="아빠">아빠</option>'
    '<option value="엄마">엄마</option>'
    '<option value="자녀">자녀</option>'
    '</select></label></div><div class="dialog-actions">'
)
if OLD_HOLDING_MARKET in html:
    html = html.replace(OLD_HOLDING_MARKET, NEW_HOLDING_MARKET, 1)
    print('✅ 1c. Owner select added to holdingDialog')
else:
    print('⚠️  1c. holdingDialog market label not found – skipping')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print()

# ──────────────────────────────────────────────────────────────────────────────
# 2. main.py
# ──────────────────────────────────────────────────────────────────────────────
MAIN_PATH = r'app\main.py'
with open(MAIN_PATH, 'r', encoding='utf-8') as f:
    main = f.read()

# 2a. Add `owner` field to HoldingCreate
OLD_HOLDING_MODEL = '    currency: str = "KRW"\n    market: str = ""\n'
NEW_HOLDING_MODEL = '    currency: str = "KRW"\n    market: str = ""\n    owner: str = "모두"\n'
if OLD_HOLDING_MODEL in main:
    main = main.replace(OLD_HOLDING_MODEL, NEW_HOLDING_MODEL, 1)
    print('✅ 2a. owner field added to HoldingCreate')
else:
    print('⚠️  2a. HoldingCreate model tail not found – skipping')

# 2b. Update GET /api/accounts to filter by owner
OLD_GET_ACCOUNTS = (
    '    accounts = full.get("accounts", [])\n'
    '    filtered = [a for a in accounts if group == "All" or a.get("family_group", "All") == group]\n'
)
NEW_GET_ACCOUNTS = (
    '    accounts = full.get("accounts", [])\n'
    '    owner = (getattr(request, "query_params", {}) or {}).get("owner", "모두") if hasattr(group, "__class__") else "모두"\n'
    '    filtered = [a for a in accounts if group == "All" or a.get("family_group", "All") == group]\n'
)
# Actually, let me do a different approach for the owner filter in GET /api/accounts
# I'll change the function signature to add owner param
OLD_GET_SIG = 'async def get_accounts(group: str = "All") -> dict:'
NEW_GET_SIG = 'async def get_accounts(group: str = "All", owner: str = "모두") -> dict:'
if OLD_GET_SIG in main:
    main = main.replace(OLD_GET_SIG, NEW_GET_SIG, 1)
    print('✅ 2b-i. owner param added to get_accounts signature')
else:
    print('⚠️  2b-i. get_accounts signature not found – skipping')

OLD_FILTER_LINE = '    filtered = [a for a in accounts if group == "All" or a.get("family_group", "All") == group]\n'
NEW_FILTER_LINE = (
    '    filtered = [a for a in accounts\n'
    '                if (owner == "모두" or a.get("owner", "모두") == owner)\n'
    '                and (group == "All" or a.get("family_group", "All") == group)]\n'
)
if OLD_FILTER_LINE in main:
    main = main.replace(OLD_FILTER_LINE, NEW_FILTER_LINE, 1)
    print('✅ 2b-ii. owner filter applied in get_accounts')
else:
    print('⚠️  2b-ii. filtered line not found – skipping')

# 2c. Update PUT /api/accounts/:id to save owner field
OLD_PUT_ACCOUNT = (
    '    account["name"] = name\n'
    '    if broker:\n'
    '        account["broker"] = broker\n'
)
NEW_PUT_ACCOUNT = (
    '    account["name"] = name\n'
    '    if broker:\n'
    '        account["broker"] = broker\n'
    '    owner_val = str(payload.get("owner") or "").strip()\n'
    '    if owner_val:\n'
    '        account["owner"] = owner_val\n'
)
if OLD_PUT_ACCOUNT in main:
    main = main.replace(OLD_PUT_ACCOUNT, NEW_PUT_ACCOUNT, 1)
    print('✅ 2c. owner saved in PUT /api/accounts/:id')
else:
    print('⚠️  2c. PUT accounts owner block not found – skipping')

# 2d. Save owner on account when creating/updating holdings
OLD_CREATE_HOLD = (
    '    account_id = get_or_add_account(data, payload.broker.strip(), payload.account_name.strip(), "manual")\n'
    '    item = normalize_holding(payload.model_dump(), account_id, payload.broker.strip(), payload.account_name.strip(), "manual")\n'
    '    upsert_holdings(data, [item])\n'
    '    write_portfolio(data)\n'
    '    return {"message": "보유종목을 저장했습니다.", "dashboard": get_dashboard()}\n'
)
NEW_CREATE_HOLD = (
    '    account_id = get_or_add_account(data, payload.broker.strip(), payload.account_name.strip(), "manual")\n'
    '    item = normalize_holding(payload.model_dump(), account_id, payload.broker.strip(), payload.account_name.strip(), "manual")\n'
    '    # propagate owner to account\n'
    '    owner_val = getattr(payload, "owner", "모두") or "모두"\n'
    '    for acct in data.get("accounts", []):\n'
    '        if acct.get("id") == account_id:\n'
    '            acct["owner"] = owner_val\n'
    '            break\n'
    '    upsert_holdings(data, [item])\n'
    '    write_portfolio(data)\n'
    '    return {"message": "보유종목을 저장했습니다.", "dashboard": get_dashboard()}\n'
)
if OLD_CREATE_HOLD in main:
    main = main.replace(OLD_CREATE_HOLD, NEW_CREATE_HOLD, 1)
    print('✅ 2d. owner propagated in POST /api/holdings')
else:
    print('⚠️  2d. create_holding body not found – skipping')

with open(MAIN_PATH, 'w', encoding='utf-8') as f:
    f.write(main)
print()

# ──────────────────────────────────────────────────────────────────────────────
# 3. wealth.js
# ──────────────────────────────────────────────────────────────────────────────
JS_PATH = r'app\static\wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 3a. Add currentOwner state variable and family tab handler after the dashboard variable declaration
OLD_DASHBOARD_VAR = 'const $ = (selector) => document.querySelector(selector);\nlet dashboard = null;\n'
NEW_DASHBOARD_VAR = (
    'const $ = (selector) => document.querySelector(selector);\n'
    'let dashboard = null;\n'
    "let currentOwner = '모두'; // 선택된 가족 구성원\n"
    '\n'
    '// ── 가족 탭 클릭 핸들러 ─────────────────────────────────────────────────────\n'
    'document.addEventListener(\'click\', (e) => {\n'
    '  const tab = e.target.closest(\'#familyTabs .family-tab\');\n'
    '  if (!tab) return;\n'
    '  currentOwner = tab.dataset.owner || \'모두\';\n'
    '  document.querySelectorAll(\'#familyTabs .family-tab\').forEach(t => t.classList.remove(\'active\'));\n'
    '  tab.classList.add(\'active\');\n'
    '  if (dashboard) renderWithOwner(dashboard, currentOwner);\n'
    '});\n'
    '\n'
    'function renderWithOwner(data, owner) {\n'
    '  // Filter accounts by owner\n'
    '  const filteredData = Object.assign({}, data);\n'
    '  if (owner !== \'모두\') {\n'
    '    filteredData.accounts = (data.accounts || []).filter(a => (a.owner || \'모두\') === owner);\n'
    '    filteredData.holdings = (data.holdings || []).filter(h => {\n'
    '      const acct = (data.accounts || []).find(a => a.id === h.account_id);\n'
    '      return acct && (acct.owner || \'모두\') === owner;\n'
    '    });\n'
    '  }\n'
    '  render(filteredData);\n'
    '}\n'
)
if 'currentOwner' not in js:
    if OLD_DASHBOARD_VAR in js:
        js = js.replace(OLD_DASHBOARD_VAR, NEW_DASHBOARD_VAR, 1)
        print('✅ 3a. currentOwner state and family tab handler added')
    else:
        print('⚠️  3a. dashboard var declaration not found – skipping')
else:
    print('ℹ️  3a. currentOwner already exists – skipping')

# 3b. Update loadDashboard to use renderWithOwner
OLD_LOAD_DASHBOARD = "async function loadDashboard() { render(await api(\"/api/dashboard\")); }"
NEW_LOAD_DASHBOARD = "async function loadDashboard() { const data = await api(\"/api/dashboard\"); dashboard = data; renderWithOwner(data, currentOwner); }"
if OLD_LOAD_DASHBOARD in js:
    js = js.replace(OLD_LOAD_DASHBOARD, NEW_LOAD_DASHBOARD, 1)
    print('✅ 3b. loadDashboard updated to use renderWithOwner')
else:
    print('⚠️  3b. loadDashboard definition not found – skipping')

# 3c. Update openAccountEditDialog to populate owner field
OLD_OPEN_EDIT = (
    'function openAccountEditDialog(account) {\n'
    '  const form = $(\"#accountEditForm\");\n'
    '  if (!form || !account) return;\n'
    '  form.reset();\n'
    '  form.dataset.accountId = account.id;\n'
    '  form.broker.value = account.broker || \"\";\n'
    '  form.name.value = account.name || \"\";\n'
    '  $(\"#accountEditDialog\").showModal();\n'
    '}'
)
NEW_OPEN_EDIT = (
    'function openAccountEditDialog(account) {\n'
    '  const form = $(\"#accountEditForm\");\n'
    '  if (!form || !account) return;\n'
    '  form.reset();\n'
    '  form.dataset.accountId = account.id;\n'
    '  form.broker.value = account.broker || \"\";\n'
    '  form.name.value = account.name || \"\";\n'
    '  if (form.owner) form.owner.value = account.owner || \"모두\";\n'
    '  $(\"#accountEditDialog\").showModal();\n'
    '}'
)
if OLD_OPEN_EDIT in js:
    js = js.replace(OLD_OPEN_EDIT, NEW_OPEN_EDIT, 1)
    print('✅ 3c. openAccountEditDialog updated with owner field')
else:
    print('⚠️  3c. openAccountEditDialog not found – skipping')

# 3d. Update accountEditForm submit to include owner in payload
OLD_EDIT_PAYLOAD = (
    '  const payload = {\n'
    '    broker: form.broker.value.trim(),\n'
    '    name: form.name.value.trim(),\n'
    '  };'
)
NEW_EDIT_PAYLOAD = (
    '  const payload = {\n'
    '    broker: form.broker.value.trim(),\n'
    '    name: form.name.value.trim(),\n'
    '    owner: form.owner ? form.owner.value : \"모두\",\n'
    '  };'
)
if OLD_EDIT_PAYLOAD in js:
    js = js.replace(OLD_EDIT_PAYLOAD, NEW_EDIT_PAYLOAD, 1)
    print('✅ 3d. accountEditForm submit updated with owner')
else:
    print('⚠️  3d. accountEditForm payload not found – skipping')

# 3e. Update openHoldingDialog to populate owner field
OLD_OPEN_HOLDING = (
    '  form.currency.value = record?.currency || \"KRW\"; form.market.value = record?.market || \"\";\n'
    '  $(\"#holdingDialog\").showModal();'
)
NEW_OPEN_HOLDING = (
    '  form.currency.value = record?.currency || \"KRW\"; form.market.value = record?.market || \"\";\n'
    '  if (form.owner) {\n'
    '    // Try to find owner from linked account\n'
    '    const linkedAcct = dashboard?.accounts?.find(a => a.id === record?.account_id);\n'
    '    form.owner.value = linkedAcct?.owner || record?.owner || \"모두\";\n'
    '  }\n'
    '  $(\"#holdingDialog\").showModal();'
)
if OLD_OPEN_HOLDING in js:
    js = js.replace(OLD_OPEN_HOLDING, NEW_OPEN_HOLDING, 1)
    print('✅ 3e. openHoldingDialog updated with owner field')
else:
    print('⚠️  3e. openHoldingDialog currency/market line not found – skipping')

# 3f. Update holdingForm submit payload to include owner
OLD_HOLDING_SUBMIT = (
    'const form = e.currentTarget, payload = Object.fromEntries(new FormData(form)); '
    '[\"quantity\", \"avg_price\", \"current_price\"].forEach'
)
NEW_HOLDING_SUBMIT = (
    'const form = e.currentTarget, payload = Object.fromEntries(new FormData(form)); '
    'if (!payload.owner) payload.owner = \"모두\"; '
    '[\"quantity\", \"avg_price\", \"current_price\"].forEach'
)
if OLD_HOLDING_SUBMIT in js:
    js = js.replace(OLD_HOLDING_SUBMIT, NEW_HOLDING_SUBMIT, 1)
    print('✅ 3f. holdingForm submit updated with owner')
else:
    print('⚠️  3f. holdingForm submit not found – skipping')

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)
print()
print('✅ All patches applied. Please restart the server.')
