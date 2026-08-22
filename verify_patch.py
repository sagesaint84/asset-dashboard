import re

# Check main.py has POST endpoint
with open('app/main.py', 'r', encoding='utf-8') as f:
    mp = f.read()
print('POST /api/accounts in main.py:', 'app.post("/api/accounts")' in mp)
print('create_account function:', 'async def create_account' in mp)

# Check wealth.js has account add handlers
with open('app/static/wealth.js', 'r', encoding='utf-8') as f:
    wj = f.read()
print('addAccountBtn handler:', '_addAccountBtn' in wj)
print('accountAddForm submit:', 'accountAddForm' in wj)
print('POST /api/accounts call:', '/api/accounts' in wj)
