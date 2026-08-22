with open('app/static/wealth.js', encoding='utf-8') as f: js = f.read()
with open('app/static/index.html', encoding='utf-8') as f: html = f.read()
with open('app/main.py', encoding='utf-8') as f: main = f.read()

checks = [
    ('topbarFamilyTabs in HTML',          'id="topbarFamilyTabs"' in html),
    ('owner select in assetRecordDialog', 'assetRecordForm' in html and 'name="owner"' in html),
    ('selectOwner() function',            'function selectOwner' in js),
    ('topbar tab click wired',            'topbarFamilyTabs .family-tab' in js),
    ('renderFamilyTabs syncs topbar',     'topbarFamilyTabs' in js),
    ('updateOwnerSelects function',       'function updateOwnerSelects' in js),
    ('openAssetRecordDialog owner',       "record?.owner || currentOwner" in js),
    ('assetRecord submit owner',          "payload.owner = payload.owner" in js),
    ('snapshot payload owner',            "owner: currentOwner" in js),
    ('snapshot reload currentOwner',      'loadAssetRecords(currentOwner)' in js),
    ('GET asset-records owner filter',    'if owner and owner' in main),
    ('PUT asset-records saves owner',     'payload["owner"]' in main),
]
ok = 0; fail = 0
for name, result in checks:
    mark = 'OK  ' if result else 'MISS'
    if result: ok += 1
    else: fail += 1
    print(f'[{mark}] {name}')
print(f'\n{ok}/{ok+fail} checks passed')
