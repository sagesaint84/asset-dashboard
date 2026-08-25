#!/usr/bin/env python3
# -*- coding: utf-8 -*-
with open('app/static/wealth.js', 'r', encoding='utf-8') as f:
    js = f.read()

lines = js.splitlines()
print(f'Total lines: {len(lines)}')

for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith('$(') or s.startswith('document.getElementById(') or s.startswith('document.querySelector('):
        print(f'Line {i+1}: {s[:90]}')
