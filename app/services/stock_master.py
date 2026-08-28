from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any
import httpx

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
STOCK_MASTER_CACHE_FILE = DATA_DIR / "stock_master_cache.json"

# 대표적인 미국 주식 및 ETF 한글-티커 매핑 사전
US_STOCK_NAME_MAP: dict[str, str] = {
    # 대표 미국 ETF
    "TQQQ": "TQQQ",
    "QLD": "QLD",
    "QQQM": "QQQM",
    "QQQ": "QQQ",
    "SPY": "SPY",
    "VOO": "VOO",
    "IVV": "IVV",
    "TLT": "TLT",
    "SOXL": "SOXL",
    "SOXS": "SOXS",
    "SQQQ": "SQQQ",
    "SOXX": "SOXX",
    "SCHD": "SCHD",
    "JEPI": "JEPI",
    "JEPQ": "JEPQ",
    "DIA": "DIA",
    "IWM": "IWM",
    "VNQ": "VNQ",
    "GLD": "GLD",
    "SLV": "SLV",
    "SPYG": "SPYG",
    "QNDX": "QNDX",
    "SMH": "SMH",
    "XLK": "XLK",
    "XLE": "XLE",
    "XLF": "XLF",
    "XLV": "XLV",
    "XLY": "XLY",
    "XLP": "XLP",
    "XLI": "XLI",
    "XLU": "XLU",
    "XLRE": "XLRE",
    "XLB": "XLB",
    "IEF": "IEF",
    "SHY": "SHY",
    "BND": "BND",
    "AGG": "AGG",
    "VT": "VT",
    "VTI": "VTI",
    "VXUS": "VXUS",
    "ARKK": "ARKK",
    "BIL": "BIL",
    "SHV": "SHV",
    "VGK": "VGK",
    "EEM": "EEM",
    "VWO": "VWO",
    "EWY": "EWY",
    "HYG": "HYG",
    "LQD": "LQD",
    "TMF": "TMF",
    "UPRO": "UPRO",
    "FNGU": "FNGU",
    "BULZ": "BULZ",
    # 대표 미국 개별주 (한글명 -> 티커)
    "엔비디아": "NVDA",
    "NVIDIA": "NVDA",
    "애플": "AAPL",
    "APPLE": "AAPL",
    "테슬라": "TSLA",
    "TESLA": "TSLA",
    "마이크로소프트": "MSFT",
    "MICROSOFT": "MSFT",
    "알파벳": "GOOGL",
    "구글": "GOOGL",
    "알파벳 A": "GOOGL",
    "알파벳 C": "GOOG",
    "아마존": "AMZN",
    "아마존닷컴": "AMZN",
    "AMAZON": "AMZN",
    "메타": "META",
    "META": "META",
    "마이크론": "MU",
    "마이크론 테크놀로지": "MU",
    "마이크론테크놀로지": "MU",
    "MICRON": "MU",
    "어플라이드 머티리얼즈": "AMAT",
    "어플라이드머티리얼즈": "AMAT",
    "APPLIED MATERIALS": "AMAT",
    "램 리서치": "LRCX",
    "램리서치": "LRCX",
    "LAM RESEARCH": "LRCX",
    "브로드컴": "AVGO",
    "BROADCOM": "AVGO",
    "ASML": "ASML",
    "AMD": "AMD",
    "어드밴스드 마이크로 디바이스": "AMD",
    "퀄컴": "QCOM",
    "인텔": "INTC",
    "TSMC": "TSM",
    "타이완 반도체": "TSM",
    "코카콜라": "KO",
    "펩시코": "PEP",
    "스타벅스": "SBUX",
    "나이키": "NKE",
    "NIKE": "NKE",
    "머크": "MRK",
    "MERCK": "MRK",
    "화이자": "PFE",
    "존슨 앤 존슨": "JNJ",
    "존슨앤존슨": "JNJ",
    "JOHNSON & JOHNSON": "JNJ",
    "일라이 릴리": "LLY",
    "일라이릴리": "LLY",
    "ELI LILLY": "LLY",
    "버크셔 해서웨이": "BRK.B",
    "버크셔해서웨이": "BRK.B",
    "JP모건": "JPM",
    "JP모건 체이스": "JPM",
    "비자": "V",
    "마스터카드": "MA",
    "월트 디즈니": "DIS",
    "디즈니": "DIS",
    "코스트코": "COST",
    "넷플릭스": "NFLX",
    "팔란티어": "PLTR",
    "슈퍼 마이크로 컴퓨터": "SMCI",
    "암 홀딩스": "ARM",
    "아이온큐": "IONQ",
}

