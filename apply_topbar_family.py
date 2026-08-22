#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_topbar_family_and_records.py
1. index.html  – topbar에 가족 탭 추가, assetRecordDialog에 owner 필드 추가
2. wealth.js   – selectOwner() 통합 함수, 탑바 탭 연동,
                 snapshot/assetRecord submit에 owner 포함,
                 openAssetRecordDialog owner 자동 설정
3. main.py     – snapshot endpoint에 owner 저장
"""

# ──────────────────────────────────────────────────────────────────────────────
# 1. index.html
# ──────────────────────────────────────────────────────────────────────────────
HTML_PATH = 'app/static/index.html'
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# 1a. 탑바에 가족 탭 추가 (브랜드와 top-actions 사이)
OLD_TOPBAR_BRAND = (
    '        <div class="topbar-brand-wrap">\n'
    '          <a class="brand" href="/" aria-label="시작 화면">W</a>\n'
    '          <div class="title"><p>Human Index INVESTMENT</p><h1>인간지표의 투자 대시보드</h1></div>\n'
    '        </div>'
)
NEW_TOPBAR_BRAND = (
    '        <div class="topbar-brand-wrap">\n'
    '          <a class="brand" href="/" aria-label="시작 화면">W</a>\n'
    '          <div class="title"><p>Human Index INVESTMENT</p><h1>인간지표의 투자 대시보드</h1></div>\n'
    '          <div class="family-tabs topbar-family-tabs" id="topbarFamilyTabs" style="display:flex;gap:0.3rem;align-items:center;flex-wrap:wrap;">\n'
    '            <button type="button" class="family-tab active" data-owner="모두">모두</button>\n'
    '          </div>\n'
    '        </div>'
)
if 'topbarFamilyTabs' not in html:
    if OLD_TOPBAR_BRAND in html:
        html = html.replace(OLD_TOPBAR_BRAND, NEW_TOPBAR_BRAND, 1)
        print('OK 1a. Topbar family tabs added')
    else:
        print('WARN 1a. Topbar brand-wrap not found')
else:
    print('INFO 1a. Topbar family tabs already exist')

# 1b. assetRecordDialog에 owner select 추가
OLD_AR_MEMO = '<label>메모<input name="memo" /></label></div>'
NEW_AR_MEMO = (
    '<label>메모<input name="memo" /></label>'
    '<label>구성원<select name="owner">'
    '<option value="모두">모두</option>'
    '<option value="아빠">아빠</option>'
    '<option value="엄마">엄마</option>'
    '<option value="자녀">자녀</option>'
    '</select></label></div>'
)
if 'assetRecordForm' in html and OLD_AR_MEMO in html:
    html = html.replace(OLD_AR_MEMO, NEW_AR_MEMO, 1)
    print('OK 1b. owner select added to assetRecordDialog')
else:
    print('WARN 1b. assetRecordDialog memo label not found')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

# ──────────────────────────────────────────────────────────────────────────────
# 2. wealth.js
# ──────────────────────────────────────────────────────────────────────────────
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 2a. Replace the family tab click handler with selectOwner() unified function
OLD_FAM_CLICK = '''// ── 가족 탭 클릭 핸들러 ─────────────────────────────────────────────────────
document.addEventListener('click', (e) => {
  const tab = e.target.closest('#familyTabs .family-tab');
  if (!tab) return;
  currentOwner = tab.dataset.owner || '모두';
  document.querySelectorAll('#familyTabs .family-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  if (dashboard) renderWithOwner(dashboard, currentOwner);
});'''

NEW_FAM_CLICK = '''// ── 가족 구성원 선택 – 탑바 + ACCOUNTS 탭 동기화 ─────────────────────────────
function selectOwner(owner) {
  currentOwner = owner || '모두';
  // ACCOUNTS 탭 업데이트
  document.querySelectorAll('#familyTabs .family-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.owner === currentOwner);
  });
  // 탑바 탭 업데이트
  document.querySelectorAll('#topbarFamilyTabs .family-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.owner === currentOwner);
  });
  if (rawDashboard) renderWithOwner(rawDashboard, currentOwner);
}

document.addEventListener('click', (e) => {
  // ACCOUNTS 탭
  const accountsTab = e.target.closest('#familyTabs .family-tab');
  if (accountsTab) { selectOwner(accountsTab.dataset.owner); return; }
  // 탑바 탭
  const topbarTab = e.target.closest('#topbarFamilyTabs .family-tab');
  if (topbarTab) { selectOwner(topbarTab.dataset.owner); return; }
});'''

if 'selectOwner' not in js:
    if OLD_FAM_CLICK in js:
        js = js.replace(OLD_FAM_CLICK, NEW_FAM_CLICK, 1)
        print('OK 2a. selectOwner() added, both tab sets wired')
    else:
        print('WARN 2a. Old family tab click handler not found')
else:
    print('INFO 2a. selectOwner already exists')

# 2b. Update renderFamilyTabs to ALSO update topbarFamilyTabs
OLD_RENDER_TABS = '''function renderFamilyTabs(members) {
  const container = document.getElementById('familyTabs');
  if (!container) return;
  // Keep "모두" tab always first
  const allBtn = '<button type="button" class="family-tab' + (currentOwner === '모두' ? ' active' : '') + '" data-owner="모두">모두</button>';
  const memberBtns = members.map(m =>
    '<button type="button" class="family-tab' + (currentOwner === m ? ' active' : '') + '" data-owner="' + m + '">' + m + '</button>'
  ).join('');
  container.innerHTML = allBtn + memberBtns;
}'''

NEW_RENDER_TABS = '''function renderFamilyTabs(members) {
  const allBtn = (containerId) => '<button type="button" class="family-tab' + (currentOwner === '모두' ? ' active' : '') + '" data-owner="모두">모두</button>';
  const memberBtns = members.map(m =>
    '<button type="button" class="family-tab' + (currentOwner === m ? ' active' : '') + '" data-owner="' + m + '">' + m + '</button>'
  ).join('');
  const inner = allBtn() + memberBtns;
  // ACCOUNTS 탭
  const container = document.getElementById('familyTabs');
  if (container) container.innerHTML = inner;
  // 탑바 탭
  const topbar = document.getElementById('topbarFamilyTabs');
  if (topbar) topbar.innerHTML = inner;
}'''

if OLD_RENDER_TABS in js:
    js = js.replace(OLD_RENDER_TABS, NEW_RENDER_TABS, 1)
    print('OK 2b. renderFamilyTabs updated to sync topbar tabs')
else:
    print('WARN 2b. renderFamilyTabs not found')

# 2c. Update openAssetRecordDialog to pre-fill owner
OLD_OPEN_AR = '''function openAssetRecordDialog(record = null) {
  const form = $("#assetRecordForm");
  form.reset();
  form.dataset.recordId = record?.id || "";
  $("#assetRecordDialogTitle").textContent = record ? "자산기록 수정" : "자산기록 추가";
  form.date.value = record?.date || new Date().toISOString().slice(0, 10);
  form.total_value_krw.value = record?.total_value_krw ?? "";
  form.total_cost_krw.value = record?.total_cost_krw ?? "";
  form.profit_krw.value = record?.profit_krw ?? "";
  form.return_rate.value = record?.return_rate ?? "";
  form.day_profit_krw.value = record?.day_profit_krw ?? "";
  form.krw_value_krw.value = record?.krw_value_krw ?? "";
  form.usd_value_krw.value = record?.usd_value_krw ?? "";
  form.holding_count.value = record?.holding_count ?? "";
  form.memo.value = record?.memo ?? "";
  $("#assetRecordDialog").showModal();
}'''

NEW_OPEN_AR = '''function openAssetRecordDialog(record = null) {
  const form = $("#assetRecordForm");
  form.reset();
  form.dataset.recordId = record?.id || "";
  $("#assetRecordDialogTitle").textContent = record ? "자산기록 수정" : "자산기록 추가";
  form.date.value = record?.date || new Date().toISOString().slice(0, 10);
  form.total_value_krw.value = record?.total_value_krw ?? "";
  form.total_cost_krw.value = record?.total_cost_krw ?? "";
  form.profit_krw.value = record?.profit_krw ?? "";
  form.return_rate.value = record?.return_rate ?? "";
  form.day_profit_krw.value = record?.day_profit_krw ?? "";
  form.krw_value_krw.value = record?.krw_value_krw ?? "";
  form.usd_value_krw.value = record?.usd_value_krw ?? "";
  form.holding_count.value = record?.holding_count ?? "";
  form.memo.value = record?.memo ?? "";
  // owner: 기존 레코드의 owner 또는 현재 선택된 구성원
  if (form.owner) form.owner.value = record?.owner || currentOwner || "모두";
  $("#assetRecordDialog").showModal();
}'''

if OLD_OPEN_AR in js:
    js = js.replace(OLD_OPEN_AR, NEW_OPEN_AR, 1)
    print('OK 2c. openAssetRecordDialog updated with owner pre-fill')
else:
    print('WARN 2c. openAssetRecordDialog not found')

# 2d. Update assetRecordForm submit to always include owner
OLD_AR_SUBMIT = '''  payload.memo = payload.memo || "";
  try {
    const method = form.dataset.recordId ? "PUT" : "POST";
    const url = form.dataset.recordId ? `/api/asset-records/${form.dataset.recordId}` : "/api/asset-records";
    const result = await api(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    form.closest("dialog").close();
    toast(result.message);
    await loadAssetRecords();'''

NEW_AR_SUBMIT = '''  payload.memo = payload.memo || "";
  payload.owner = payload.owner || currentOwner || "모두";
  try {
    const method = form.dataset.recordId ? "PUT" : "POST";
    const url = form.dataset.recordId ? `/api/asset-records/${form.dataset.recordId}` : "/api/asset-records";
    const result = await api(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    form.closest("dialog").close();
    toast(result.message);
    await loadAssetRecords(currentOwner);'''

if OLD_AR_SUBMIT in js:
    js = js.replace(OLD_AR_SUBMIT, NEW_AR_SUBMIT, 1)
    print('OK 2d. assetRecordForm submit updated with owner')
else:
    print('WARN 2d. assetRecordForm submit block not found')

# 2e. Update snapshot button to include owner and reload with currentOwner
OLD_SNAPSHOT_END = ', async () => { await loadDashboard(); await loadAssetRecords(); }));'
NEW_SNAPSHOT_END = ', async () => { await loadDashboard(); await loadAssetRecords(currentOwner); }));'
if OLD_SNAPSHOT_END in js:
    js = js.replace(OLD_SNAPSHOT_END, NEW_SNAPSHOT_END, 1)
    print('OK 2e. snapshot callback updated to pass currentOwner')
else:
    print('WARN 2e. snapshot callback not found')

# 2f. Update snapshot API call to include owner
OLD_SNAPSHOT_MEMO = '      holding_count: s.holding_count, source: "snapshot", memo: "수동 스냅샷"'
NEW_SNAPSHOT_MEMO = '      holding_count: s.holding_count, source: "snapshot", memo: "수동 스냅샷", owner: currentOwner || "모두"'
if OLD_SNAPSHOT_MEMO in js:
    js = js.replace(OLD_SNAPSHOT_MEMO, NEW_SNAPSHOT_MEMO, 1)
    print('OK 2f. snapshot payload includes owner')
else:
    print('WARN 2f. snapshot memo line not found')

# 2g. Update renderWithOwner to dynamically update owner select options in dialogs
#     (so new members added later appear in assetRecordDialog)
# We add an extra step after renderFamilyTabs to update select options
OLD_LOAD_FAM = '''async function loadFamilyMembers() {
  try {
    const res = await api('/api/family-members');
    renderFamilyTabs(res.members || []);
  } catch (e) {
    // fallback to defaults if API fails
    renderFamilyTabs(['아빠', '엄마', '자녀']);
  }
}'''

NEW_LOAD_FAM = '''async function loadFamilyMembers() {
  try {
    const res = await api('/api/family-members');
    renderFamilyTabs(res.members || []);
    updateOwnerSelects(res.members || []);
  } catch (e) {
    renderFamilyTabs(['아빠', '엄마', '자녀']);
    updateOwnerSelects(['아빠', '엄마', '자녀']);
  }
}

// 다이얼로그 내 owner <select>들을 현재 구성원 목록으로 동기화
function updateOwnerSelects(members) {
  const opts = ['<option value="모두">모두</option>']
    .concat(members.map(m => `<option value="${m}">${m}</option>`))
    .join('');
  document.querySelectorAll('select[name="owner"]').forEach(sel => {
    const prev = sel.value;
    sel.innerHTML = opts;
    if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
  });
}'''

if 'updateOwnerSelects' not in js:
    if OLD_LOAD_FAM in js:
        js = js.replace(OLD_LOAD_FAM, NEW_LOAD_FAM, 1)
        print('OK 2g. loadFamilyMembers updated with updateOwnerSelects')
    else:
        print('WARN 2g. loadFamilyMembers not found')
else:
    print('INFO 2g. updateOwnerSelects already exists')

# 2h. Also call updateOwnerSelects when members change (in addMemberBtn, rename, delete handlers)
OLD_RENDER_AFTER_ADD = '''      renderFamilyTabs(res.members || []);
      renderFamilyMemberList(res.members || []);
    } catch(err) { toast(err.message, true); }
    return;
  }

  // 이름 변경 버튼'''
NEW_RENDER_AFTER_ADD = '''      renderFamilyTabs(res.members || []);
      updateOwnerSelects(res.members || []);
      renderFamilyMemberList(res.members || []);
    } catch(err) { toast(err.message, true); }
    return;
  }

  // 이름 변경 버튼'''
if OLD_RENDER_AFTER_ADD in js:
    js = js.replace(OLD_RENDER_AFTER_ADD, NEW_RENDER_AFTER_ADD, 1)
    print('OK 2h. add member handler updates owner selects')
else:
    print('WARN 2h. add member handler block not found')

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)
print()

# ──────────────────────────────────────────────────────────────────────────────
# 3. main.py  – snapshot에 owner 저장
# ──────────────────────────────────────────────────────────────────────────────
MAIN_PATH = 'app/main.py'
with open(MAIN_PATH, 'r', encoding='utf-8') as f:
    main = f.read()

# snapshot endpoint – add owner to the record
OLD_SNAP_BODY = '''    record = upsert_asset_record({
        "date": today,'''
NEW_SNAP_BODY = '''    record = upsert_asset_record({
        "date": today,
        "owner": "모두",  # snapshot is always for all (filtered view saves via manual record)'''

# Actually snapshot is called without owner info from server side.
# Let's add owner param to the snapshot endpoint
OLD_SNAP_DEF = '@app.post("/api/asset-records/snapshot")\nasync def snapshot_asset_record() -> dict:'
NEW_SNAP_DEF = '@app.post("/api/asset-records/snapshot")\nasync def snapshot_asset_record(request: Request) -> dict:'
if OLD_SNAP_DEF in main:
    main = main.replace(OLD_SNAP_DEF, NEW_SNAP_DEF, 1)
    print('OK 3a. snapshot endpoint accepts request body')
else:
    print('WARN 3a. snapshot def not found')

# Add owner extraction in snapshot body
OLD_SNAP_UPSERT = '    record = upsert_asset_record({'
# Find after snapshot_asset_record function start
snap_idx = main.find('async def snapshot_asset_record')
if snap_idx != -1:
    upsert_idx = main.find('    record = upsert_asset_record({', snap_idx)
    if upsert_idx != -1 and 'owner_snap' not in main[snap_idx:snap_idx+500]:
        owner_extract = '    try:\n        body = await request.json()\n        owner_snap = body.get("owner", "모두") or "모두"\n    except Exception:\n        owner_snap = "모두"\n    '
        main = main[:upsert_idx] + owner_extract + main[upsert_idx:]
        print('OK 3b. snapshot extracts owner from request body')
    else:
        print('INFO 3b. owner already in snapshot or upsert not found')
else:
    print('WARN 3b. snapshot function not found')

# Also update PUT /api/asset-records to save owner field
OLD_PUT_AR = '''@app.put("/api/asset-records/{record_id}")
async def update_asset_record(record_id: str, payload: dict) -> dict:
    payload["id"] = record_id
    record = upsert_asset_record(payload)'''
NEW_PUT_AR = '''@app.put("/api/asset-records/{record_id}")
async def update_asset_record(record_id: str, payload: dict) -> dict:
    payload["id"] = record_id
    if "owner" not in payload or not payload["owner"]:
        payload["owner"] = "모두"
    record = upsert_asset_record(payload)'''
if OLD_PUT_AR in main:
    main = main.replace(OLD_PUT_AR, NEW_PUT_AR, 1)
    print('OK 3c. PUT /api/asset-records saves owner')
else:
    print('WARN 3c. PUT asset-records not found')

with open(MAIN_PATH, 'w', encoding='utf-8') as f:
    f.write(main)

# ──────────────────────────────────────────────────────────────────────────────
# 4. CSS – 탑바 가족 탭 스타일 (탑바에서 더 작게 표시)
# ──────────────────────────────────────────────────────────────────────────────
CSS_PATH = 'app/static/wealth-overrides.css'
with open(CSS_PATH, 'r', encoding='utf-8') as f:
    css = f.read()

TOPBAR_CSS = '''
/* ── 탑바 가족 탭 (더 컴팩트하게) ─────────────────────────────────────────── */
.topbar-family-tabs {
  margin-left: 12px;
}
.topbar-family-tabs .family-tab {
  padding: 3px 10px;
  font-size: 12px;
}
.topbar-brand-wrap {
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: wrap;
}
'''
if 'topbar-family-tabs' not in css:
    with open(CSS_PATH, 'a', encoding='utf-8') as f:
        f.write(TOPBAR_CSS)
    print('OK 4. Topbar family tab CSS added')
else:
    print('INFO 4. Topbar CSS already exists')

print('\nAll done!')
