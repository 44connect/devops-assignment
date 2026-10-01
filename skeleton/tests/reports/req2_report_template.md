# requirement_2 검증 Report (TE)

| 항목 | 내용 |
|------|------|
| **프로젝트** | webOS Subscription Management Dashboard |
| **검증 대상** | requirement_2.md (가전 목록 + 사용 현황 + 차트) |
| **검증 일시** | 2026-10-01 16:35:30 |
| **작성자** | 김민지 |

**총 32건 중 PASS 32 / FAIL 0 — Pass Rate 100.0%**

| TC ID | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |
|:-----:|----------------|-----------|-----------|:----:|
| DEV-01 | get_devices_by_user("U001") 직접 호출 | D001, D002 반환 | ['D001', 'D002'] | ✅ PASS |
| DEV-02 | get_device_usage("D001") 직접 호출 | D001 사용 현황 dict 반환 | deviceId=D001 | ✅ PASS |
| DEV-03 | selectSubscriber() 구현 | 선택 갱신 → 사용 현황 초기화 → /devices 호출 → renderDevices() | 구현됨 | ✅ PASS |
| DEV-04 | renderDevices() 검색/필터 + 빈 목록 메시지 + 행 클릭 | filter / 소문자 비교 / 안내 메시지 2종 / selectDevice / badge | 모두 구현 | ✅ PASS |
| DEV-05 | selectDevice() 구현 | 선택 갱신 → /usage 호출 → usage-info 렌더링 → renderUsageChart() | 구현됨 | ✅ PASS |
| DEV-06 | renderUsageChart() 구현 | 기존 차트 destroy / bar 타입 / Mon~Sun / beginAtZero | 구현됨 | ✅ PASS |
| DEV-07 | 가전 검색/필터 이벤트 리스너 주석 해제 | 둘 다 활성화 | 활성화 | ✅ PASS |
| TE-1 | /api/subscribers/U001/devices 호출 | 200 + 2개 가전 (D001, D002) | status=200, ['D001', 'D002'] | ✅ PASS |
| API-01 | 가전 응답 필드 검증 | deviceId/type/model/location/status/lastSeen 모두 존재 | 모든 항목 정상 | ✅ PASS |
| TE-2 | /api/subscribers/U005/devices 호출 | 200 + 빈 배열 [] | status=200, body=[] | ✅ PASS |
| TE-3 | /api/subscribers/U999/devices 호출 | 404 에러 | status=404 | ✅ PASS |
| TE-4 | U001 클릭 시 가전 Table 표시 | D001, D002 표시 | ['D001', 'D002'] / selectSubscriber 구현 | ✅ PASS |
| TE-5 | U005 클릭 시 안내 메시지 | "No registered devices" 표시 | 가전 0개 / 메시지 있음 | ✅ PASS |
| TE-6 | U001 가전 검색 "TV" 입력 | TV 타입만 표시 (D001) | ['D001'] | ✅ PASS |
| TE-7 | U003 가전 상태 필터 "Online" 선택 | Online 가전만 표시 (D004, D005) | ['D004', 'D005'] | ✅ PASS |
| TE-8 | /api/devices/D001/usage 호출 | 200 + 사용 현황 9개 필드 | status=200, 필드 정상 | ✅ PASS |
| TE-9 | /api/devices/D999/usage 호출 | 404 에러 | status=404 | ✅ PASS |
| TE-10 | D001 클릭 시 사용 현황 표시 | 전원 On / 누적 152시간 / 주간 18회 / Normal 등 8개 항목 렌더링 | 값 정상, 8개 항목 렌더링 | ✅ PASS |
| TE-11 | D001 클릭 시 Bar Chart 표시 | Mon~Sun 7개 값 [2, 3, 1, 4, 2, 3, 3] + bar 차트 구현 | [2, 3, 1, 4, 2, 3, 3] / 차트 구현 | ✅ PASS |
| TE-12 | 다른 가전(D002) 클릭 시 차트 갱신 | 이전 차트 destroy + 새 데이터 [0, 1, 0, 1, 1, 0, 1] | [0, 1, 0, 1, 1, 0, 1] / destroy 있음 | ✅ PASS |
| TE-13 | 가전 검색 소문자 "tv" (대소문자 무시) | D001 표시 | ['D001'] | ✅ PASS |
| TE-14 | 가전 검색 "WashTower" (모델명) | D002 표시 | ['D002'] | ✅ PASS |
| TE-15 | 가전 검색 "Dormitory" (위치) | D001 표시 | ['D001'] | ✅ PASS |
| TE-16 | 가전 검색 "Error" (상태) | D006 표시 | ['D006'] | ✅ PASS |
| TE-17 | 상태 필터 Offline(U001) / Standby(U004) / Error(U003) | D002 / D008 / D006 | {'Offline': ['D002'], 'Standby': ['D008'], 'Error': ['D006']} | ✅ PASS |
| TE-18 | U003 검색 "LG" + 필터 "Online" 동시 적용 | D004, D005 표시 | ['D004', 'D005'] | ✅ PASS |
| TE-19 | U002 상태 필터 "Error" (일치 없음) | 0개 → "No devices matched" | 0개 | ✅ PASS |
| DATA-01 | 가전 status 값 범위 | Online / Offline / Standby / Error 중 하나 | 8개 모두 정상 | ✅ PASS |
| DATA-02 | 목록의 모든 가전에 사용 현황 존재 | 가전 목록의 모든 deviceId 가 /usage 200 | 8개 모두 존재 | ✅ PASS |
| DATA-03 | 사용 현황 deviceId / deviceName = 가전 목록 deviceId / model | 모두 일치 | 모두 일치 | ✅ PASS |
| DATA-04 | weeklyUsageTrend 형식 | 모든 가전 7개(Mon~Sun), 0 이상 정수 | 모두 정상 | ✅ PASS |
| DATA-05 | powerStatus / healthStatus 값 범위 | On/Off/Standby/Error/Cleaning, Normal/Warning | 모두 정상 | ✅ PASS |