# 국내 주요 주식 및 대표 약칭 매핑 사전
KR_STOCK_ALIAS_MAP: dict[str, str] = {
    "현대차": "005380",
    "현차": "005380",
    "현대자동차": "005380",
    "삼전": "005930",
    "삼성전자": "005930",
    "삼전우": "005935",
    "삼성전자우": "005935",
    "하닉": "000660",
    "하이닉스": "000660",
    "SK하이닉스": "000660",
    "네이버": "035420",
    "NAVER": "035420",
    "카카오": "035720",
    "카뱅": "323410",
    "카카오뱅크": "323410",
    "카페": "377300",
    "카카오페이": "377300",
    "크래프톤": "259960",
    "포스코홀딩스": "005490",
    "포스코": "005490",
    "POSCO홀딩스": "005490",
    "포홀": "005490",
    "LG엔솔": "373220",
    "엔솔": "373220",
    "엘지에너지솔루션": "373220",
    "LG에너지솔루션": "373220",
    "에코프로": "086520",
    "에코프로비엠": "247540",
    "에코비엠": "247540",
    "셀트리온": "068270",
    "셀트": "068270",
    "삼성바이오로직스": "207940",
    "삼바": "207940",
    "기아": "000270",
    "기아차": "000270",
    "현대모비스": "012330",
    "모비스": "012330",
    "LG화학": "051910",
    "엘지화학": "051910",
    "삼성SDI": "006400",
    "삼성에스디아이": "006400",
    "삼성물산": "028260",
    "한화에어로스페이스": "012450",
    "한화에어로": "012450",
    "한화오션": "042660",
    "대한항공": "003490",
    "신한지주": "055550",
    "KB금융": "105560",
    "하나금융지주": "086790",
    "우리금융지주": "316140",
    "기업은행": "024110",
    "삼성생명": "032830",
    "삼성화재": "000810",
    "KT&G": "033780",
    "케이티앤지": "033780",
    "KT": "030200",
    "케이티": "030200",
    "SK텔레콤": "017670",
    "SKT": "017670",
    "LG유플러스": "032640",
    "LGU+": "032640",
    "두산에너빌리티": "034020",
    "두산중공업": "034020",
    "HD현대중공업": "329180",
    "현대중공업": "329180",
    "HD현대일렉트릭": "267260",
    "현대일렉트릭": "267260",
    "알테오젠": "196170",
    "HLB": "028300",
    "에이치엘비": "028300",
}

# 티커 -> 한글/공식명칭 역매핑
US_STOCK_CODE_MAP: dict[str, str] = {
    v: k for k, v in US_STOCK_NAME_MAP.items() if not k.isupper()
}

_NAME_TO_CODE_MAP: dict[str, str] = {}
_CODE_TO_NAME_MAP: dict[str, str] = {}
_INITIALIZED: bool = False


def _normalize_key(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9가-힣]", "", str(text or "")).upper()


