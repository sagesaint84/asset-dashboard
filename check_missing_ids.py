#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

with open('app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('app/static/wealth.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Find all $("#xyz") or document.getElementById("xyz") in wealth.js
id_matches = re.findall(r'\$\(["\']#([a-zA-Z0-9_-]+)["\']\)', js)
id_matches += re.findall(r'document\.getElementById\(["\']([a-zA-Z0-9_-]+)["\']\)', js)

missing_ids = set()
for eid in set(id_matches):
    if f'id="{eid}"' not in html and f"id='{eid}'" not in html:
        missing_ids.add(eid)

print("Missing element IDs in index.html:")
for mid in sorted(missing_ids):
    print(" -", mid)
