v4.2.0

(feat) admin/admin 등 초기 비밀번호 계정 로그인 시 대시보드 진입 전 비밀번호 변경 전용 페이지(/change-password-init) 강제 라우팅
(security) 비밀번호를 변경하기 전까지는 대시보드(/dashboard) URL을 직접 입력해도 접근 불가 차단
(fix) admin 화면에서 사용자 계정 목록 테이블 렌더링 시 escapeHtml 참조 오류 수정 (사용자 목록 정상 표시)
(perf) 서비스 워커 캐시 버전(wealth-cache-v5) 및 스크립트 쿼리(v412) 갱신

v4.1.1

(fix) 프론트엔드 API 통신 헬퍼(api) 누락 바인딩 수정 및 fetchJson 별칭 연동
(fix) 서비스 워커 캐시 버전(wealth-cache-v4) 갱신 및 구버전 JS/CSS 클라이언트 캐시 자동 무효화
(fix) 초기 비밀번호 강제 변경 모달(#forcePasswordModal) 백드롭 스타일 및 중앙 팝업 레이아웃 보강
(fix) admin 로그인 시 비동기 세션 검증 후 화면 분기(applyUserRoleView) 안정화

v4.1.0

(feat) admin 로그인 시 자산관리 화면 제외 및 사용자 관리 메인 전용 대시보드(#adminMainPanel) 노출
(security) admin/admin 초기 로그인 시 1회 비밀번호 강제 변경 전까지 모든 자산/관리 API 호출 403 차단 보안 가드 구축
(feat) admin 사용자 계정 관리 메인 화면에 통계 요약 카드(총 사용자, 활성 사용자, 초기비번 대기자) 및 신규 아이디 발급 폼 탑재
(perf) admin 접속 시 자산 관련 API 호출 및 시세 크롤링 연산 전면 생략으로 서버 및 브라우저 성능 극대화
(fix) 로그아웃 후 원하는 사용자 계정(admin, sagesaint, user2 등)으로 자유롭게 로그인할 수 있도록 로컬 미들웨어 인증 흐름 정돈

v4.0.0

(feat) 사용자별 완벽 데이터 격리(Multi-User Isolation) 및 사용자 관리 시스템 구축
(feat) 사용자별 개별 데이터 폴더(data/users/{username}/) 격리 저장 및 기존 sagesaint 데이터 100% 무손실 자동 마이그레이션
(security) PBKDF2-HMAC-SHA256(10만 회) 솔트 기반 안전한 비밀번호 단방향 암호화 DB(data/users.json) 적용
(security) 초기 관리자(admin/admin) 접속 시 비밀번호 변경 강제(forced password change) 보안 가드 연동
(feat) 관리자(Admin) 전용 사용자 계정 관리 팝업 탑재: 신규 아이디 추가(초기 비번 4자리 지정), 비밀번호 4자리 리셋, 계정 삭제(데이터 폴더 동시 파기)
(feat) 신규 등록 계정 첫 로그인 시 4자리 초기 비밀번호 검증 후 새 비밀번호(4자 이상) 변경 필수 모달 연동
(feat) 상단 헤더 현재 접속자 배지(👤 아이디), 관리자 전용 [⚙️ 사용자 관리], [🔑 비번 변경], [로그아웃] 연동
(perf) 5년치 환율 및 종목 마스터는 공용 공유 캐시(data/)로 분리하여 서버 리소스 최적화

v3.3.9

(feat) MDN 공식 PWA 표준 규격 완벽 준수 및 오프라인 캐시 서비스 워커 전면 개편
(feat) W3C 표준 Web App Manifest (/manifest.json) 루트 스코프 및 192/512px any/maskable 아이콘 4종 완비
(feat) 서비스 워커 (/sw.js) 루트 스코프 등록 및 사전 리소스 프리캐싱(Pre-caching) 탑재
(design) 브라우저 PWA 설치 감지 엔진(beforeinstallprompt) 및 상단 앱 설치 버튼 연동

v3.3.8

(fix) 삼성인터넷 PWA WebAPK 독립 앱 설치 호환성을 위해 v2.2.0 검증 설정으로 완벽 복원
(fix) 매니페스트(/static/manifest.json) 및 서비스 워커(/static/sw.js) 경로 원형 동기화
(feat) 안드로이드 자동회전 시스템 설정 연동 유지 (세로 고정 시 강제 회전 방지)

v3.3.7

(fix) PWA 매니페스트 시작 경로(/dashboard) 및 Standalone 설정 안정화 원복
(fix) 오라클/사설 환경에서 WebAPK 민팅 오류 방지 및 전체화면(Standalone) 바로가기 호환성 최적화

v3.3.6

(fix) PWA WebAPK 독립 앱 설치 시 전체화면(Standalone) 미적용 및 브라우저 탭 실행 오류 수정
(feat) 백엔드 인증 미들웨어 내 /manifest.json 및 /sw.js 루트 공개 경로(PUBLIC_PATHS) 등록
(feat) /sw.js 루트 스코프 서빙 및 Service-Worker-Allowed 헤더 지원
(design) 안드로이드 크롬 전용 전체화면 메타 태그(mobile-web-app-capable) 및 display_override 규격 추가

v3.3.5

(fix) PWA 모바일 기기 화면 회전 시 스마트폰 시스템 설정 연동 (세로 고정 시 강제 가로 회전 방지)
(feat) 기간별 변동률 산출 기준을 캘린더 실제 날짜 기반으로 전면 개편 (주간 7일 전, 월간 1개월 전, 연간 1년 전 날짜 매칭 및 휴일 자동 보정)
(fix) 자산기록 콤보차트 일간(2일) 및 주간(5일) 데이터 포인트 및 막대 위치 중앙 정렬 최적화 (양 끝 쏠림 현상 해결)
(design) 주요지수/자산히트맵/종목차트 기간 탭 일간/주간/월간/연간 표준화 및 모바일 컴팩트 스타일 적용
(feat) 주요지수 섹션 접힘 상태에서도 계좌 연결 및 조회 버튼 상시 클릭 허용

v3.3.4

(add) 보유종목/실현손익/배당금 전체 팝업에 종목명 기반 종목코드 실시간 자동 검색 및 채움 엔진 연동
(add) 실현손익 및 배당금 팝업 내 등록된 계좌(ACCOUNTS) 원클릭 선택 및 자동 채움 지원

(add) 반도체지수 추가
(fix) 핵심요약(OVERVIEW) 총수익 및 일간 수익 3줄 분리 표시
(clean) 파일명 인코딩 정돈 및 전체 17개 API 엔드포인트 무결성 검증 완료



v3.3.3

(add) 종목코드자동입력



v3.3.2

(fix) 예상 배당금 누락 수정



v3.3.1

(fix) 실현손익 배당금 기간 수정



v3.3.0

(add) 가져오기 종목명 종목코드 연동



v3.2.2

(feature) 주제별 숨김 추가



v3.2.1

(feature) 테마 적용



v3.2.0

(feature) 배당금, 실현 수익 추가



v3.1.1

&#x20;(fix) 표시 개선

&#x20;(fix)더미 데이터 삭제



v3.1.0

(add)연동 방법 toss openapi에서 야후파이낸스 및 네이버증권으로 변경

(add)투자자산 섹터별 분류 추가

(add)자산 기록 기간 추가, 표현 그래프 변경, 월별 자산 추가

(add) 카드형 히트맵 추가

(add) 보유종목 차트 추가



v3.0.1

(fix)모바일 접속 화면 수정



v3.0.0

(add)가족 구성원 추가 관리 기능

(add)데이터 저장하기 및 불러오기 기능

