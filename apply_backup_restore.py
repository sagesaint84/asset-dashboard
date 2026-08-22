#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_backup_restore.py
1. index.html – 로컬 데이터 저장하기 / 불러오기 버튼 추가 + 숨김 file input
2. main.py    – GET /api/export  (전체 데이터 ZIP/JSON 다운로드)
              – POST /api/import-backup (JSON 파일 업로드 → 데이터 복원)
3. wealth.js  – exportButton, importBackupBtn 핸들러
"""

# ── 1. index.html ──────────────────────────────────────────────────────────────
HTML_PATH = 'app/static/index.html'
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

OLD_BOTTOM = (
    '    <div class="bottom-actions" style="text-align:center; margin-top:20px;">\n'
    '  <button id="clearButton" class="button text danger" type="button">로컬 데이터 지우기</button>\n'
    '</div>'
)
NEW_BOTTOM = (
    '    <div class="bottom-actions" style="text-align:center; margin-top:20px; display:flex; flex-wrap:wrap; gap:8px; justify-content:center;">\n'
    '  <button id="exportButton" class="button secondary" type="button">💾 데이터 저장하기</button>\n'
    '  <button id="importBackupBtn" class="button secondary" type="button">📂 데이터 불러오기</button>\n'
    '  <button id="clearButton" class="button text danger" type="button">로컬 데이터 지우기</button>\n'
    '  <input id="importBackupFile" type="file" accept=".json" style="display:none;" />\n'
    '</div>'
)

if 'exportButton' not in html:
    if OLD_BOTTOM in html:
        html = html.replace(OLD_BOTTOM, NEW_BOTTOM, 1)
        print('OK 1. Export/Import buttons added to HTML')
    else:
        print('WARN 1. Bottom actions block not found')
else:
    print('INFO 1. Buttons already exist')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

# ── 2. main.py ─────────────────────────────────────────────────────────────────
MAIN_PATH = 'app/main.py'
with open(MAIN_PATH, 'r', encoding='utf-8') as f:
    main = f.read()

BACKUP_ENDPOINTS = '''

@app.get("/api/export")
async def export_data():
    """포트폴리오 전체 데이터를 JSON 파일로 다운로드"""
    from fastapi.responses import JSONResponse
    import json
    from app.services.portfolio import read_portfolio
    from app.services.asset_records import read_asset_records

    bundle = {
        "version": "1.0",
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "portfolio": read_portfolio(),
        "asset_records": read_asset_records(),
    }
    content = json.dumps(bundle, ensure_ascii=False, indent=2)
    from starlette.responses import Response
    filename = f"dashboard_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/import-backup")
async def import_backup(file: UploadFile = File(...)) -> dict:
    """백업 JSON 파일에서 데이터 복원"""
    import json
    from app.services.portfolio import write_portfolio
    from app.services.asset_records import write_asset_records

    try:
        raw = await file.read()
        bundle = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(400, f"JSON 파싱 실패: {exc}") from exc

    if "portfolio" not in bundle and "asset_records" not in bundle:
        raise HTTPException(400, "유효한 백업 파일이 아닙니다.")

    msgs = []
    if "portfolio" in bundle:
        write_portfolio(bundle["portfolio"])
        msgs.append("포트폴리오")
    if "asset_records" in bundle:
        write_asset_records(bundle["asset_records"])
        msgs.append("자산기록")

    return {"message": f"{', '.join(msgs)} 데이터를 복원했습니다."}
'''

if '/api/export' not in main:
    # Find a good insertion point (before last line or before sync endpoints)
    insert_marker = '\n@app.post("/api/demo")'
    if insert_marker in main:
        main = main.replace(insert_marker, BACKUP_ENDPOINTS + insert_marker, 1)
        print('OK 2. Export/Import endpoints added to main.py')
    else:
        # Append before end
        main = main.rstrip() + '\n' + BACKUP_ENDPOINTS + '\n'
        print('OK 2. Export/Import endpoints appended to main.py')
else:
    print('INFO 2. Endpoints already exist')

# Ensure UploadFile and File are imported
if 'UploadFile' not in main:
    main = main.replace(
        'from fastapi import FastAPI',
        'from fastapi import FastAPI, UploadFile, File',
        1
    )
    print('OK 2b. UploadFile/File added to imports')
else:
    print('INFO 2b. UploadFile already imported')

with open(MAIN_PATH, 'w', encoding='utf-8') as f:
    f.write(main)

# ── 3. wealth.js ───────────────────────────────────────────────────────────────
JS_PATH = 'app/static/wealth.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

EXPORT_IMPORT_JS = '''
// ── 데이터 저장 / 불러오기 ───────────────────────────────────────────────────
document.getElementById('exportButton')?.addEventListener('click', () => {
  window.location.href = '/api/export';
});

document.getElementById('importBackupBtn')?.addEventListener('click', () => {
  document.getElementById('importBackupFile')?.click();
});

document.getElementById('importBackupFile')?.addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  if (!confirm(`'${file.name}' 파일로 데이터를 복원할까요?\\n현재 데이터는 덮어쓰입니다.`)) {
    e.target.value = '';
    return;
  }
  const btn = document.getElementById('importBackupBtn');
  btn && (btn.disabled = true);
  try {
    const formData = new FormData();
    formData.append('file', file);
    const result = await api('/api/import-backup', { method: 'POST', body: formData });
    toast(result.message || '데이터를 복원했습니다.');
    await loadDashboard();
    await loadAssetRecords(currentOwner);
  } catch (err) {
    toast(err.message, true);
  } finally {
    e.target.value = '';
    btn && (btn.disabled = false);
  }
});
'''

if 'exportButton' not in js:
    # Insert before PWA service worker registration
    SW_MARKER = '// PWA 서비스 워커 등록'
    if SW_MARKER in js:
        js = js.replace(SW_MARKER, EXPORT_IMPORT_JS + '\n' + SW_MARKER, 1)
        print('OK 3. Export/Import JS handlers added')
    else:
        js = js.rstrip() + '\n' + EXPORT_IMPORT_JS + '\n'
        print('OK 3. Export/Import JS appended')
else:
    print('INFO 3. JS handlers already exist')

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print('\nAll done!')
