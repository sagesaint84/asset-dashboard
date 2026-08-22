#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_family_v2.py
- Fix "모두" bug (rawDashboard separation)
- Make family members configurable (add/rename/delete)
- Add CRUD API for family members in main.py
"""

# ──────────────────────────────────────────────────────────────────────────────
# 1. main.py – add family member CRUD endpoints
# ──────────────────────────────────────────────────────────────────────────────
MAIN_PATH = 'app/main.py'
with open(MAIN_PATH, 'r', encoding='utf-8') as f:
    main = f.read()

FAMILY_API = '''

# ---------------------------------------------------------------------------
# Family members CRUD API
# ---------------------------------------------------------------------------
DEFAULT_FAMILY_MEMBERS = ["아빠", "엄마", "자녀"]

def get_family_members(data: dict) -> list:
    return data.get("settings", {}).get("family_members", list(DEFAULT_FAMILY_MEMBERS))

@app.get("/api/family-members")
async def list_family_members() -> dict:
    data = read_portfolio()
    return {"members": get_family_members(data)}

@app.post("/api/family-members")
async def add_family_member(request: Request) -> dict:
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "이름을 입력해 주세요.")
    data = read_portfolio()
    members = get_family_members(data)
    if name in members:
        raise HTTPException(409, "이미 존재하는 이름입니다.")
    members.append(name)
    data.setdefault("settings", {})["family_members"] = members
    write_portfolio(data)
    return {"members": members, "message": f"'{name}' 구성원을 추가했습니다."}

@app.put("/api/family-members/{old_name}")
async def rename_family_member(old_name: str, request: Request) -> dict:
    body = await request.json()
    new_name = (body.get("name") or "").strip()
    if not new_name:
        raise HTTPException(400, "새 이름을 입력해 주세요.")
    data = read_portfolio()
    members = get_family_members(data)
    if old_name not in members:
        raise HTTPException(404, "구성원을 찾지 못했습니다.")
    if new_name in members and new_name != old_name:
        raise HTTPException(409, "이미 존재하는 이름입니다.")
    members = [new_name if m == old_name else m for m in members]
    data.setdefault("settings", {})["family_members"] = members
    # Update all accounts with old_name owner -> new_name
    for acct in data.get("accounts", []):
        if acct.get("owner") == old_name:
            acct["owner"] = new_name
    write_portfolio(data)
    return {"members": members, "message": f"'{old_name}' -> '{new_name}'으로 이름을 변경했습니다."}

@app.delete("/api/family-members/{member_name}")
async def delete_family_member(member_name: str) -> dict:
    data = read_portfolio()
    members = get_family_members(data)
    if member_name not in members:
        raise HTTPException(404, "구성원을 찾지 못했습니다.")
    members = [m for m in members if m != member_name]
    data.setdefault("settings", {})["family_members"] = members
    # Reset owner on accounts that belonged to deleted member
    for acct in data.get("accounts", []):
        if acct.get("owner") == member_name:
            acct["owner"] = "모두"
    write_portfolio(data)
    return {"members": members, "message": f"'{member_name}' 구성원을 삭제했습니다."}

'''

# Insert after the POST /api/accounts endpoint
INSERT_AFTER = 'return {"message": f"계좌 \'{broker} - {account_name}\'이(가) 추가되었습니다.", **new_account}'
if FAMILY_API.strip().split('\n')[3] not in main:
    idx = main.find(INSERT_AFTER)
    if idx != -1:
        end = main.find('\n', idx) + 1
        main = main[:end] + FAMILY_API + main[end:]
        print('OK 1. Family member CRUD endpoints added to main.py')
    else:
        print('WARN 1. Insert point not found in main.py')
else:
    print('INFO 1. Family CRUD already exists in main.py')

with open(MAIN_PATH, 'w', encoding='utf-8') as f:
    f.write(main)

# ──────────────────────────────────────────────────────────────────────────────
# 2. index.html – replace hardcoded family tabs with dynamic container
#    + add family management dialog
# ──────────────────────────────────────────────────────────────────────────────
HTML_PATH = 'app/static/index.html'
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the hardcoded family-tabs section with a dynamic one + manage button
OLD_TABS = (
    '<div class="family-tabs" id="familyTabs" style="display:flex;gap:0.35rem;align-items:center;">'
    '<button type="button" class="family-tab active" data-owner="\ub3fc\ub450">\ub3fc\ub450</button>'
    '<button type="button" class="family-tab" data-owner="\uc544\ube60">\uc544\ube60</button>'
    '<button type="button" class="family-tab" data-owner="\uc5c4\ub9c8">\uc5c4\ub9c8</button>'
    '<button type="button" class="family-tab" data-owner="\uc790\ub140">\uc790\ub140</button>'
    '</div>'
)
NEW_TABS = (
    '<div class="family-tabs" id="familyTabs" style="display:flex;gap:0.35rem;align-items:center;flex-wrap:wrap;">'
    '<button type="button" class="family-tab active" data-owner="\ub3fc\ub450">\ub3fc\ub450</button>'
    '</div>'
    '<button id="manageFamilyBtn" class="button text" type="button" title="\uac00\uc871 \uad6c\uc131\uc6d0 \uad00\ub9ac" style="padding:4px 8px;font-size:12px;">\u2699\ufe0f \uad00\ub9ac</button>'
)
if OLD_TABS in html:
    html = html.replace(OLD_TABS, NEW_TABS, 1)
    print('OK 2a. Family tabs replaced with dynamic container')
else:
    # Try encoded version
    OLD_TABS2 = (
        '<div class="family-tabs" id="familyTabs" style="display:flex;gap:0.35rem;align-items:center;">'
        '<button type="button" class="family-tab active" data-owner="모두">모두</button>'
        '<button type="button" class="family-tab" data-owner="아빠">아빠</button>'
        '<button type="button" class="family-tab" data-owner="엄마">엄마</button>'
        '<button type="button" class="family-tab" data-owner="자녀">자녀</button>'
        '</div>'
    )
    if OLD_TABS2 in html:
        html = html.replace(OLD_TABS2, NEW_TABS, 1)
        print('OK 2a. Family tabs replaced (UTF-8 match)')
    else:
        print('WARN 2a. Old family tabs not found, checking...')
        idx = html.find('id="familyTabs"')
        print(f'  familyTabs at index: {idx}')
        if idx >= 0:
            print(f'  Context: {repr(html[idx:idx+300])}')

# Add family management dialog before the closing </body>
FAMILY_DIALOG = '''
    <!-- 가족 구성원 관리 다이얼로그 -->
    <dialog id="familyManagerDialog" class="dialog">
      <div class="dialog-head">
        <h2>가족 구성원 관리</h2>
        <button value="cancel" class="close" aria-label="닫기">×</button>
      </div>
      <p class="dialog-description">구성원을 추가하거나 이름을 변경·삭제할 수 있습니다. "모두"는 항상 유지됩니다.</p>
      <div id="familyMemberList" style="display:flex;flex-direction:column;gap:8px;margin:12px 0;min-height:60px;"></div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <input id="newMemberName" type="text" placeholder="새 구성원 이름" style="flex:1;" maxlength="20" />
        <button id="addMemberBtn" class="button primary compact" type="button">추가</button>
      </div>
      <div class="dialog-actions">
        <button class="button secondary" value="cancel" type="button">닫기</button>
      </div>
    </dialog>
'''

if 'familyManagerDialog' not in html:
    html = html.replace('</body>', FAMILY_DIALOG + '\n  </body>', 1)
    print('OK 2b. Family manager dialog added')
else:
    print('INFO 2b. Family manager dialog already exists')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

# ──────────────────────────────────────────────────────────────────────────────
# 3. wealth.js – fix rawDashboard + dynamic family tabs
# ──────────────────────────────────────────────────────────────────────────────
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 3a. Add rawDashboard variable
OLD_STATE = "let dashboard = null;\nlet currentOwner = '모두'; // 선택된 가족 구성원\n"
NEW_STATE = "let dashboard = null;\nlet rawDashboard = null; // 필터링 전 원본 서버 데이터\nlet currentOwner = '모두'; // 선택된 가족 구성원\n"
if 'rawDashboard' not in js:
    if OLD_STATE in js:
        js = js.replace(OLD_STATE, NEW_STATE, 1)
        print('OK 3a. rawDashboard variable added')
    else:
        print('WARN 3a. State variable block not found')
else:
    print('INFO 3a. rawDashboard already exists')

# 3b. Fix renderWithOwner to always filter from rawDashboard
OLD_RENDER_WITH = '''function renderWithOwner(data, owner) {
  // Filter accounts by owner
  const filteredData = Object.assign({}, data);
  if (owner !== '모두') {
    filteredData.accounts = (data.accounts || []).filter(a => (a.owner || '모두') === owner);
    filteredData.holdings = (data.holdings || []).filter(h => {
      const acct = (data.accounts || []).find(a => a.id === h.account_id);
      return acct && (acct.owner || '모두') === owner;
    });
  }
  render(filteredData);
}'''
NEW_RENDER_WITH = '''function renderWithOwner(data, owner) {
  // Always filter from rawDashboard to prevent data loss on re-render
  const src = rawDashboard || data;
  const filteredData = Object.assign({}, src);
  if (owner !== '모두') {
    filteredData.accounts = (src.accounts || []).filter(a => {
      const o = a.owner || '모두';
      return o === owner;
    });
    const ownedIds = new Set(filteredData.accounts.map(a => a.id));
    filteredData.holdings = (src.holdings || []).filter(h => ownedIds.has(h.account_id));
  } else {
    // 모두: show everything
    filteredData.accounts = src.accounts || [];
    filteredData.holdings = src.holdings || [];
  }
  render(filteredData);
}'''
if OLD_RENDER_WITH in js:
    js = js.replace(OLD_RENDER_WITH, NEW_RENDER_WITH, 1)
    print('OK 3b. renderWithOwner fixed to use rawDashboard')
else:
    print('WARN 3b. renderWithOwner not found as expected')

# 3c. Fix render() to NOT overwrite rawDashboard (only dashboard)
OLD_RENDER_FN = '''function render(data) {
  dashboard = data;'''
NEW_RENDER_FN = '''function render(data) {
  dashboard = data;
  // rawDashboard is set only by loadDashboard (not by filtered renders)'''
if OLD_RENDER_FN in js:
    js = js.replace(OLD_RENDER_FN, NEW_RENDER_FN, 1)
    print('OK 3c. render() comment added (rawDashboard protection)')
else:
    print('WARN 3c. render() function not found')

# 3d. Fix loadDashboard to set rawDashboard
OLD_LOAD = 'async function loadDashboard() { const data = await api("/api/dashboard"); dashboard = data; renderWithOwner(data, currentOwner); }'
NEW_LOAD = 'async function loadDashboard() { const data = await api("/api/dashboard"); rawDashboard = data; dashboard = data; renderWithOwner(data, currentOwner); }'
if OLD_LOAD in js:
    js = js.replace(OLD_LOAD, NEW_LOAD, 1)
    print('OK 3d. loadDashboard updated to set rawDashboard')
else:
    print('WARN 3d. loadDashboard line not found')

# 3e. Add family tabs management functions and bootstrap
FAMILY_JS = '''

// ── 가족 구성원 탭 동적 렌더링 ────────────────────────────────────────────────
async function loadFamilyMembers() {
  try {
    const res = await api('/api/family-members');
    renderFamilyTabs(res.members || []);
  } catch (e) {
    // fallback to defaults if API fails
    renderFamilyTabs(['아빠', '엄마', '자녀']);
  }
}

function renderFamilyTabs(members) {
  const container = document.getElementById('familyTabs');
  if (!container) return;
  // Keep "모두" tab always first
  const allBtn = '<button type="button" class="family-tab' + (currentOwner === '모두' ? ' active' : '') + '" data-owner="모두">모두</button>';
  const memberBtns = members.map(m =>
    '<button type="button" class="family-tab' + (currentOwner === m ? ' active' : '') + '" data-owner="' + m + '">' + m + '</button>'
  ).join('');
  container.innerHTML = allBtn + memberBtns;
}

function renderFamilyMemberList(members) {
  const list = document.getElementById('familyMemberList');
  if (!list) return;
  if (!members.length) {
    list.innerHTML = '<p style="color:var(--muted);font-size:13px;">구성원이 없습니다.</p>';
    return;
  }
  list.innerHTML = members.map(m => `
    <div class="family-member-row" style="display:flex;align-items:center;gap:8px;">
      <input class="family-member-name-input" type="text" value="${m}" data-original="${m}"
        style="flex:1;font-size:13px;" maxlength="20" />
      <button class="button secondary compact family-rename-btn" data-name="${m}" type="button">수정</button>
      <button class="button text danger compact family-delete-btn" data-name="${m}" type="button">삭제</button>
    </div>
  `).join('');
}

// Family manager dialog open
const _manageFamilyBtn = document.getElementById('manageFamilyBtn');
if (_manageFamilyBtn) {
  _manageFamilyBtn.addEventListener('click', async () => {
    const dlg = document.getElementById('familyManagerDialog');
    if (!dlg) return;
    try {
      const res = await api('/api/family-members');
      renderFamilyMemberList(res.members || []);
    } catch(e) {
      renderFamilyMemberList([]);
    }
    dlg.showModal();
  });
}

// Family member list interactions (rename / delete)
const _familyMemberList = document.getElementById('familyMemberList');
if (_familyMemberList) {
  _familyMemberList.addEventListener('click', async (e) => {
    const renameBtn = e.target.closest('.family-rename-btn');
    const deleteBtn = e.target.closest('.family-delete-btn');

    if (renameBtn) {
      const row = renameBtn.closest('.family-member-row');
      const input = row.querySelector('.family-member-name-input');
      const oldName = renameBtn.dataset.name;
      const newName = (input.value || '').trim();
      if (!newName || newName === oldName) return;
      try {
        const res = await api(`/api/family-members/${encodeURIComponent(oldName)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newName }),
        });
        toast(res.message || '이름을 변경했습니다.');
        if (currentOwner === oldName) currentOwner = newName;
        renderFamilyTabs(res.members || []);
        renderFamilyMemberList(res.members || []);
        await loadDashboard();
      } catch(err) { toast(err.message, true); }
    }

    if (deleteBtn) {
      const name = deleteBtn.dataset.name;
      if (!confirm(`'${name}' 구성원을 삭제할까요? 이 구성원의 계좌는 '미분류'로 이동됩니다.`)) return;
      try {
        const res = await api(`/api/family-members/${encodeURIComponent(name)}`, { method: 'DELETE' });
        toast(res.message || '삭제했습니다.');
        if (currentOwner === name) { currentOwner = '모두'; }
        renderFamilyTabs(res.members || []);
        renderFamilyMemberList(res.members || []);
        await loadDashboard();
      } catch(err) { toast(err.message, true); }
    }
  });
}

// Add new member
const _addMemberBtn = document.getElementById('addMemberBtn');
if (_addMemberBtn) {
  _addMemberBtn.addEventListener('click', async () => {
    const input = document.getElementById('newMemberName');
    const name = (input?.value || '').trim();
    if (!name) { toast('이름을 입력해 주세요.', true); return; }
    try {
      const res = await api('/api/family-members', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      toast(res.message || '추가했습니다.');
      if (input) input.value = '';
      renderFamilyTabs(res.members || []);
      renderFamilyMemberList(res.members || []);
    } catch(err) { toast(err.message, true); }
  });
}

// Enter key in new member input
document.getElementById('newMemberName')?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('addMemberBtn')?.click();
});
'''

if 'loadFamilyMembers' not in js:
    # Insert before the PWA service worker section
    SW_MARKER = "// PWA 서비스 워커 등록"
    if SW_MARKER in js:
        js = js.replace(SW_MARKER, FAMILY_JS + '\n' + SW_MARKER, 1)
        print('OK 3e. Family management JS added')
    else:
        js += FAMILY_JS
        print('OK 3e. Family management JS appended to end')
else:
    print('INFO 3e. loadFamilyMembers already exists')

# 3f. Update bootstrap to also load family members
OLD_BOOTSTRAP = 'async function bootstrap() { await loadDashboard().catch((error) => toast(error.message, true)); await loadMarkets(); await loadAssetRecords(); }'
NEW_BOOTSTRAP = 'async function bootstrap() { await loadFamilyMembers(); await loadDashboard().catch((error) => toast(error.message, true)); await loadMarkets(); await loadAssetRecords(); }'
if OLD_BOOTSTRAP in js:
    js = js.replace(OLD_BOOTSTRAP, NEW_BOOTSTRAP, 1)
    print('OK 3f. bootstrap updated to load family members')
else:
    print('WARN 3f. bootstrap function not found')

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

# ──────────────────────────────────────────────────────────────────────────────
# 4. wealth-overrides.css – add family member row style
# ──────────────────────────────────────────────────────────────────────────────
CSS_PATH = 'app/static/wealth-overrides.css'
with open(CSS_PATH, 'r', encoding='utf-8') as f:
    css = f.read()

MEMBER_CSS = '''
/* ── 가족 구성원 관리 행 ──────────────────────────────────────────────────── */
.family-member-row input {
  background: #111a33;
  color: #d8e2ff;
  border: 1px solid #27365c;
  border-radius: 6px;
  padding: 5px 10px;
}
.family-member-row input:focus {
  border-color: #7957e8;
  outline: none;
}
'''
if 'family-member-row' not in css:
    with open(CSS_PATH, 'a', encoding='utf-8') as f:
        f.write(MEMBER_CSS)
    print('OK 4. Family member row CSS added')
else:
    print('INFO 4. Family member row CSS already exists')

print('\nAll patches complete!')