def load_stock_master_cache() -> None:
    global _NAME_TO_CODE_MAP, _CODE_TO_NAME_MAP, _INITIALIZED
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 로컬 캐시 파일 로드
    if STOCK_MASTER_CACHE_FILE.exists():
        try:
            with open(STOCK_MASTER_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                name_to_code = data.get("name_to_code", {})
                code_to_name = data.get("code_to_name", {})
                for n, c in name_to_code.items():
                    _NAME_TO_CODE_MAP[n] = c
                    _NAME_TO_CODE_MAP[_normalize_key(n)] = c
                for c, n in code_to_name.items():
                    _CODE_TO_NAME_MAP[c] = n
        except Exception as e:
            logger.warning(f"종목 마스터 캐시 파일 로드 실패: {e}")

    # 2. 국내 주요 별칭 및 미국 사전 등록 (최우선)
    for name, code in KR_STOCK_ALIAS_MAP.items():
        _NAME_TO_CODE_MAP[name] = code
        _NAME_TO_CODE_MAP[_normalize_key(name)] = code

    for name, ticker in US_STOCK_NAME_MAP.items():
        _NAME_TO_CODE_MAP[name] = ticker
        _NAME_TO_CODE_MAP[_normalize_key(name)] = ticker
        if ticker not in _CODE_TO_NAME_MAP:
            _CODE_TO_NAME_MAP[ticker] = name

    # 3. 대시보드 기존 holdings, dividend, pnl 데이터 인덱싱
    _index_existing_dashboard_records()
    _INITIALIZED = True


def save_stock_master_cache() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = {
            "name_to_code": _NAME_TO_CODE_MAP,
            "code_to_name": _CODE_TO_NAME_MAP,
        }
        with open(STOCK_MASTER_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"종목 마스터 캐시 저장 실패: {e}")


def _index_existing_dashboard_records() -> None:
    # portfolio.json
    portfolio_file = DATA_DIR / "portfolio.json"
    if portfolio_file.exists():
        try:
            with open(portfolio_file, "r", encoding="utf-8") as f:
                p_data = json.load(f)
                for h in p_data.get("holdings", []):
                    c = str(h.get("code", "")).strip()
                    n = str(h.get("name", "")).strip()
                    if c and n:
                        _CODE_TO_NAME_MAP[c] = n
                        _NAME_TO_CODE_MAP[n] = c
                        _NAME_TO_CODE_MAP[_normalize_key(n)] = c
        except Exception:
            pass

    # actual_dividend_records.json
    div_file = DATA_DIR / "actual_dividend_records.json"
    if div_file.exists():
        try:
            with open(div_file, "r", encoding="utf-8") as f:
                d_data = json.load(f)
                for r in d_data.get("records", []):
                    c = str(r.get("code", "")).strip()
                    n = str(r.get("name", "")).strip()
                    if c and n:
                        _CODE_TO_NAME_MAP[c] = n
                        _NAME_TO_CODE_MAP[n] = c
                        _NAME_TO_CODE_MAP[_normalize_key(n)] = c
        except Exception:
            pass

    # realized_pnl_records.json
    pnl_file = DATA_DIR / "realized_pnl_records.json"
    if pnl_file.exists():
        try:
            with open(pnl_file, "r", encoding="utf-8") as f:
                r_data = json.load(f)
                for r in r_data.get("records", []):
                    c = str(r.get("code", "")).strip()
                    n = str(r.get("name", "")).strip()
                    if c and n and c != n:
                        _CODE_TO_NAME_MAP[c] = n
                        _NAME_TO_CODE_MAP[n] = c
                        _NAME_TO_CODE_MAP[_normalize_key(n)] = c
        except Exception:
            pass


async def sync_stock_master_online() -> None:
    global _NAME_TO_CODE_MAP, _CODE_TO_NAME_MAP
    if not _INITIALIZED:
        load_stock_master_cache()

    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. 국내 상장 ETF 전체 수집 (네이버 증권 ETF API)
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://finance.naver.com/api/sise/etfItemList.nhn", headers=headers)
            if resp.status_code == 200:
                data = json.loads(resp.content.decode("cp949", errors="ignore"))
                items = data.get("result", {}).get("etfItemList", [])
                for item in items:
                    c = str(item.get("itemcode", "")).strip()
                    n = str(item.get("itemname", "")).strip()
                    if c and n:
                        _CODE_TO_NAME_MAP[c] = n
                        _NAME_TO_CODE_MAP[n] = c
                        _NAME_TO_CODE_MAP[_normalize_key(n)] = c
                logger.info(f"국내 ETF 마스터 동기화 완료: {len(items)}개")
    except Exception as e:
        logger.warning(f"ETF 마스터 동기화 실패: {e}")

    # 2. KRX 상장법인목록 전체 수집 (KIND)
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get("https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13", headers=headers)
            if resp.status_code == 200:
                text = resp.content.decode("euc-kr", errors="ignore")
                rows = re.findall(r"<tr>(.*?)</tr>", text, re.DOTALL)
                krx_count = 0
                for row in rows[1:]:
                    cols = [re.sub(r"<[^>]+>", "", td).strip() for td in re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)]
                    if len(cols) >= 3:
                        n = cols[0]
                        c = cols[2].zfill(6)
                        if n and c:
                            _CODE_TO_NAME_MAP[c] = n
                            _NAME_TO_CODE_MAP[n] = c
                            _NAME_TO_CODE_MAP[_normalize_key(n)] = c
                            krx_count += 1
                logger.info(f"KRX 상장법인 마스터 동기화 완료: {krx_count}개")
    except Exception as e:
        logger.warning(f"KRX 상장법인 마스터 동기화 실패: {e}")

    # 3. 미국 종목 사전 재보강 (덮어쓰기 방지)
    for name, ticker in US_STOCK_NAME_MAP.items():
        _NAME_TO_CODE_MAP[name] = ticker
        _NAME_TO_CODE_MAP[_normalize_key(name)] = ticker
        _CODE_TO_NAME_MAP[ticker] = name

    save_stock_master_cache()


