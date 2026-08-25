#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_portfolio_sectors.py
- Add default sector mapping
- Add sector to normalize_holding
- Add sector_classifications to get_dashboard
"""

PORTFOLIO_PY = 'app/services/portfolio.py'
with open(PORTFOLIO_PY, 'r', encoding='utf-8') as f:
    code = f.read()

SECTOR_MAP_CODE = '''
DEFAULT_SECTOR_MAP = {
    # 반도체
    "005930": "반도체", "005935": "반도체", "000660": "반도체", "0193T0": "반도체", "0193W0": "반도체",
    "091160": "반도체", "240810": "반도체", "353200": "반도체", "395160": "반도체", "471990": "반도체",
    "NVDA": "반도체", "AVGO": "반도체", "TSM": "반도체", "NVDL": "반도체",

    # IT·빅테크
    "AAPL": "IT·빅테크", "MSFT": "IT·빅테크", "035420": "IT·빅테크", "030000": "IT·빅테크",

    # 2차전지·모빌리티
    "364980": "2차전지", "TSLA": "모빌리티·2차전지", "005380": "자동차·운송",

    # 금융·지주
    "0089D0": "금융·지주", "039490": "금융·지주", "055550": "금융·지주", "086790": "금융·지주",
    "091170": "금융·지주", "102970": "금융·지주", "105560": "금융·지주", "138040": "금융·지주", "316140": "금융·지주",

    # 전력·인프라·건설
    "015760": "전력·인프라", "117700": "건설·인프라", "267260": "전력·인프라",
    "487130": "전력·인프라", "487240": "전력·인프라",

    # 방산·조선
    "449450": "방산·우주", "466920": "조선·기계",

    # 바이오·헬스케어
    "244580": "바이오·헬스케어",

    # 소비재·엔터·유통
    "228790": "소비재·뷰티", "475050": "엔터·미디어", "KO": "음료·소비재", "WMT": "도소매·유통",

    # 리츠·부동산
    "481850": "리츠·부동산",

    # 미국 대표지수·ETF
    "QQQM": "미국 대표지수", "SPYG": "미국 대표지수", "QLD": "미국 대표지수", "TQQQ": "미국 대표지수",
    "QNDX": "미국 대표지수", "IVV": "미국 대표지수", "0015B0": "미국 대표지수", "0026S0": "미국 대표지수",
    "0069M0": "미국 대표지수", "0104H0": "미국 대표지수", "0190M0": "미국 대표지수", "379810": "미국 대표지수",

    # 국내 대표지수·ETF
    "069500": "국내 대표지수", "0163Y0": "국내 대표지수", "0088N0": "국내 대표지수",

    # 채권·안전자산
    "TLT": "채권·안전자산",
}


def get_default_sector(code: str, name: str = "") -> str:
    c = str(code).strip().upper()
    if c in DEFAULT_SECTOR_MAP:
        return DEFAULT_SECTOR_MAP[c]
    n = name.upper()
    if any(k in n for k in ["반도체", "SEMICONDUCTOR", "CHIP"]): return "반도체"
    if any(k in n for k in ["2차전지", "배터리", "BATTERY"]): return "2차전지"
    if any(k in n for k in ["금융", "은행", "증권", "지주", "FINANCIAL", "BANK"]): return "금융·지주"
    if any(k in n for k in ["전력", "인프라", "에너지", "ENERGY", "POWER"]): return "전력·인프라"
    if any(k in n for k in ["바이오", "헬스케어", "PHARMA", "BIO", "HEALTH"]): return "바이오·헬스케어"
    if any(k in n for k in ["나스닥", "S&P", "다우", "INDEX", "200", "코스닥"]): return "대표지수·ETF"
    return "기타"
'''

if 'DEFAULT_SECTOR_MAP' not in code:
    insert_pos = code.find('def normalize_holding')
    code = code[:insert_pos] + SECTOR_MAP_CODE + '\n\n' + code[insert_pos:]
    print("OK 1. Added DEFAULT_SECTOR_MAP")

# Update normalize_holding to include sector
OLD_NORM = '''        "source": source,
        "price_updated_at": raw.get("price_updated_at"),
    }'''

NEW_NORM = '''        "source": source,
        "sector": clean_text(raw.get("sector")) or get_default_sector(code, name),
        "price_updated_at": raw.get("price_updated_at"),
    }'''

if OLD_NORM in code:
    code = code.replace(OLD_NORM, NEW_NORM, 1)
    print("OK 2. Updated normalize_holding with sector")

# Add sector_classifications calculation in get_dashboard
OLD_CLASS_END = '''        "classifications": [
            {
                "key": key,
                "label": item["label"],
                "market_value_krw": item["market_value_krw"],
                "cost_value_krw": item["cost_value_krw"],
                "profit_krw": item["profit_krw"],
                "rate": item["profit_krw"] / item["cost_value_krw"] * 100 if item["cost_value_krw"] else 0,
                "weight": item["market_value_krw"] / total_value * 100 if total_value else 0,
                "holding_count": item["holding_count"],
            }
            for key, item in classifications.items()
        ],'''

NEW_CLASS_END = '''        "classifications": [
            {
                "key": key,
                "label": item["label"],
                "market_value_krw": item["market_value_krw"],
                "cost_value_krw": item["cost_value_krw"],
                "profit_krw": item["profit_krw"],
                "rate": item["profit_krw"] / item["cost_value_krw"] * 100 if item["cost_value_krw"] else 0,
                "weight": item["market_value_krw"] / total_value * 100 if total_value else 0,
                "holding_count": item["holding_count"],
            }
            for key, item in classifications.items()
        ],
        "sector_classifications": [
            {
                "key": s_name,
                "label": s_name,
                "market_value_krw": s_item["market_value_krw"],
                "cost_value_krw": s_item["cost_value_krw"],
                "profit_krw": s_item["profit_krw"],
                "rate": s_item["profit_krw"] / s_item["cost_value_krw"] * 100 if s_item["cost_value_krw"] else 0,
                "weight": s_item["market_value_krw"] / total_value * 100 if total_value else 0,
                "holding_count": s_item["holding_count"],
            }
            for s_name, s_item in sector_classifications.items()
        ],'''

SECTOR_ACCUMULATOR = '''
    sector_classifications: dict[str, dict[str, Any]] = {}
    for h in enriched:
        sec = h.get("sector") or get_default_sector(h.get("code", ""), h.get("name", ""))
        sec_obj = sector_classifications.setdefault(sec, {
            "label": sec,
            "market_value_krw": 0.0,
            "cost_value_krw": 0.0,
            "profit_krw": 0.0,
            "holding_count": 0,
        })
        sec_obj["market_value_krw"] += h["market_value_krw"]
        sec_obj["cost_value_krw"] += h["cost_value_krw"]
        sec_obj["profit_krw"] += h["profit_krw"]
        sec_obj["holding_count"] += 1

    # 현금·예수금도 섹터에 포함
    total_cash_all = total_cash_krw + (total_cash_usd * usd_rate)
    if total_cash_all > 0:
        sector_classifications["현금·예수금"] = {
            "label": "현금·예수금",
            "market_value_krw": total_cash_all,
            "cost_value_krw": total_cash_all,
            "profit_krw": 0.0,
            "holding_count": len([a for a in accounts.values() if a["cash_total_krw"] > 0]),
        }
'''

if OLD_CLASS_END in code:
    insert_sec_pos = code.find('classifications["현금·예수금"] =')
    if insert_sec_pos != -1:
        # insert after classifications block
        class_ret_pos = code.find('return {', insert_sec_pos)
        code = code[:class_ret_pos] + SECTOR_ACCUMULATOR + '\n    ' + code[class_ret_pos:]
        code = code.replace(OLD_CLASS_END, NEW_CLASS_END, 1)
        print("OK 3. Added sector_classifications to get_dashboard")

with open(PORTFOLIO_PY, 'w', encoding='utf-8') as f:
    f.write(code)

print("Portfolio sector updates complete!")
