#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_auth_and_api.py
- Strip whitespace from DASHBOARD_USERNAME and DASHBOARD_PASSWORD in main.py
- Ensure 401 redirects to /login in wealth.js
- Handle local auth gracefully
"""

# 1. Update app/main.py
with open("app/main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

old_auth_vars = """AUTH_USERNAME = os.getenv("DASHBOARD_USERNAME", "")
AUTH_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "")"""

new_auth_vars = """AUTH_USERNAME = os.getenv("DASHBOARD_USERNAME", "").strip()
AUTH_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "").strip()
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "").strip() or "asset_dashboard_secret_key_default" """

if old_auth_vars in main_code:
    main_code = main_code.replace(old_auth_vars, new_auth_vars, 1)
    print("OK: main.py auth env vars stripped")

with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(main_code)


# 2. Update wealth.js api() function
with open("app/static/wealth.js", "r", encoding="utf-8") as f:
    js = f.read()

old_api_fn = """async function api(url, options = {}) {
  const response = await fetch(url, options);
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || result.message || "요청을 처리하지 못했습니다.");
  return result;
}"""

new_api_fn = """async function api(url, options = {}) {
  options.credentials = options.credentials || 'include';
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("로그인이 필요합니다. 로그인 페이지로 이동합니다.");
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || result.message || "요청을 처리하지 못했습니다.");
  return result;
}"""

if old_api_fn in js:
    js = js.replace(old_api_fn, new_api_fn, 1)
    print("OK: wealth.js api() updated with 401 redirect")

with open("app/static/wealth.js", "w", encoding="utf-8") as f:
    f.write(js)

print("Auth and API fixes applied!")
