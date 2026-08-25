import urllib.request
import json

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# 1. 국내 주식 및 ETF 테스트
for code in ["005930", "0015B0", "228790", "000660", "475050"]:
    url = f"https://m.stock.naver.com/api/stock/{code}/basic"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
            print(f"[Domestic] {code}: {data.get('stockName')} -> Price: {data.get('nowPrice')}, Change: {data.get('changePrice')}, Rate: {data.get('fluctuationsRatio')}%")
    except Exception as e:
        print(f"[Domestic Error] {code}: {e}")

# 2. 실시간 환율 테스트 (USD/KRW)
url_fx = "https://m.stock.naver.com/api/fx/FX_USDKRW"
try:
    req = urllib.request.Request(url_fx, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read().decode("utf-8"))
        print(f"[FX] USDKRW: Price: {data.get('nowPrice')}, Rate: {data.get('fluctuationsRatio')}%")
except Exception as e:
    print(f"[FX Error]: {e}")

# 3. 미국 주식 및 ETF 테스트 (Yahoo Finance & Naver)
for sym in ["QQQM", "AAPL", "TLT", "TQQQ", "SPYG", "QLD", "QNDX"]:
    url_us = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
    try:
        req = urllib.request.Request(url_us, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read().decode("utf-8"))
            meta = res["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            rate = ((price - prev) / prev * 100) if prev else 0
            print(f"[Yahoo US] {sym}: Price: {price}, Prev: {prev}, Rate: {rate:.2f}%")
    except Exception as e:
        print(f"[Yahoo US Error] {sym}: {e}")
