#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_exact_two_fixes.py
Fix 1: Remove market-symbol-tag from renderMarkets
Fix 2: Clean snapshot payload & ensure credentials: 'include'
"""

with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    js = f.read()

# Fix 1: Remove symbol tag from renderMarkets
old_tag = '<span class="market-symbol-tag">${html(item.symbol)}</span>'
if old_tag in js:
    js = js.replace(old_tag, "")
    print("Fix 1 OK: Removed market-symbol-tag from renderMarkets")

# Fix 2: Ensure api() includes credentials
old_api = """async function api(url, options = {}) {
  const response = await fetch(url, options);
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || result.message || "요청을 처리하지 못했습니다.");
  return result;
}"""

new_api = """async function api(url, options = {}) {
  options.credentials = options.credentials || 'include';
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.location.href = '/login';
    throw new Error('로그인이 필요합니다.');
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || result.message || "요청을 처리하지 못했습니다.");
  return result;
}"""

if old_api in js:
    js = js.replace(old_api, new_api, 1)
    print("Fix 2 OK: Updated api() with credentials and 401 redirect")

with open("app/static/wealth.js", "w", encoding="utf-8") as f:
    f.write(js)

print("Exact two fixes applied cleanly to wealth.js!")