## 수동 브라우저 검증 (직접 확인 후 기입)

> 위 자동 결과 중 검색/필터는 app.js 규칙을 파이썬으로 재현한 결과이고,
> 화면 표시·차트는 코드 구현 여부만 확인한 것입니다.
> 실제 화면 동작은 아래 항목을 브라우저에서 확인해 판정란에 PASS / FAIL 을 적으세요.

| ID | 확인 방법 | 기대 결과 | 실제 결과 | 판정 |
|:--:|----------|-----------|-----------|:----:|
| UI-01 | U001 행 클릭 | U001 행 selected 강조 + 가전 Table 에 D001, D002 표시 | U001 강조, D001·D002 표시 | ✅ PASS |
| UI-02 | U005 행 클릭 | "No registered devices" 메시지 표시 | "No registered devices" 표시 | ✅ PASS |
| UI-03 | U001 선택 후 가전 검색창에 "tv" 입력 | 입력 즉시 D001 만 표시 (대소문자 무시) | D001만 표시 | ✅ PASS |
| UI-04 | U003 선택 후 상태 필터 Online → Error 변경 | Online: D004, D005 / Error: D006 | Online: D004, D005 / Error: D006 | ✅ PASS |
| UI-05 | U002 선택 후 상태 필터 "Error" | "No devices matched" 메시지 표시 | "No devices matched" 표시 | ✅ PASS |
| UI-06 | U001 → D001 행 클릭 | Device ID, Name, Power, Last Used, Total Hours, Weekly Count, Health, Remark 8개 표시 | 8개 항목 표시 | ✅ PASS |
| UI-07 | D001 Bar Chart | Mon~Sun 막대, 값 2, 3, 1, 4, 2, 3, 3 / y축 0 부터 시작 | Mon~Sun 2, 3, 1, 4, 2, 3, 3 | ✅ PASS |
| UI-08 | D001 → D002 클릭 | 차트가 0, 1, 0, 1, 1, 0, 1 로 교체 (마우스 올려도 이전 차트 안 보임) | 0, 1, 0, 1, 1, 0, 1 로 교체, 이전 차트 없음 | ✅ PASS |
| UI-09 | D001 선택 상태에서 다른 구독자(U003) 클릭 | 사용 현황이 "Select a device to view usage details." 로 초기화 | 사용 현황 초기화 | ✅ PASS |
| UI-10 | 개발자도구(F12) Console 탭 | JS 에러 없음 (favicon.ico 404 는 제외) | 에러 없음 | ✅ PASS |

## 확인 필요 사항

- D007(LG CordZero R5)의 `powerStatus` 가 `Cleaning` 입니다. 오리엔테이션 명세(On / Off / Standby / Error)에는 없는 값이지만 app.js 배지 규칙(노랑)에는 있어 DATA-05 에서 허용했습니다. PM 확인 필요.

> 본 Report 는 `tests/req2_test_template.py` 로 생성되었습니다.
