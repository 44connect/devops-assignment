# requirement_3 검증 Report (TE)

| 항목 | 내용 |
|------|------|
| **프로젝트** | webOS Subscription Management Dashboard |
| **검증 대상** | requirement_3.md (상태 badge + CI/CD) |
| **검증 일시** | 2026-10-01 17:04:25 |
| **작성자** | 김민지 |

**총 19건 중 PASS 19 / FAIL 0 — Pass Rate 100.0%**

| TC ID | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |
|:-----:|----------------|-----------|-----------|:----:|
| DEV-01 | badgeClass() 매핑 표 12개 값 | 표와 같은 CSS 클래스 | 12개 일치 (node 실행) | ✅ PASS |
| DEV-02 | 대소문자 무시 / 모르는 값·빈 값·null → 기본 badge | ACTIVE·online → status-active, 나머지 → badge | 모두 기대값 (node 실행) | ✅ PASS |
| DEV-03 | style.css 색상 클래스 6개 정의 + 색상 | status-active 초록 / paused 파랑 / expired 빨강 / offline 회색 / on 노랑 / off 회색 | 6개 모두 정의, 색상 일치 | ✅ PASS |
| DEV-04 | badge 적용 위치 | 구독 상태 / 가전 상태 / 전원·건강 상태 모두 badgeClass() 사용 | 3곳 모두 적용 | ✅ PASS |
| TE-1 | Active 상태 구독자 확인 | Active → 초록 badge | U001 status=Active → badge status-active (초록) | ✅ PASS |
| TE-2 | Paused 상태 구독자 확인 | Paused → 파랑 badge | U003 status=Paused → badge status-paused (파랑) | ✅ PASS |
| TE-3 | Expired 상태 구독자 확인 | Expired → 빨강 badge | U005 status=Expired → badge status-expired (빨강) | ✅ PASS |
| TE-4 | Online 상태 가전 확인 | Online → 초록 badge | D001 status=Online → badge status-active (초록) | ✅ PASS |
| TE-5 | Offline 상태 가전 확인 | Offline → 회색 badge | D002 status=Offline → badge status-offline (회색) | ✅ PASS |
| TE-6 | Error 상태 가전 확인 | Error → 빨강 badge | D006 status=Error → badge status-expired (빨강) | ✅ PASS |
| TE-7 | Power On 상태 확인 | On → 노랑 badge | D001 powerStatus=On → badge status-on (노랑) | ✅ PASS |
| TE-8 | Health Normal 상태 확인 | Normal → 초록 badge | D001 healthStatus=Normal → badge status-active (초록) | ✅ PASS |
| TE-9 | Health Warning 상태 확인 | Warning → 빨강 badge | D006 healthStatus=Warning → badge status-expired (빨강) | ✅ PASS |
| TE-14 | Standby 상태 가전 확인 | Standby → 파랑 badge | D008 status=Standby → badge status-paused (파랑) | ✅ PASS |
| TE-15 | Power Cleaning 상태 확인 | Cleaning → 노랑 badge | D007 powerStatus=Cleaning → badge status-on (노랑) | ✅ PASS |
| TE-16 | Power Off 상태 확인 | Off → 회색 badge | D002 powerStatus=Off → badge status-off (회색) | ✅ PASS |
| TE-17 | Power Standby 상태 확인 | Standby → 파랑 badge | D004 powerStatus=Standby → badge status-paused (파랑) | ✅ PASS |
| TE-18 | Power Error 상태 확인 | Error → 빨강 badge | D006 powerStatus=Error → badge status-expired (빨강) | ✅ PASS |
| DATA-01 | 데이터의 모든 상태 값에 색상 지정 | 기본 badge(색 없음)로 나오는 값 없음 | 12개 값 모두 색상 지정: ['Active', 'Cleaning', 'Error', 'Expired', 'Normal', 'Off', 'Offline', 'On', 'Online', 'Paused', 'Standby', 'Warning'] | ✅ PASS |

## 수동 검증 (화면 / CI / 배포)

> 자동 결과의 색상은 badgeClass() 결과와 style.css 의 글자색으로 판정한 것입니다.
> 실제 화면, GitHub Actions, Render 배포는 직접 확인한 뒤 `tests/manual/req3_manual.json` 에 기록하면
> 스크립트를 다시 실행해도 아래 표에 그대로 반영됩니다. (자동 Pass Rate 에는 포함되지 않음)
> 수동 확인 일시: 2026-10-01

| ID | 확인 방법 | 기대 결과 | 실제 결과 | 판정 |
|:--:|----------|-----------|-----------|:----:|
| UI-01 | 구독자 Table Status 컬럼 | Active 초록 / Paused 파랑 / Expired 빨강 | Active 초록 / Paused 파랑 / Expired 빨강 | ✅ PASS |
| UI-02 | U001 클릭 → 가전 Table | D001 Online 초록 / D002 Offline 회색 | D001 Online 초록 / D002 Offline 회색 | ✅ PASS |
| UI-03 | U003 클릭 → D006 클릭 | 가전 상태 Error 빨강 / Power Status Error 빨강 / Health Status Warning 빨강 | Error 빨강 / Power Error 빨강 / Health Warning 빨강 | ✅ PASS |
| UI-04 | U004 클릭 → D007, D008 클릭 | D008 Standby 파랑 / D007 Power Cleaning 노랑 / D008 Power Standby 파랑 | D008 Standby 파랑 / D007 Cleaning 노랑 / D008 Power Standby 파랑 | ✅ PASS |
| UI-05 | U001 → D001, D002 클릭 | D001 Power On 노랑 + Health Normal 초록 / D002 Power Off 연회색 | Power On 노랑, Health Normal 초록 / Power Off 연회색 | ✅ PASS |
| UI-06 | U003 행 클릭 (선택 행 안의 Paused badge) | 선택 행 배경과 badge 가 구분되어 보임 | 선택 행 안에서도 Paused badge 구분 가능 (배경색이 비슷해(#dbeafe / #e0e7ff) 대비는 낮음, 개선 권장) | ✅ PASS |
| UI-07 | 개발자도구(F12) Console 탭 | JS 에러 없음 | JS 에러 없음 | ✅ PASS |
| CI-10 | dev / main 에 push 또는 PR | GitHub Actions 탭에서 CI 자동 실행 | dev push(#36833392179), PR(#36833348490) 시 자동 실행 확인 (main 은 아직 merge 전이라 dev 기준) | ✅ PASS |
| CI-11 | CI 로그: 서버 기동 + /health | 통과 (초록 체크) | Build and test 단계에서 서버 기동 + /health 통과 (run #36833644760) | ✅ PASS |
| CI-12 | CI 로그: API 테스트 | 3개 엔드포인트 포함 검증 테스트 전체 통과 | make ci: req1 22/22, req2 32/32 PASS (3개 엔드포인트 포함) | ✅ PASS |
| CI-13 | CI 통과 후 Render 배포 | https://<서비스>.onrender.com 접속 + /health OK |  | 미확인 |

> 본 Report 는 `tests/req3_test_template.py` 로 생성되었습니다.
