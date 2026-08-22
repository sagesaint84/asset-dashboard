#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_family_dialog.py
- Move familyManagerDialog BEFORE the <script> tag
- Remove stray </dialog> at line 289
- Use event delegation in JS (robust against dynamic content)
"""

# ─── Fix index.html ────────────────────────────────────────────────────────────
HTML_PATH = 'app/static/index.html'
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Remove stray </dialog>
STRAY = '    </dialog>\n\n    <div id="heatmapTooltip"'
FIXED = '    <div id="heatmapTooltip"'
if STRAY in html:
    html = html.replace(STRAY, FIXED, 1)
    print('OK: removed stray </dialog>')
else:
    print('WARN: stray </dialog> not found (may already be fixed)')

# 2. Extract the familyManagerDialog block (currently after <script>)
DIALOG_START = '\n    <!-- 가족 구성원 관리 다이얼로그 -->'
DIALOG_END = '    </dialog>\n\n  </body>'
idx_start = html.find(DIALOG_START)
idx_end = html.find(DIALOG_END)
if idx_start != -1 and idx_end != -1:
    dialog_block = html[idx_start:idx_end + len('    </dialog>')]
    # Remove it from after the script
    html = html[:idx_start] + '\n\n  </body>' + html[idx_end + len(DIALOG_END):]
    # Insert it before the <script> tag
    SCRIPT_TAG = '<script src="/static/wealth.js'
    html = html.replace(SCRIPT_TAG, dialog_block + '\n\n' + SCRIPT_TAG, 1)
    print('OK: familyManagerDialog moved before <script> tag')
else:
    print(f'WARN: dialog block not found (start={idx_start}, end={idx_end})')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

# ─── Fix wealth.js – use event delegation on document for dialog buttons ────────
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# Replace the static element-binding approach with event delegation
OLD_MANAGE_BTN = '''// Family manager dialog open
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
});'''

NEW_MANAGE_BTN = '''// ── 가족 구성원 관리 – 이벤트 위임으로 구현 (dialog 내부 버튼 안전하게 처리) ──
async function openFamilyManager() {
  const dlg = document.getElementById('familyManagerDialog');
  if (!dlg) return;
  try {
    const res = await api('/api/family-members');
    renderFamilyMemberList(res.members || []);
  } catch(e) {
    renderFamilyMemberList([]);
  }
  dlg.showModal();
}

document.addEventListener('click', async (e) => {
  // 관리 버튼 열기
  if (e.target.closest('#manageFamilyBtn')) {
    await openFamilyManager();
    return;
  }

  // 추가 버튼
  if (e.target.closest('#addMemberBtn')) {
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
    return;
  }

  // 이름 변경 버튼
  const renameBtn = e.target.closest('.family-rename-btn');
  if (renameBtn) {
    const row = renameBtn.closest('.family-member-row');
    const input = row?.querySelector('.family-member-name-input');
    const oldName = renameBtn.dataset.name;
    const newName = (input?.value || '').trim();
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
    return;
  }

  // 삭제 버튼
  const deleteBtn = e.target.closest('.family-delete-btn');
  if (deleteBtn) {
    const name = deleteBtn.dataset.name;
    if (!confirm(`'${name}' 구성원을 삭제할까요?`)) return;
    try {
      const res = await api(`/api/family-members/${encodeURIComponent(name)}`, { method: 'DELETE' });
      toast(res.message || '삭제했습니다.');
      if (currentOwner === name) currentOwner = '모두';
      renderFamilyTabs(res.members || []);
      renderFamilyMemberList(res.members || []);
      await loadDashboard();
    } catch(err) { toast(err.message, true); }
    return;
  }
});

// Enter 키로 구성원 추가
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && document.activeElement?.id === 'newMemberName') {
    document.getElementById('addMemberBtn')?.click();
  }
});'''

if OLD_MANAGE_BTN in js:
    js = js.replace(OLD_MANAGE_BTN, NEW_MANAGE_BTN, 1)
    print('OK: wealth.js family manager replaced with event delegation')
else:
    print('WARN: old manage btn block not found exactly')
    # Try partial match
    if '_manageFamilyBtn' in js and '_addMemberBtn' in js:
        # Find the section and replace
        start = js.find('// Family manager dialog open')
        end = js.find("  if (e.key === 'Enter') document.getElementById('addMemberBtn')?.click();\n});")
        if start != -1 and end != -1:
            end += len("  if (e.key === 'Enter') document.getElementById('addMemberBtn')?.click();\n});")
            js = js[:start] + NEW_MANAGE_BTN + js[end:]
            print('OK: wealth.js family manager replaced (fallback method)')
        else:
            print(f'WARN: section bounds not found (start={start}, end={end})')
    else:
        print('WARN: family manager code not found at all')

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print('\nFix complete!')
