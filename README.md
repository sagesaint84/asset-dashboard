# 📊 내 자산 대시보드 (My Asset Dashboard)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Supported-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**가족 통합 포트폴리오 · 주요 증권사 OpenAPI 연동 · 실시간 국내/해외 시세 · 배당금 및 실현손익 정밀 관리 로컬 자산 관리 플랫폼**

</div>

---

## 📑 목차
- [✨ 주요 기능](#-주요-기능)
- [🔑 환경변수(.env) 설정 및 OpenAPI 연동](#-환경변수env-설정-및-openapi-연동)
- [📂 엑셀 / CSV 파일 일괄 가져오기](#-엑셀--csv-파일-일괄-가져오기)
- [🖥️ Windows 설치 및 사용 방법](#️-windows-설치-및-사용-방법)
- [🐧 Linux / Docker 설치, 실행 및 업데이트 방법](#-linux--docker-설치-실행-및-업데이트-방법)
- [🛡️ 보안 및 개인정보 보호 안내](#️-보안-및-개인정보-보호-안내)

---

## ✨ 주요 기능

### 1. 👨‍👩‍👧 가족 구성원 통합 및 소유자별 필터링
- 가족 구성원(예: `아빠`, `엄마`, `자녀`)을 자유롭게 등록/관리할 수 있습니다.
- 상단 소유자 탭 클릭 한 번으로 **전체 통합 요약**, **보유종목**, **배당금**, **매도 실현손익**, **자산 스냅샷**을 개별 또는 전체 단위로 즉시 필터링합니다.

### 2. 📈 실시간 시장 지표 & 실시간 환율 & 핵심 요약
- 네이버 증권 및 야후 파이낸스 연동으로 **코스피, 코스닥, S&P 500, 나스닥 지수**의 실시간 시세와 1개월 추이 미니 차트를 제공합니다.
- **실시간 USD/KRW 환율**을 자동으로 수신하여 원화 및 달러 자산을 실시간 원화 환산 가치로 정확하게 집계합니다.
- 핵심요약(OVERVIEW) 카드는 **평가금액 / 수익률 / 매입금액 또는 기준일**의 3줄 구조로 정갈하게 표시됩니다.

### 3. 💼 통합 포트폴리오 & 기간별(1D/1W/1M/YTD/1Y) 수익률
- 증권사별 계좌(토스증권, KB증권, 나무증권, 키움증권 등)의 주식 평가액과 예수금을 한 화면에 통합합니다.
- 각 종목별 **1일(1D), 1주일(1W), 1개월(1M), 연초 대비(YTD), 1년(1Y)** 수익률을 자동 계산하여 인터랙티브 SVG 차트로 시각화합니다.
- 팝업에서 등록된 계좌를 선택하면 **증권사, 계좌명, 소유자**가 1초 만에 자동 완성됩니다.

### 4. 🔍 지능형 종목코드 자동 검색 및 자동 채움 (`StockMaster`)
- **보유종목 직접 추가**, **실현손익 추가**, **배당금 추가** 팝업에서 **종목코드 없이 종목명만 입력해도 종목코드(국내 6자리/미국 티커)와 통화가 실시간 자동 입력**됩니다.
- **대표 약칭/별칭 사전 탑재**:
  - `현대차` / `현차` ➔ **`005380`** (현대자동차)
  - `삼전` / `삼전우` ➔ **`005930`** / **`005935`** (삼성전자 / 삼성전자우)
  - `하닉` / `하이닉스` ➔ **`000660`** (SK하이닉스)
  - `네이버` ➔ **`035420`** (NAVER)
  - `LG엔솔` / `엔솔` ➔ **`373220`** (LG에너지솔루션)
  - `에코프로` / `에코비엠` ➔ **`086520`** / **`247540`**
  - `카뱅` ➔ **`323410`** (카카오뱅크)
  - `엔비디아` ➔ **`NVDA`**, `애플` ➔ **`AAPL`**, `테슬라` ➔ **`TSLA`** 등
- **토큰 분리 퍼지 검색**: `1Q나스닥` ➔ `0069M0` (1Q 미국나스닥100), `KODEX반도체` ➔ `091160` 자동 매칭.
- 종목코드를 끝까지 비워두고 [저장하기]를 눌러도 서버에서 자동으로 종목코드를 찾아 정상 저장하는 이중 안전망을 갖추고 있습니다.

### 5. 🍩 6대 세부 자산군 & 섹터별 투자자산 분류
- 자산군을 **🇰🇷 국내주식**, **📈 국내ETF**, **🌐 국내상장해외ETF**, **🗽 해외주식**, **🇺🇸 해외ETF**, **💵 현금·예수금**의 6대 핵심 자산군으로 정밀 분류합니다.
- 반도체, 대표지수·ETF, 2차전지, 금융·지주, 전력·인프라 등 섹터별 비중 및 도넛 차트를 지원합니다.

### 6. 📅 배당금 관리 (국내 ETF 분배율 연동 & 월별 캘린더 & 과거 환율 자동 계산)
- **예상 배당금 시뮬레이션**: 네이버 모바일 증권 API 및 KRX 신규 단축코드(`0069M0`, `0026S0` 등) 완벽 지원으로 국내 ETF(1Q ETF 3/6/9/12월 분기분배 등)의 실시간 분배율을 수집·추정합니다.
- **실제 배당금 원장 관리**: 계좌별 배당 입금 내역, 연도별 배당금 막대 차트 및 12개월 캘린더를 제공합니다.
- 달러(USD) 배당금은 **입금일 당시의 과거 실제 환율**을 자동 매칭하여 정확한 원화 배당 수령액을 계산합니다.

### 7. 💰 매도 실현손익 관리 (일반 주식 vs 📦 공모주 청약/매매 분리)
- 연도별/월별 누적 실현손익, 승률, 총 거래 건수를 제공하며, **일반 주식거래**와 **📦 공모주 청약/매매**를 탭별로 분리 관리할 수 있습니다.
- **환차손익 보정 정밀 엔진**:
  $$\text{최종 원화 실현손익} = (\text{USD 실현손익} \times \text{매도일 실제 환율}) + \text{환차손익(KRW)}$$
- 거래내역 수정 및 삭제 시 스크롤 위치가 튀지 않고 작업 위치를 100% 보존합니다.

### 8. 🌙 5대 테마 지원 & PWA & 안전한 원클릭 백업
- **다크 모드**, **라이트 모드**, **화이트 모드**, **오션 블루**, **포레스트 그린** 등 다양한 테마를 지원합니다.
- **PWA(Progressive Web App)** 지원으로 모바일 기기(아이폰/안드로이드)에서 '홈 화면에 추가'하여 앱처럼 사용할 수 있습니다.
- 최하단 **[💾 데이터 저장하기]** 버튼 클릭 시 전체 데이터가 `asset-dashboard_YYYY-MM-DD.json` 파일로 안전하게 통합 백업됩니다.

---

## 🔑 환경변수(.env) 설정 및 OpenAPI 연동

프로젝트 루트의 `.env.example` 파일을 복사하여 `.env` 파일을 생성한 뒤 필요한 값을 설정합니다:

```bash
cp .env.example .env
```

### 1. 토스증권 OpenAPI 연동 (선택)
토스증권 계좌의 보유종목과 실시간 예수금을 자동으로 불러옵니다.
1. [토스증권 WTS](https://wts.tossinvest.com) > 설정 > **Open API**에서 `Client ID`와 `Client Secret`을 발급받습니다.
2. 허용 IP 관리에 대시보드를 실행할 PC/서버의 **공인 IP**를 등록합니다.
3. `.env` 파일에 입력:
   ```env
   TOSSINVEST_OPENAPI_BASE_URL=https://openapi.tossinvest.com
   TOSSINVEST_CLIENT_ID=your_client_id_here
   TOSSINVEST_CLIENT_SECRET=your_client_secret_here
   ```

### 2. KB증권 OpenAPI 연동 (선택)
1. [KB증권 개발자 포털](https://developer.kbsec.com)에서 App Key와 App Secret을 발급받습니다.
2. `.env` 파일에 입력:
   ```env
   KB_OPENAPI_BASE_URL=https://developer.kbsec.com:32484
   KB_OPENAPI_APP_KEY=your_kb_app_key_here
   KB_OPENAPI_APP_SECRET=your_kb_app_secret_here
   ```

### 3. NH투자증권(나무) NHPLUG OpenAPI 연동 (선택)
1. NHPLUG 포털에서 App Key와 App Secret을 발급받습니다.
2. `.env` 파일에 입력:
   ```env
   NHPLUG_BASE_URL=https://api.nhplug.com:8443
   NHPLUG_AUTH_URL=https://api.nhplug.com:8443
   NHPLUG_APP_KEY=your_nh_app_key_here
   NHPLUG_APP_SECRET=your_nh_app_secret_here
   ```

### 4. 대시보드 로그인 보안 설정 (선택)
외부 네트워크나 모바일에서 접속 시 비밀번호 보호를 설정할 수 있습니다.
```env
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your_secure_password
DASHBOARD_SECRET_KEY=generate_a_long_random_secret_key_here
```
> ※ 값을 비워두면 로그인 절차 없이 바로 대시보드가 열립니다.

---

## 📂 엑셀 / CSV 파일 일괄 가져오기

OpenAPI를 지원하지 않는 증권사나 과거 거래 내역은 화면의 **[📂 가져오기]** 버튼을 통해 엑셀(.xlsx) 또는 CSV로 한 번에 등록할 수 있습니다. 팝업에서 통일된 표준 샘플 파일을 다운로드할 수 있습니다.

### 📋 지원 샘플 파일 목록
1. **`샘플_타증권사_보유종목.xlsx`** (보유종목 가져오기)
   * `[소유자 | 증권사 | 계좌명 | 종목코드 | 종목명 | 보유수량 | 평균매입가 | 현재가 | 통화]`
2. **`샘플_배당.xlsx`** (배당내역 가져오기)
   * `[소유자 | 증권사 | 계좌명 | 입금일 (Date) | 종목코드 | 종목명 | 통화 | 실제 배당금 (입금액) | 메모]`
3. **`샘플_매도실현손익.xlsx`** (매도 실현손익 가져오기)
   * `[소유자 | 증권사 | 계좌명 | 매도일 (Date) | 종목코드 | 종목명 | 통화 | 실현손익 | 환차손익 | 공모주 여부 | 메모]`

> 💡 **스마트 자동 완성**: 종목코드나 종목명 중 하나만 적혀있어도 자동으로 상호 매칭되며, 날짜에 맞는 과거 환율이 자동 계산됩니다.

---

## 🖥️ Windows 설치 및 사용 방법

### 1. 사전 요구사항
- [Python 3.11 이상](https://www.python.org/downloads/) 설치 (설치 시 `Add Python to PATH` 체크)

### 2. 설치 및 환경 구성
프로젝트 폴더에서 PowerShell 또는 명령 프롬프트를 엽니다:

```powershell
# 1. 가상환경 생성
py -m venv .venv

# 2. 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# 3. 필수 패키지 설치
pip install -r requirements.txt

# 4. 환경변수 파일 생성
copy .env.example .env
```

### 3. 실행 방법
- **방법 1 (간편 실행)**: 프로젝트 폴더의 **`대시보드_실행.cmd`** 파일을 더블클릭하면 서버 시작과 함께 브라우저(`http://127.0.0.1:4829`)가 자동으로 열립니다.
- **방법 2 (터미널 실행)**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  python -m uvicorn app.main:app --host 127.0.0.1 --port 4829 --reload
  ```

---

## 🐧 Linux / Docker 설치, 실행 및 업데이트 방법

서버(Ubuntu, Debian, Synology NAS 등)에서 Docker와 Docker Compose를 사용하여 손쉽게 구동하고 관리할 수 있습니다.

### 1. Docker로 최초 설치 및 실행

```bash
# 1. 저장소 복제
git clone https://github.com/your-username/asset-dashboard.git
cd asset-dashboard

# 2. 환경변수 파일 설정
cp .env.example .env
# nano .env 또는 vi .env 로 필요한 설정(로그인 계정 등) 수정

# 3. 데이터 디렉터리 권한 확인
mkdir -p data

# 4. Docker Compose 빌드 및 백그라운드 실행
docker compose up -d --build
```

실행 후 웹 브라우저에서 `http://서버IP:4829`로 접속합니다.

### 2. Docker 컨테이너 상태 및 로그 확인

```bash
# 실행 상태 확인
docker compose ps

# 실시간 로그 확인
docker compose logs -f
```

### 3. 최신 버전 업데이트 방법

새로운 기능이나 패치가 릴리즈되었을 때 기존 데이터(`data/` 폴더)를 그대로 유지하면서 업데이트하는 방법입니다:

```bash
# 1. 대시보드 디렉터리로 이동
cd asset-dashboard

# 2. 최신 소스코드 pull
git pull origin main

# 3. 컨테이너 무중단 재빌드 및 재시작
docker compose up -d --build
```
> 💾 **데이터 안전 보장**: 모든 보유종목, 배당내역, 실현손익 데이터는 호스트의 `./data` 디렉터리에 볼륨 마운트되어 있으므로 컨테이너를 재빌드하거나 삭제해도 데이터가 안전하게 보존됩니다.

---

## 🛡️ 보안 및 개인정보 보호 안내

1. **100% 로컬 저장 원칙**:
   - 모든 자산 데이터, 배당 기록, 실현손익 데이터는 사용자의 로컬 `data/` 폴더 내 JSON 파일로만 저장되며, 외부 중앙 서버로 일체 전송되지 않습니다.
2. **조회 전용 (안전한 자산 관리)**:
   - 본 프로그램에는 매매 주문, 출금, 이체 등 자산을 이동시키는 기능이 일체 포함되어 있지 않으며 오직 조회(Read-Only) 기능만 수행합니다.
3. **GitHub 보안 클린**:
   - `.env` 및 `data/` 폴더, 개인 엑셀 파일은 `.gitignore`에 등록되어 있어 GitHub에 코드를 push해도 개인 금융 데이터나 API 키가 유출되지 않습니다.

---

<div align="center">
  <sub>Built with ❤️ for personal wealth management.</sub>
</div>