def search_stock_by_name(query: str) -> dict[str, Any]:
    """종목명 또는 약칭으로 최적의 종목코드와 통화를 검색한다."""
    if not _INITIALIZED:
        load_stock_master_cache()

    q = str(query or "").strip()
    if not q:
        return {"found": False, "code": "", "name": "", "currency": "KRW", "suggestions": []}

    norm_q = _normalize_key(q)

    # 0. 이자(원화이자, 달러이자, RP이자 등) 전용 처리 (화이자 주식 오매칭 방지)
    is_interest_query = ("이자" in norm_q or "예탁금" in norm_q or norm_q.startswith("interest")) and norm_q != "화이자" and not norm_q.startswith("화이자")
    if is_interest_query:
        if "달러" in norm_q or "외화" in norm_q or "usd" in norm_q.lower() or norm_q == "interestusd":
            return {
                "found": True,
                "code": "INTEREST_USD",
                "name": "달러이자",
                "currency": "USD",
                "suggestions": [
                    {"code": "INTEREST_USD", "name": "달러이자", "currency": "USD"},
                    {"code": "INTEREST_KRW", "name": "원화이자", "currency": "KRW"},
                ]
            }
        elif "rp" in norm_q.lower() or norm_q == "interestrp":
            return {
                "found": True,
                "code": "INTEREST_RP",
                "name": "RP이자",
                "currency": "KRW",
                "suggestions": [
                    {"code": "INTEREST_RP", "name": "RP이자", "currency": "KRW"},
                ]
            }
        elif "예탁금" in norm_q or norm_q == "interestcash":
            return {
                "found": True,
                "code": "INTEREST_CASH",
                "name": "예탁금이자",
                "currency": "KRW",
                "suggestions": [
                    {"code": "INTEREST_CASH", "name": "예탁금이자", "currency": "KRW"},
                ]
            }
        elif "원화" in norm_q or norm_q == "이자" or norm_q == "interestkrw":
            return {
                "found": True,
                "code": "INTEREST_KRW",
                "name": "원화이자",
                "currency": "KRW",
                "suggestions": [
                    {"code": "INTEREST_KRW", "name": "원화이자", "currency": "KRW"},
                    {"code": "INTEREST_USD", "name": "달러이자", "currency": "USD"},
                ]
            }
        else:
            return {
                "found": True,
                "code": "INTEREST_KRW",
                "name": q,
                "currency": "KRW",
                "suggestions": [
                    {"code": "INTEREST_KRW", "name": "원화이자", "currency": "KRW"},
                    {"code": "INTEREST_USD", "name": "달러이자", "currency": "USD"},
                ]
            }

    code, name, curr = resolve_stock_info(code="", name=q)
    is_found = bool(code and code != q)

    # 부분 일치 후보 리스트 (최대 6개)
    suggestions: list[dict[str, str]] = []

    # 1. 완전 일치 후보
    if is_found:
        suggestions.append({"code": code, "name": name, "currency": curr})

    # 2. 접두사, 포함, 토큰 분리 일치 후보군 탐색
    matches: list[tuple[int, int, str, str]] = []
    seen_codes = {code} if is_found else set()
    tokens = [re.sub(r'[^a-zA-Z0-9가-힣]', '', t).upper() for t in re.findall(r'[a-zA-Z0-9]+|[가-힣]+', q)]
    tokens = [t for t in tokens if t]

    for c, n in _CODE_TO_NAME_MAP.items():
        if c in seen_codes:
            continue
        norm_n = _normalize_key(n)
        norm_c = _normalize_key(c)
        if norm_n.startswith(norm_q) or norm_c.startswith(norm_q):
            matches.append((0, len(norm_n), c, n))
            seen_codes.add(c)
        elif norm_q in norm_n or norm_q in norm_c:
            matches.append((1, len(norm_n), c, n))
            seen_codes.add(c)
        elif tokens and all(t in norm_n for t in tokens):
            matches.append((2, len(norm_n), c, n))
            seen_codes.add(c)
        if len(matches) >= 30:
            break

    matches.sort()
    for _, _, c, n in matches[:5]:
        _, _, item_curr = resolve_stock_info(code=c, name=n)
        suggestions.append({"code": c, "name": n, "currency": item_curr})

    best_code = code if is_found else (suggestions[0]["code"] if suggestions else "")
    best_name = name if is_found else (suggestions[0]["name"] if suggestions else q)
    best_curr = curr if is_found else (suggestions[0]["currency"] if suggestions else "KRW")

    return {
        "found": bool(best_code),
        "code": best_code,
        "name": best_name,
        "currency": best_curr,
        "suggestions": suggestions,
    }


