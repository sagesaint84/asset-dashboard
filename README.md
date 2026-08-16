# 내 자산 대시보드

KB증권 계좌와 토스증권·나무증권 등 다른 증권사의 보유종목을 한 화면에서 합산하는 로컬 전용 FastAPI 대시보드입니다.

## 할 수 있는 일

- KB증권 OpenAPI로 국내 보유주식(SSQM1801), 국내 잔고(SSQM2932), 해외주식 잔고평가(SPQM2226)를 동기화합니다.
- 토스증권 OpenAPI로 계좌 목록과 국내·미국 보유주식을 읽어 동기화하고, USD/KRW 환율을 실시간으로 반영합니다. 주문 API는 사용하지 않습니다.
- 나무증권(NH투자증권) NHPLUG Open API로 계좌 목록과 국내·해외 보유주식을 읽어 동기화합니다.
- 토스증권 시장지표 API의 코스피와 SPY·QQQ 추종 ETF의 일중 캔들로 상단 미니 그래프를 표시합니다. 미국 지수 심볼은 토스 API에서 직접 제공되지 않아 SPY·QQQ를 기준으로 표시합니다.
- KB OpenAPI의 국내 현재가(IVU10140)와 해외 현재가(GSS10030)로 가져온 보유종목의 시세를 갱신합니다.
- 다른 증권사의 내보내기 파일(CSV/XLSX)을 가져와 계좌별로 통합합니다.
- 종목을 직접 추가·삭제하고, 계좌별 비중·평가금액·평가손익을 확인합니다.
- 원화·달러 자산과 투자자산 분류별 수익률, 전일 저장 기준 대비 평가자산 변동을 확인합니다.

이 프로그램은 주문을 내거나 계좌 비밀번호를 보관하지 않습니다. 모든 보유내역은 이 폴더의 `data/portfolio.json`에만 저장됩니다.

## 시작하기 (Windows)

1. 이 폴더에서 PowerShell을 엽니다.
2. 아래 명령을 한 번 실행합니다.

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. `.env.example` 파일을 복사해 이름을 `.env`로 바꿉니다.
4. KB OpenAPI 포털에서 발급받은 `appKey`, `appSecret`을 `.env`에 입력합니다.
5. 실행합니다.

   ```powershell
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

6. 브라우저에서 `http://127.0.0.1:8000`을 엽니다. 처음 만든 `index.html`은 이 주소의 시작 페이지로 연결되며, 실제 대시보드는 `/dashboard`에서 열립니다.

이후에는 `대시보드_실행.cmd` 파일을 더블클릭하면 됩니다. 창을 닫으면 대시보드 서버도 종료됩니다.

## 다른 증권사 파일 가져오기

직접 OpenAPI를 제공하지 않는 증권사에서 내려받은 CSV/XLSX를 화면의 **파일 가져오기**에서 선택하세요. 첫 번째 행에는 아래 중 가능한 열 이름을 넣어 주세요.

| 항목 | 인식하는 열 이름 예시 |
| --- | --- |
| 증권사 | `증권사`, `broker` |
| 계좌 | `계좌명`, `계좌번호`, `account` |
| 종목코드 | `종목코드`, `종목번호`, `code`, `symbol` |
| 종목명 | `종목명`, `종목`, `name` |
| 수량 | `보유수량`, `수량`, `quantity` |
| 평균매입가 | `평균매입가`, `매입단가`, `buy_price` |
| 현재가 | `현재가`, `price`, `current_price` |
| 통화 | `통화`, `currency` |
| 거래소 | `거래소`, `market`, `exchange` |

가져온 종목은 계좌명과 종목코드가 같으면 최신 파일의 값으로 갱신됩니다. 시세가 비어 있거나 오래된 경우 **시세 갱신**을 누르면 KB 시세 API로 조회를 시도합니다. 해외 종목은 거래소 코드(NAS, NYS, AMX 등)가 있어야 갱신할 수 있습니다.

## KB OpenAPI 연결

KB 제공 Python 예제와 같은 B2C 요청 형식을 따릅니다.

- 토큰: `POST /oauth2/token`, `grantType=client_credentials`
- 요청: `POST /api/v1/*` + `dataHeader`/`dataBody`
- 헤더: `appKey`, `Authorization: bearer <access_token>`

KB OpenAPI는 운영 서버를 호출합니다. 호출 제한을 고려해 화면의 버튼을 눌렀을 때만 동기화·시세 갱신을 수행합니다. 실제 응답 구조가 계정별로 다를 수 있으므로, 첫 연결 후 화면의 결과와 KB 앱을 대조해 주세요.

## 토스증권 OpenAPI 연결

1. 토스증권 WTS의 Open API 설정에서 Client ID와 Client Secret을 발급받고, 허용 IP에 이 컴퓨터의 공인 IP를 등록합니다.
2. `.env.example`을 복사한 `.env`에 `TOSSINVEST_CLIENT_ID`, `TOSSINVEST_CLIENT_SECRET`을 입력합니다.
3. 대시보드를 다시 시작한 뒤 **토스 계좌 동기화**를 누릅니다.

토스증권 계좌 목록(`GET /api/v1/accounts`)을 조회한 뒤 각 계좌의 보유주식(`GET /api/v1/holdings`)을 가져옵니다. 토스증권 API의 현재가 다건 조회도 시세 갱신에 사용합니다. 계좌번호는 마지막 네 자리만 대시보드에 표시합니다.

화면의 **환율 갱신**은 토스증권의 `GET /api/v1/exchange-rate`를 이용해 보유 중인 외화(USD·JPY·HKD·CNY 등)의 원화 환율과 유효 시각을 반영합니다. `.env`에 고정 환율을 적지 않습니다.

## 나무증권(NHPLUG) 연결

1. NHPLUG에서 App Key와 App Secret을 발급합니다.
2. `.env`의 `NHPLUG_APP_KEY`, `NHPLUG_APP_SECRET`에 입력합니다. 실계좌는 기본 주소를 그대로 사용하고, 모의계좌는 `NHPLUG_BASE_URL=https://moapi.nhplug.com:8443`으로 바꿉니다.
3. 대시보드를 다시 시작한 뒤 **나무 계좌 동기화**를 누릅니다.

동기화는 NHPLUG의 계좌 조회와 국내·해외 잔고 조회만 사용하며, 주문 기능은 호출하지 않습니다. 계좌번호는 마지막 네 자리만 대시보드에 표시합니다.
