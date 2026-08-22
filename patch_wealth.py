#!/usr/bin/env python3
# patch_wealth.py - Adds account add button JS handlers to wealth.js

path = r'c:\Users\USER\Desktop\asset-dashboard-clean\app\static\wealth.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'accountAddForm' in content:
    print('Already patched, skipping.')
else:
    # The new code block to insert after the holdingsBody listener line
    insertion = """
// ── 계좌 추가 버튼 ───────────────────────────────────────────────────────────
const _addAccountBtn = document.getElementById('addAccountBtn');
if (_addAccountBtn) {
  _addAccountBtn.addEventListener('click', () => {
    const dlg = document.getElementById('accountAddDialog');
    if (dlg) {
      document.getElementById('accountAddForm')?.reset();
      dlg.showModal();
    }
  });
}

document.getElementById('accountAddForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const payload = {
    broker: form.broker.value.trim(),
    account_name: form.account_name.value.trim(),
    owner: form.owner.value,
  };
  try {
    const result = await api('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    form.closest('dialog')?.close();
    toast(result.message || '계좌가 추가되었습니다.');
    await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  }
});
"""

    # Find insertion point: after the heatmap tooltip comment section starts
    marker = '// 히트맵 툴팁 및 클릭 필터 상호작용'
    idx = content.find(marker)
    if idx == -1:
        print('ERROR: marker not found')
    else:
        content = content[:idx] + insertion + '\n' + content[idx:]
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('SUCCESS: wealth.js patched.')