def resolve_stock_info(code: str = "", name: str = "", currency: str = "") -> tuple[str, str, str]:
    if not _INITIALIZED:
        load_stock_master_cache()

    code = str(code or "").strip()
    name = str(name or "").strip()
    curr = str(currency or "").strip().upper()

    if not code and not name:
        return ("", "", curr or "KRW")

    norm_name = _normalize_key(name)
    norm_code = _normalize_key(code)

    # 0. 이자(원화이자, 달러이자, RP이자, 예탁금이자 등) 전용 항목 처리 (화이자 주식 오매칭 방지)
    is_interest_item = (
        ("이자" in norm_name or "예탁금" in norm_name or code.startswith("INTEREST_"))
        and norm_name != "화이자"
        and not norm_name.startswith("화이자")
    )
    if is_interest_item:
        if "달러" in norm_name or "외화" in norm_name or "usd" in norm_name.lower() or code == "INTEREST_USD":
            return (code or "INTEREST_USD", name or "달러이자", "USD")
        elif "rp" in norm_name.lower() or code == "INTEREST_RP":
            return (code or "INTEREST_RP", name or "RP이자", curr or "KRW")
        elif "예탁금" in norm_name or code == "INTEREST_CASH":
            return (code or "INTEREST_CASH", name or "예탁금이자", curr or "KRW")
        elif "원화" in norm_name or norm_name == "이자" or code == "INTEREST_KRW":
            return (code or "INTEREST_KRW", name or "원화이자", curr or "KRW")
        else:
            return (code or "INTEREST_KRW", name, curr or "KRW")

    # 1. code가 없고 name만 있는 경우
    if not code and name:
        # A. 미국 사전 및 영문 티커 우선 매칭
        if name in US_STOCK_NAME_MAP or norm_name in _NAME_TO_CODE_MAP:
            matched = _NAME_TO_CODE_MAP.get(name) or _NAME_TO_CODE_MAP.get(norm_name)
            if matched:
                code = matched

        if not code:
            # B. 종목명 자체가 미국 티커인 경우 (예: "TQQQ", "NVDA", "SPY")
            if name.isupper() and 1 <= len(name) <= 6 and name.isalpha():
                code = name
            else:
                # C. 국내 별칭/약칭 및 마스터 직접 매칭
                matched_code = (
                    KR_STOCK_ALIAS_MAP.get(name)
                    or KR_STOCK_ALIAS_MAP.get(norm_name)
                    or _NAME_TO_CODE_MAP.get(name)
                    or _NAME_TO_CODE_MAP.get(norm_name)
                )
                if matched_code:
                    code = matched_code
                else:
                    # D. 부분 일치 및 토큰 일치
                    tokens = [re.sub(r'[^a-zA-Z0-9가-힣]', '', t).upper() for t in re.findall(r'[a-zA-Z0-9]+|[가-힣]+', name)]
                    tokens = [t for t in tokens if t]
                    prefix_matches = []
                    contains_matches = []
                    token_matches = []
                    for c, n in _CODE_TO_NAME_MAP.items():
                        norm_n = _normalize_key(n)
                        if norm_n.startswith(norm_name):
                            prefix_matches.append((len(norm_n), c, n))
                        elif norm_name in norm_n:
                            contains_matches.append((len(norm_n), c, n))
                        elif tokens and all(t in norm_n for t in tokens):
                            token_matches.append((len(norm_n), c, n))

                    if prefix_matches:
                        prefix_matches.sort()
                        code = prefix_matches[0][1]
                        name = prefix_matches[0][2]
                    elif contains_matches:
                        contains_matches.sort()
                        code = contains_matches[0][1]
                        name = contains_matches[0][2]
                    elif token_matches:
                        token_matches.sort()
                        code = token_matches[0][1]
                        name = token_matches[0][2]
                    else:
                        code = name

    # 2. code가 있고 name이 없거나 보정이 필요한 경우
    if code and (not name or name == code):
        matched_name = _CODE_TO_NAME_MAP.get(code) or _CODE_TO_NAME_MAP.get(code.zfill(6))
        if matched_name:
            name = matched_name
        else:
            if code.upper() in US_STOCK_CODE_MAP:
                name = US_STOCK_CODE_MAP[code.upper()]
            elif code.upper() in US_STOCK_NAME_MAP:
                name = US_STOCK_NAME_MAP[code.upper()]
            else:
                name = code

    # 3. 통화(currency) 자동 결정
    if not curr:
        code_upper = code.upper()
        if (code.isdigit() and len(code) == 6) or (len(code) == 6 and not code.isalpha()):
            curr = "KRW"
        elif code_upper in US_STOCK_NAME_MAP.values() or (code_upper.isalpha() and 1 <= len(code_upper) <= 5):
            curr = "USD"
        else:
            if any("가" <= ch <= "힣" for ch in (code + name)):
                curr = "KRW"
            else:
                curr = "USD"

    return (code, name, curr)
