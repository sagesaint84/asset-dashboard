# 📊 내 자산 대시보드 (My Asset Dashboard)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Supported-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)
![MultiUser](https://img.shields.io/badge/Multi--User-Isolated-success?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**멀티 유저 데이터 완전 격리 · 관리자/사용자 역할 분리 · 증권사 OpenAPI 개별 연동 · 실시간 시세/환율 · 배당금 및 실현손익 정밀 관리 로컬 자산 관리 플랫폼**

</div>

---

## 📑 목차
- [✨ 주요 기능](#-주요-기능)
- [👥 멀티 유저 격리 시스템 & 관리자 권한](#-멀티-유저-격리-시스템--관리자-권한)
- [⚙️ 웹 UI를 통한 증권사 OpenAPI 설정 & 삭제](#️-웹-ui를-통한-증권사-openapi-설정--삭제)
- [🔑 환경변수(.env) 초기 설정](#-환경변수env-초기-설정)
- [📂 엑셀 / CSV 파일 일괄 가져오기](#-엑셀--csv-파일-일괄-가져오기)
- [🖥️ Windows 설치 및 실행 방법](#️-windows-설치-및-실행-방법)
- [🐧 Linux / Docker 설치, 실행 및 업데이트 방법](#-linux--docker-설치-실행-및-업데이트-방법)
- [🛡️ 보안 및 개인정보 보호 원칙](#️-보안-및-개인정보-보호-원칙)

---

## ✨ 주요 기능

### 1. 👥 멀티 유저 완벽 데이터 격리 (Multi-User Dashboard)
- **사용자별 전용 저장소**: 각 사용자별 데이터(`portfolio.json`, `asset_records.json`, `dividend_records.json`, `realized_pnl_records.json`, `openapi_config.json`)가 `data/users/{username}/` 디렉터리에 완벽히 격리되어 타인의 자산 데이터나 인증키가 섞이지 않습니다.
- **역할 분리 (Admin vs User)**:
  - **`admin` (시스템 관리자)**: 대시보드 화면 대신 **사용자 계정 관리 전용 콘솔** 단독 제공. 신규 사용자 생성(초기 4자리 비밀번호 발급), 비밀번호 4자리 강제 초기화, 계정 삭제 권한 보유.
  - **`user` (일반 사용자, `sagesaint` 등)**: 본인만의 독립된 자산 대시보드 화면 및 개별 OpenAPI 인증키 설정 화면 제공.
- **초기 비밀번호 강제 변경 프로세스**: 신규 발급받은 초기 4자리 비밀번호로 로그인 시 대시보드 진입이 원천 차단되며, 전용 비밀번호 변경 화면(`/change-password-init`)에서 안전한 비밀번호로 변경한 후에만 대시보드 사용이 가능합니다.

### 2. ⚙️ 증권사 OpenAPI 웹 UI 개별 등록 및 삭제
- 웹 화면 상단 **`[⚙️ OpenAPI]`** 버튼을 통해 각 증권사(토스증권, KB증권, 나무증권)의 AppKey 및 AppSecret을 간편하게 등록할 수 있습니다.
- 등록된 시크릿은 마스킹(`********`)되어 안전하게 보존되며, 필요 시 언제든지 각 증권사 카드 헤더의 **`[🗑️ 삭제]`** 버튼을 통해 즉시 인증키 및 캐시 토큰을 파기할 수 있습니다.
- 대시보드의 **`[🔗 계좌 연결]`** 버튼 클릭 시 본인이 등록한 증권사 계좌 및 예수금만 격리 동기화됩니다.

### 3. 📈 실시간 시장 지표 & 실시간 환율 & 스마트 시세 갱신
- 네이버 증권 및 야후 파이낸스 연동으로 **코스피, 코스닥, S&P 500, 나스닥, 필라델피아 반도체 지수**의 실시간 시세와 추이 차트를 제공합니다.
- **실시간 USD/KRW 환율**을 자동으로 수신하여 원화 및 달러 자산을 실시간 원화 가치로 정확하게 집계합니다.
- 주식 보유종목이 없는 신규 계정(예: 예수금만 보유 중인 상태)에서도 **`[↻ 조회]`** 버튼 클릭 시 오류 없이 **지수 및 환율을 정상 동기화**합니다.

### 4. 💵 배당금 관리 및 이자 항목(`원화이자`, `달러이자` 등) 지원
- **실제 배당금 원장 및 캘린더**: 계좌별 배당금 입금 내역, 연도별 배당금 막대 차트 및 12개월 캘린더를 제공합니다.
- **이자/현금성 배당 전용 코드 탑재**: 배당금 입력 시 `원화이자`(`INTEREST_KRW`), `달러이자`(`INTEREST_USD`), `RP이자`(`INTEREST_RP`), `예탁금이자`(`INTEREST_CASH`) 항목을 공식 지원하여 **화이자(Pfizer, PFE) 주식으로 오매칭되는 현상을 원천 방지**했습니다.
- 달러(USD) 배당금은 **입금일 당시의 실제 과거 환율**을 자동 매칭하여 정확한 원화 환산 배당액을 계산합니다.

### 5. 💰 매도 실현손익 관리 (일반 주식 vs 📦 공모주 분리)
- 연도별/월별 누적 실현손익, 승률, 총 거래 건수를 제공하며, **일반 주식거래**와 **📦 공모주 청약/매매**를 탭별로 분리 관리합니다.
- **환차손익 보정 정밀 엔진**:
  $$\text{최종 원화 실현손익} = (\text{USD 실현손익} \times \text{매도일 실제 환율}) + \text{환차손익(KRW)}$$

### 6. 🔍 지능형 종목 자동 검색 & 자동 완성 (`StockMaster`)
- 보유종목, 배당금, 실현손익 입력 시 종목명만 입력해도 종목코드(국내 6자리/미국 티커)와 통화가 자동 입력됩니다.
- 대표 약칭(`삼전`, `하닉`, `현차`, `엔비디아`, `테슬라` 등) 및 ETF 단축코드(`0069M0` 등)를 자동 판별합니다.

### 7. 📱 PWA (Progressive Web App) & 5대 테마 지원
- 웹 표준 Service Worker 및 Manifest 탑재로 모바일(iOS Safari / Android Chrome) 및 PC 브라우저에서 '홈 화면에 추가'하여 앱처럼 사용할 수 있습니다.
- **다크 모드**, **라이트 모드**, **화이트 모드**, **오션 블루**, **포레스트 그린** 등 다양한 테마를 지원합니다.

---

## 👥 멀티 유저 격리 시스템 & 관리자 권한

본 대시보드는 1대의 서버/PC에서 여러 사용자가 각자의 독립된 자산을 관리할 수 있는 **멀티 유저 통합 격리 아키텍처**를 제공합니다.

### 1. 계정 체계
| 구분 | 아이디 예시 | 역할(Role) | 화면 구성 | 접근 권한 |
| :--- | :--- | :---: | :--- | :--- |
| **시스템 관리자** | `admin` | `admin` | **사용자 계정 관리 전용 콘솔** | 사용자 목록 조회, 신규 아이디 추가, 비밀번호 4자리 초기화, 계정 삭제 |
| **일반 사용자** | `sagesaint`, `potato` 등 | `user` | **개인 투자 자산 대시보드** | 본인 자산/배당/손익 조회, 개별 OpenAPI 키 관리, 본인 비밀번호 변경 |

### 2. 관리자(Admin) 콘솔 사용 방법
1. 브라우저에서 `admin` 계정으로 로그인합니다. (최초 로그인 시 비밀번호 강제 변경 필수)
2. 자산 화면 대신 **사용자 관리 화면**이 메인으로 표시됩니다.
3. **새 사용자 추가**: 아이디와 초기 비밀번호 4자리를 입력하여 생성합니다.
4. **비밀번호 초기화**: 사용자가 비밀번호를 잊었을 때 임의의 4자리 비밀번호로 초기화합니다.
5. **사용자 삭제**: 계정 삭제 시 해당 유저의 폴더(`data/users/{username}/`)도 함께 안전하게 정리됩니다.

### 3. 신규 사용자 로그인 프로세스
1. 관리자가 생성해 준 아이디와 초기 4자리 비밀번호로 로그인합니다.
2. 대시보드로 바로 진입되지 않고 **비밀번호 변경 필수 안내 화면**이 나타납니다.
3. 새로운 비밀번호(4자 이상)로 변경 완료 즉시 대시보드로 자동 이동하여 본인만의 자산 관리를 시작할 수 있습니다.

---

## ⚙️ 웹 UI를 통한 증권사 OpenAPI 설정 & 삭제

소스코드나 `.env` 파일을 직접 열지 않고도 웹 화면에서 안전하게 OpenAPI 인증키를 관리할 수 있습니다:

1. 로그인 후 상단 헤더 우측의 **`[⚙️ OpenAPI]`** 버튼을 클릭합니다.
2. **토스증권**, **KB증권**, **NH투자증권(나무)**, **한국투자증권(KIS)**, **키움증권** 중 보유한 증권사의 AppKey와 AppSecret(계좌번호)을 입력하고 **[💾 설정 저장]**을 누릅니다.
3. 이미 등록된 키는 자동으로 안전하게 마스킹(`****`) 처리되어 계정별 폴더(`data/users/{username}/`)에 격리 보관됩니다.
4. 연결을 해제하거나 키를 변경하고 싶을 때는 상태 뱃지 옆의 **`[🗑️ 삭제]`** 버튼을 누르면 해당 증권사의 키와 토큰 캐시가 즉시 완전히 초기화됩니다.

---

## 📂 엑셀 / CSV 파일 일괄 가져오기

OpenAPI 미지원 증권사나 과거 거래 내역은 화면의 **`[📂 가져오기]`** 버튼을 통해 한 번에 등록할 수 있습니다:
1. **`샘플_타증권사_보유종목.xlsx`** (보유종목 가져오기)
2. **`샘플_배당.xlsx`** (배당내역 가져오기 - `원화이자`, `달러이자` 등도 그대로 지원)
3. **`샘플_매도실현손익.xlsx`** (매도 실현손익 가져오기)

---

## 🖥️ Windows 설치 및 실행 방법

### 1. 요구사항
- [Python 3.11 이상](https://www.python.org/downloads/) 설치 (`Add Python to PATH` 체크)

### 2. 가상환경 및 패키지 설치
```powershell
# 가상환경 생성 및 활성화
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 패키지 설치
pip install -r requirements.txt
```

### 3. 대시보드 실행
- **간편 실행**: 프로젝트 폴더의 **`대시보드_실행.cmd`** 파일을 더블클릭합니다.
- **터미널 실행**:
  ```powershell
  python -m uvicorn app.main:app --host 127.0.0.1 --port 4829
  ```

---

## 🐧 Linux / Docker 설치, 실행 및 업데이트 방법

```bash
# 1. 저장소 복제 및 이동
git clone https://github.com/sagesaint84/asset-dashboard.git
cd asset-dashboard

# 2. Docker Compose 빌드 및 실행
docker compose up -d --build

# 3. 최신 버전 업데이트 시 (데이터 보존)
git pull origin main
docker compose up -d --build
```

---

## 🛡️ 보안 및 개인정보 보호 원칙

1. **100% 로컬 저장 및 사용자별 폴더 격리**:
   - 모든 자산, 거래, 인증키 데이터는 서버 로컬의 `data/users/{username}/`에만 저장되며 외부 중앙 서버로 일체 전송되지 않습니다.
2. **조회 전용 (Read-Only)**:
   - 본 프로그램에는 매매 주문, 출금, 이체 기능이 일체 포함되어 있지 않으며 오직 조회만 수행합니다.
3. **GitHub 보안 클린**:
   - `.env` 및 `data/` 폴더 내 개인 금융 데이터와 인증 정보는 `.gitignore`로 보호되어 공개 저장소에 푸시되지 않습니다.

---

<div align="center">
  <sub>Built with ❤️ for personal and family wealth management.</sub>
</div>
