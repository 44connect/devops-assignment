# requirement_1 검증 Report (TE 실습)

| 항목 | 내용 |
|------|------|
| **프로젝트** | webOS Subscription Management Dashboard |
| **검증 대상** | requirement_1.md |
| **검증 일시** | 2026-10-01 16:41:19 |
| **작성자** | 김민지 |

**총 22건 중 PASS 22 / FAIL 0 — Pass Rate 100.0%**

| TC ID | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |
|:-----:|----------------|-----------|-----------|:----:|
| DEV-01 | get_subscribers() 함수 직접 호출 | 5명 반환 | 5명 반환 | ✅ PASS |
| API-01 | GET /api/subscribers 호출 | 200 OK | status=200 | ✅ PASS |
| TE-1 | /api/subscribers 호출 | 5명의 사용자 목록 반환 | 5명 | ✅ PASS |
| TE-3 | 검색창에 "Kim" 입력 | Kim Minsoo만 표시 | 1명: ['Kim Minsoo'] | ✅ PASS |
| DEV-02 | 응답 필드 검증 (userId/name/plan/status/deviceCount) | 모든 항목에 필드 존재, deviceCount는 number | 모든 항목 정상 | ✅ PASS |
| DEV-03 | fetchSubscribers() 구현 | /api/subscribers fetch 후 renderSubscribers() 호출 | 구현됨 | ✅ PASS |
| DEV-04 | renderSubscribers() 검색/필터 + 행 렌더링 + 행 클릭 | filter / 소문자 비교 / 행 생성 / 클릭 / selected 클래스 | 모두 구현 | ✅ PASS |
| DEV-05 | 이벤트 리스너 + 초기 fetchSubscribers() 주석 해제 | 셋 다 활성화 | 활성화 | ✅ PASS |
| API-02 | GET /health 호출 | 200 OK, {"status":"ok"} | status=200, body={'status': 'ok'} | ✅ PASS |
| TE-2 | 대시보드 접속 시 Table 자동 표시 | 5명 목록 표시 | 페이지 status=200 / 초기 호출 활성 / 5명 | ✅ PASS |
| TE-4 | 검색창에 "Premium" 입력 | Premium 플랜 사용자만 표시 (U001, U004) | 2명: ['U001', 'U004'] | ✅ PASS |
| TE-5 | 상태 필터 "Active" 선택 | Active 사용자만 표시 (U001, U002, U004) | 3명: ['U001', 'U002', 'U004'] | ✅ PASS |
| TE-6 | 상태 필터 "Expired" 선택 | Jung Hyerin만 표시 | 1명: ['Jung Hyerin'] | ✅ PASS |
| TE-7 | 검색("Kim") + 필터("Active" / "Expired") 동시 적용 | 두 조건 모두 만족하는 결과만 (U001 / 0명) | ['U001'] / 0명 | ✅ PASS |
| TE-8 | 검색어 삭제 시 | 전체 목록(5명) 복원 | 5명 | ✅ PASS |
| TE-9 | 검색창에 소문자 "kim" 입력 (대소문자 무시) | Kim Minsoo만 표시 | 1명: ['Kim Minsoo'] | ✅ PASS |
| TE-10 | 검색창에 "Active" 입력 (status 검색) | Active 사용자 전부 표시 (U001, U002, U004) | 3명: ['U001', 'U002', 'U004'] | ✅ PASS |
| TE-11 | 검색창에 "U003" 입력 (userId 검색) | Park Junho만 표시 | 1명: ['Park Junho'] | ✅ PASS |
| TE-12 | 검색창에 "zzz" 입력 (일치 없음) | 0명 표시 (빈 Table) | 0명 | ✅ PASS |
| DATA-01 | status 값 범위 | Active / Paused / Expired 중 하나 | 모두 정상 | ✅ PASS |
| DATA-02 | plan 값 범위 | Premium / Basic / Family 중 하나 | 모두 정상 | ✅ PASS |
| DATA-03 | deviceCount = 실제 등록 가전 수 | 모든 사용자 일치 (U005는 0) | 모두 일치 | ✅ PASS |

## 수동 브라우저 검증

> 위 자동 결과 중 검색/필터(TE-3~12)는 app.js 규칙을 파이썬으로 재현한 결과입니다.
> 실제 화면 동작은 브라우저에서 확인한 뒤 `tests/manual/req1_manual.json` 에 기록하면
> 스크립트를 다시 실행해도 아래 표에 그대로 반영됩니다. (자동 Pass Rate 에는 포함되지 않음)
> 수동 확인 일시: 2026-10-01

| ID | 확인 방법 | 기대 결과 | 실제 결과 | 판정 |
|:--:|----------|-----------|-----------|:----:|
| UI-01 | http://localhost:8000 접속 | 새로고침 없이 5명이 Table 에 표시 | 5명 자동 표시 | ✅ PASS |
| UI-02 | 검색창에 "kim" 을 한 글자씩 입력 | 입력할 때마다 즉시 목록이 줄어듦 (Enter 불필요) | 입력 즉시 목록 갱신 | ✅ PASS |
| UI-03 | 상태 필터 "Paused" 선택 | Park Junho 1명만 표시 | Park Junho 1명 | ✅ PASS |
| UI-04 | 검색 "Premium" + 필터 "Active" | U001, U004 표시 | U001, U004 표시 | ✅ PASS |
| UI-05 | 검색창에 "zzz" 입력 | "No subscribers matched" 메시지 표시 | "No subscribers matched" 표시 | ✅ PASS |
| UI-06 | 검색어 지우고 필터 All Status | 5명 전체 복원 | 5명 전체 복원 | ✅ PASS |
| UI-07 | Status 컬럼 Badge 색상 | Active 초록 / Paused 파랑 / Expired 빨강 (요구사항 #3 이후) | badgeClass() 미구현 (항상 "badge" 반환) (요구사항 #3 범위) | ➖ N/A |
| UI-08 | U001 행 클릭 | 행이 selected 로 강조 (selectSubscriber 는 요구사항 #2 범위) | selectSubscriber() 미구현 (빈 함수) (요구사항 #2 범위) | ➖ N/A |
| UI-09 | 개발자도구(F12) Console 탭 | 빨간 에러 없음 | JS 에러 없음. favicon.ico 404 1건 (아이콘 파일 없음, 기능 영향 없음) | ✅ PASS |

> 본 Report 는 `tests/req1_test_template.py` 로 생성되었습니다.
