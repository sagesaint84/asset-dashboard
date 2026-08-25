#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_backend_extensions.py
1. Update app/services/portfolio.py:
   - Calculate sector_classifications in get_dashboard()
   - Return sector_classifications
2. Update app/main.py:
   - Add sector field to HoldingCreate model
   - Add GET /api/stock-chart/{code} endpoint
   - Remove startup TossOpenAPI call
"""

PORTFOLIO_PY = 'app/services/portfolio.py'
with open(PORTFOLIO_PY, 'r', encoding='utf-8') as f:
    p_code = f.read()

OLD_CLS_BLOCK = '''    classification_list = []
    for classification in classifications.values():
        classification.setdefault("profit_krw", classification["market_value_krw"] - classification["cost_value_krw"])
        classification.setdefault("return_rate", classification["profit_krw"] / classification["cost_value_krw"] * 100 if classification["cost_value_krw"] else 0.0)
        classification["weight"] = classification["market_value_krw"] / total_value * 100 if total_value else 0.0
        classification_list.append(classification)
    classification_list.sort(key=lambda item: item["market_value_krw"], reverse=True)'''

NEW_CLS_BLOCK = '''    classification_list = []
    for classification in classifications.values():
        classification.setdefault("profit_krw", classification["market_value_krw"] - classification["cost_value_krw"])
        classification.setdefault("return_rate", classification["profit_krw"] / classification["cost_value_krw"] * 100 if classification["cost_value_krw"] else 0.0)
        classification["weight"] = classification["market_value_krw"] / total_value * 100 if total_value else 0.0
        classification_list.append(classification)
    classification_list.sort(key=lambda item: item["market_value_krw"], reverse=True)

    # 섹터별 포트폴리오 집계
    sectors: dict[str, dict[str, Any]] = {}
    for item in enriched:
        sec = item.get("sector") or get_default_sector(item.get("code", ""), item.get("name", ""))
        item["sector"] = sec
        s_obj = sectors.setdefault(sec, {
            "name": sec,
            "market_value_krw": 0.0,
            "cost_value_krw": 0.0,
            "profit_krw": 0.0,
            "return_rate": 0.0,
            "holding_count": 0,
            "weight": 0.0,
        })
        s_obj["market_value_krw"] += item["market_value_krw"]
        s_obj["cost_value_krw"] += item["cost_value_krw"]
        s_obj["profit_krw"] += item["profit_krw"]
        s_obj["holding_count"] += 1

    if total_cash_krw_combined > 0:
        sectors["현금·예수금"] = {
            "name": "현금·예수금",
            "market_value_krw": total_cash_krw_combined,
            "cost_value_krw": total_cash_krw_combined,
            "profit_krw": 0.0,
            "return_rate": 0.0,
            "holding_count": len([a for a in account_list if a.get("cash_total_krw", 0) > 0]),
            "weight": total_cash_krw_combined / total_value * 100 if total_value else 0.0,
        }

    sector_list = []
    for s_obj in sectors.values():
        s_obj["return_rate"] = s_obj["profit_krw"] / s_obj["cost_value_krw"] * 100 if s_obj["cost_value_krw"] else 0.0
        s_obj["weight"] = s_obj["market_value_krw"] / total_value * 100 if total_value else 0.0
        sector_list.append(s_obj)
    sector_list.sort(key=lambda x: x["market_value_krw"], reverse=True)'''

if OLD_CLS_BLOCK in p_code:
    p_code = p_code.replace(OLD_CLS_BLOCK, NEW_CLS_BLOCK, 1)
    p_code = p_code.replace('"classifications": classification_list,', '"classifications": classification_list,\n        "sector_classifications": sector_list,', 1)
    print("OK 1. Added sector_classifications to portfolio.py")

with open(PORTFOLIO_PY, 'w', encoding='utf-8') as f:
    f.write(p_code)

# 2. Update app/main.py
MAIN_PY = 'app/main.py'
with open(MAIN_PY, 'r', encoding='utf-8') as f:
    m_code = f.read()

# Update HoldingCreate model
OLD_HC = '''class HoldingCreate(BaseModel):
    account_id: str = ""
    broker: str = ""
    account_name: str = ""
    code: str = ""
    name: str = ""
    quantity: float = 0.0
    avg_price: float = 0.0
    current_price: float | None = None
    currency: str = "KRW"
    market: str = ""
    owner: str = "모두"'''

NEW_HC = '''class HoldingCreate(BaseModel):
    account_id: str = ""
    broker: str = ""
    account_name: str = ""
    code: str = ""
    name: str = ""
    sector: str = ""
    quantity: float = 0.0
    avg_price: float = 0.0
    current_price: float | None = None
    currency: str = "KRW"
    market: str = ""
    owner: str = "모두"'''

if OLD_HC in m_code:
    m_code = m_code.replace(OLD_HC, NEW_HC, 1)
    print("OK 2a. Added sector to HoldingCreate model")

# Remove startup TossOpenAPI call
OLD_STARTUP = '''@app.on_event("startup")
async def startup_event() -> None:
    toss = TossOpenAPI()
    if toss.configured:
        data = read_portfolio()
        syms = list({str(h.get("code", "")).upper() for h in data.get("holdings", []) if h.get("code")})
        if syms:
            asyncio.create_task(toss.get_multi_period_changes(syms))'''

NEW_STARTUP = '''@app.on_event("startup")
async def startup_event() -> None:
    # No external OpenAPI calls on startup to prevent rate limiting
    pass'''

if OLD_STARTUP in m_code:
    m_code = m_code.replace(OLD_STARTUP, NEW_STARTUP, 1)
    print("OK 2b. Removed startup TossOpenAPI call")

# Add stock chart endpoint
CHART_ENDPOINT = '''
@app.get("/api/stock-chart/{code}")
async def get_stock_chart(code: str, period: str = "1M") -> dict:
    from app.services.web_finance import fetch_stock_chart_data
    try:
        return await fetch_stock_chart_data(code, period)
    except Exception as exc:
        raise HTTPException(400, f"차트 데이터 조회 실패: {exc}") from exc
'''

if '/api/stock-chart' not in m_code:
    m_code = m_code.rstrip() + '\n' + CHART_ENDPOINT + '\n'
    print("OK 2c. Added /api/stock-chart endpoint")

with open(MAIN_PY, 'w', encoding='utf-8') as f:
    f.write(m_code)

print("Backend extensions complete!")
