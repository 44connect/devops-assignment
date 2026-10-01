"""
requirement_2.md 검증 스크립트  (TE)

실행 방법
--------
    # 프로젝트 루트(skeleton)에서
    python tests/req2_test_template.py

결과
----
    tests/reports/req2_report_template.md

필요 패키지: requirements.txt 의 패키지 외에는 파이썬 표준 라이브러리만 사용합니다.

────────────────────────────────────────────────────────────────────────
검증 흐름 (requirement_2.md 기준)
  1) 개발자 테스트  : API 함수가 값을 반환하는가? app.js 구현이 들어갔는가?
  2) API 테스트     : 가전 목록 / 사용 현황 API 와 404 처리가 동작하는가?
  3) TE 시나리오    : 가전 검색/필터, 사용 현황, 차트가 "기대 결과"대로인가?
  4) 데이터 검증    : 가전 목록과 사용 현황 데이터가 서로 맞는가?
────────────────────────────────────────────────────────────────────────
"""

import os
import re
import sys
import time
import json
import socket
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# Windows 콘솔(cp949)에서도 한글/기호가 깨지지 않도록 출력 인코딩을 UTF-8 로 설정
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# =============================================================================
# 경로 설정
# =============================================================================
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
REPORT_DIR = os.path.join(THIS_DIR, "reports")
REPORT_PATH = os.path.join(REPORT_DIR, "req2_report_template.md")

os.chdir(PROJECT_ROOT)          # 상대경로(app/static 등)를 위해 루트로 이동
BASE_URL = None                 # 서버 기동 후 채워짐

# 검증 결과를 담는 리스트. 각 항목: (TC ID, 시나리오, 기대결과, 실제결과, 통과여부)
results = []


def check(tc_id, scenario, expected, actual, passed):
    """검증 결과 1건을 기록한다."""
    results.append((tc_id, scenario, expected, actual, passed))
    tag = "PASS" if passed else "FAIL"
    print(f"  [{tag}] {tc_id}  {scenario}")


# =============================================================================
# HTTP 유틸
# =============================================================================
def http_get(path, timeout=5):
    """(status_code, json_data) 반환. 실패 시 (None, None)."""
    try:
        with urllib.request.urlopen(BASE_URL + path, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


DEVICE_FIELDS = {"deviceId", "type", "model", "location", "status", "lastSeen"}
USAGE_FIELDS = {"deviceId", "deviceName", "powerStatus", "lastUsedAt",
                "totalUsageHours", "weeklyUsageCount", "healthStatus",
                "remark", "weeklyUsageTrend"}
VALID_DEVICE_STATUS = {"Online", "Offline", "Standby", "Error"}
# 명세(오리엔테이션)는 On/Off/Standby/Error 이지만, 데이터(D007)와 app.js 배지 규칙에
# "Cleaning" 이 있어 허용값에 포함 (PM 확인 필요 사항으로 Report 에 기재)
VALID_POWER_STATUS = {"On", "Off", "Standby", "Error", "Cleaning"}
VALID_HEALTH_STATUS = {"Normal", "Warning"}

# 수동 브라우저 검증 항목 (자동 테스트가 볼 수 없는 실제 화면 동작)
#   (ID, 확인 방법, 기대 결과)  → Report 에 빈 칸으로 출력, 직접 확인 후 기입
MANUAL_CHECKS = [
    ("UI-01", "U001 행 클릭", "U001 행 selected 강조 + 가전 Table 에 D001, D002 표시"),
    ("UI-02", "U005 행 클릭", '"No registered devices" 메시지 표시'),
    ("UI-03", 'U001 선택 후 가전 검색창에 "tv" 입력', "입력 즉시 D001 만 표시 (대소문자 무시)"),
    ("UI-04", "U003 선택 후 상태 필터 Online → Error 변경", "Online: D004, D005 / Error: D006"),
    ("UI-05", 'U002 선택 후 상태 필터 "Error"', '"No devices matched" 메시지 표시'),
    ("UI-06", "U001 → D001 행 클릭",
     "Device ID, Name, Power, Last Used, Total Hours, Weekly Count, Health, Remark 8개 표시"),
    ("UI-07", "D001 Bar Chart", "Mon~Sun 막대, 값 2, 3, 1, 4, 2, 3, 3 / y축 0 부터 시작"),
    ("UI-08", "D001 → D002 클릭", "차트가 0, 1, 0, 1, 1, 0, 1 로 교체 (마우스 올려도 이전 차트 안 보임)"),
    ("UI-09", "D001 선택 상태에서 다른 구독자(U003) 클릭",
     '사용 현황이 "Select a device to view usage details." 로 초기화'),
    ("UI-10", "개발자도구(F12) Console 탭", "JS 에러 없음 (favicon.ico 404 는 제외)"),
]


def ids(items):
    return [d.get("deviceId") for d in items]


def read_js():
    """app.js 를 읽어 주석(// ...)을 제거한 문자열을 반환."""
    with open(os.path.join("app", "static", "app.js"), encoding="utf-8") as f:
        src = f.read()
    return re.sub(r"//.*", "", src)


def js_function_body(js, name):
    """주석 제거된 js 에서 function name(...) { ... } 본문을 중괄호 짝으로 추출."""
    m = re.search(r"function\s+" + name + r"\s*\([^)]*\)\s*\{", js)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(js) and depth:
        depth += {"{": 1, "}": -1}.get(js[i], 0)
        i += 1
    return js[m.end():i - 1]


def missing_tokens(body, tokens):
    """body 에 없는 항목 이름 목록. tokens: {이름: 찾을 문자열 또는 문자열 튜플(하나만 있으면 됨)}"""
    lacking = []
    for label, tok in tokens.items():
        options = tok if isinstance(tok, tuple) else (tok,)
        if not any(o in body for o in options):
            lacking.append(label)
    return lacking


# 가전 검색/필터 로직 (app.js renderDevices 규칙을 파이썬으로 재현)
#   - 검색: type, model, status, deviceId, location 부분 매칭 (대소문자 무시)
#   - 필터: status 일치
def filter_devices(devices, search="", status=""):
    s = (search or "").lower()
    out = []
    for d in devices:
        matches_search = any(
            s in str(d.get(k, "")).lower()
            for k in ("type", "model", "status", "deviceId", "location")
        )
        matches_status = (not status) or d.get("status") == status
        if matches_search and matches_status:
            out.append(d)
    return out


# =============================================================================
# 서버 기동 유틸
# =============================================================================
def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server(port):
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    for _ in range(40):
        if proc.poll() is not None:
            return proc, False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                if r.status == 200:
                    return proc, True
        except Exception:
            time.sleep(0.5)
    return proc, False


def stop_server(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# =============================================================================
# 검증 실행부
# =============================================================================
def run_tests():
    # =========================================================================
    # 1) 개발자 테스트 : 서버 없이 함수 직접 호출
    # =========================================================================
    try:
        from app.api.subscribers import get_devices_by_user
        data = get_devices_by_user("U001")
        passed = isinstance(data, list) and ids(data) == ["D001", "D002"]
        actual = f"{ids(data)}" if isinstance(data, list) else "list 아님/None"
    except Exception as e:
        passed, actual = False, f"예외: {type(e).__name__} {e}"
    check("DEV-01", 'get_devices_by_user("U001") 직접 호출', "D001, D002 반환",
          actual, passed)

    try:
        from app.api.devices import get_device_usage
        data = get_device_usage("D001")
        passed = isinstance(data, dict) and data.get("deviceId") == "D001"
        actual = f'deviceId={data.get("deviceId")}' if isinstance(data, dict) else "dict 아님/None"
    except Exception as e:
        passed, actual = False, f"예외: {type(e).__name__} {e}"
    check("DEV-02", 'get_device_usage("D001") 직접 호출', "D001 사용 현황 dict 반환",
          actual, passed)

    # app.js 구현 여부 (정적 검사, 주석 제외)
    js = read_js()
    lacking = missing_tokens(js_function_body(js, "selectSubscriber"), {
        "selectedUserId 갱신": "selectedUserId =",
        "/devices API 호출": "/devices",
        "fetch": "fetch(",
        "renderDevices 호출": "renderDevices(",
        "사용 현황 초기화": "usage-empty",
    })
    check("DEV-03", "selectSubscriber() 구현",
          "선택 갱신 → 사용 현황 초기화 → /devices 호출 → renderDevices()",
          f"누락: {lacking}" if lacking else "구현됨", not lacking)

    lacking = missing_tokens(js_function_body(js, "renderDevices"), {
        "filter": ".filter(",
        "toLowerCase": "toLowerCase()",
        "No registered devices": "No registered devices",
        "No devices matched": "No devices matched",
        "selectDevice": "selectDevice(",
        "badge": "badgeClass(",
    })
    check("DEV-04", "renderDevices() 검색/필터 + 빈 목록 메시지 + 행 클릭",
          "filter / 소문자 비교 / 안내 메시지 2종 / selectDevice / badge",
          f"누락: {lacking}" if lacking else "모두 구현", not lacking)

    lacking = missing_tokens(js_function_body(js, "selectDevice"), {
        "selectedDeviceId 갱신": "selectedDeviceId =",
        "/usage API 호출": "/usage",
        "fetch": "fetch(",
        "usage-info 렌더링": "usage-info",
        "renderUsageChart 호출": "renderUsageChart(",
    })
    check("DEV-05", "selectDevice() 구현",
          "선택 갱신 → /usage 호출 → usage-info 렌더링 → renderUsageChart()",
          f"누락: {lacking}" if lacking else "구현됨", not lacking)

    lacking = missing_tokens(js_function_body(js, "renderUsageChart"), {
        "기존 차트 destroy": "destroy()",
        "new Chart": "new Chart(",
        "bar 타입": ('"bar"', "'bar'"),
        "요일 라벨": ('"Mon"', "'Mon'"),
        "beginAtZero": "beginAtZero",
    })
    check("DEV-06", "renderUsageChart() 구현",
          "기존 차트 destroy / bar 타입 / Mon~Sun / beginAtZero",
          f"누락: {lacking}" if lacking else "구현됨", not lacking)

    active = {
        "device-search 리스너": bool(re.search(
            r'^\s*document\.getElementById\("device-search"\)'
            r'\.addEventListener\("input",\s*renderDevices\)', js, re.M)),
        "device-status-filter 리스너": bool(re.search(
            r'^\s*document\.getElementById\("device-status-filter"\)'
            r'\.addEventListener\("change",\s*renderDevices\)', js, re.M)),
    }
    lacking = [k for k, ok in active.items() if not ok]
    check("DEV-07", "가전 검색/필터 이벤트 리스너 주석 해제", "둘 다 활성화",
          f"비활성: {lacking}" if lacking else "활성화", not lacking)

    # =========================================================================
    # 2) API 테스트 + TE 시나리오 (가전 목록)
    # =========================================================================
    # TE-1 : U001 가전 목록
    st, u001 = http_get("/api/subscribers/U001/devices")
    u001 = u001 if isinstance(u001, list) else []
    check("TE-1", "/api/subscribers/U001/devices 호출", "200 + 2개 가전 (D001, D002)",
          f"status={st}, {ids(u001)}", st == 200 and ids(u001) == ["D001", "D002"])

    # API-01 : 가전 응답 필드
    missing = [d.get("deviceId", "?") for d in u001 if not DEVICE_FIELDS.issubset(d)]
    check("API-01", "가전 응답 필드 검증",
          "deviceId/type/model/location/status/lastSeen 모두 존재",
          "데이터 없음" if not u001 else f"누락: {missing}" if missing else "모든 항목 정상",
          bool(u001) and not missing)

    # TE-2 : 가전 없는 사용자 → []
    st, body = http_get("/api/subscribers/U005/devices")
    check("TE-2", "/api/subscribers/U005/devices 호출", "200 + 빈 배열 []",
          f"status={st}, body={body}", st == 200 and body == [])

    # TE-3 : 존재하지 않는 사용자 → 404
    st, _ = http_get("/api/subscribers/U999/devices")
    check("TE-3", "/api/subscribers/U999/devices 호출", "404 에러",
          f"status={st}", st == 404)

    # TE-4 : U001 클릭 시 가전 Table (API 결과 + 필터 없음 = 표시 대상)
    r = filter_devices(u001)
    sel_ok = "DEV-03" in [t for t, *_ , p in results if p]
    check("TE-4", "U001 클릭 시 가전 Table 표시", "D001, D002 표시",
          f"{ids(r)} / selectSubscriber {'구현' if sel_ok else '미구현'}",
          ids(r) == ["D001", "D002"] and sel_ok)

    # TE-5 : U005 클릭 시 안내 메시지
    _, u005 = http_get("/api/subscribers/U005/devices")
    msg_ok = "No registered devices" in js_function_body(js, "renderDevices")
    check("TE-5", "U005 클릭 시 안내 메시지", '"No registered devices" 표시',
          f"가전 {len(u005) if isinstance(u005, list) else '?'}개 / 메시지 {'있음' if msg_ok else '없음'}",
          u005 == [] and msg_ok)

    # TE-6 : 가전 검색 "TV"
    r = filter_devices(u001, search="TV")
    check("TE-6", 'U001 가전 검색 "TV" 입력', "TV 타입만 표시 (D001)",
          f"{ids(r)}", ids(r) == ["D001"])

    # TE-7 : 상태 필터 "Online" (Online / Error 가 섞인 U003 기준)
    _, u003 = http_get("/api/subscribers/U003/devices")
    u003 = u003 if isinstance(u003, list) else []
    r = filter_devices(u003, status="Online")
    check("TE-7", 'U003 가전 상태 필터 "Online" 선택', "Online 가전만 표시 (D004, D005)",
          f"{ids(r)}", ids(r) == ["D004", "D005"])

    # =========================================================================
    # 2) API 테스트 + TE 시나리오 (사용 현황 + 차트)
    # =========================================================================
    # TE-8 : D001 사용 현황
    st, usage = http_get("/api/devices/D001/usage")
    usage = usage if isinstance(usage, dict) else {}
    missing = sorted(USAGE_FIELDS - set(usage))
    check("TE-8", "/api/devices/D001/usage 호출", "200 + 사용 현황 9개 필드",
          f"status={st}" + (f", 누락: {missing}" if missing else ", 필드 정상"),
          st == 200 and not missing)

    # TE-9 : 존재하지 않는 디바이스 → 404
    st, _ = http_get("/api/devices/D999/usage")
    check("TE-9", "/api/devices/D999/usage 호출", "404 에러", f"status={st}", st == 404)

    # TE-10 : D001 클릭 시 사용 현황 표시 (값 + selectDevice 렌더링 항목)
    dev_body = js_function_body(js, "selectDevice")
    shown = [k for k in ("deviceId", "deviceName", "powerStatus", "lastUsedAt",
                         "totalUsageHours", "weeklyUsageCount", "healthStatus", "remark")
             if k not in dev_body]
    expected_vals = {"powerStatus": "On", "totalUsageHours": 152,
                     "weeklyUsageCount": 18, "healthStatus": "Normal"}
    wrong = {k: usage.get(k) for k, v in expected_vals.items() if usage.get(k) != v}
    check("TE-10", "D001 클릭 시 사용 현황 표시",
          "전원 On / 누적 152시간 / 주간 18회 / Normal 등 8개 항목 렌더링",
          f"값 불일치: {wrong}" if wrong else
          f"렌더링 누락: {shown}" if shown else "값 정상, 8개 항목 렌더링",
          bool(usage) and not wrong and not shown)

    # TE-11 : Bar Chart 데이터 (요일 7개)
    trend = usage.get("weeklyUsageTrend")
    chart_ok = "DEV-06" in [t for t, *_ , p in results if p]
    check("TE-11", "D001 클릭 시 Bar Chart 표시",
          "Mon~Sun 7개 값 [2, 3, 1, 4, 2, 3, 3] + bar 차트 구현",
          f"{trend} / 차트 {'구현' if chart_ok else '미구현'}",
          trend == [2, 3, 1, 4, 2, 3, 3] and chart_ok)

    # TE-12 : 다른 가전 클릭 시 차트 갱신 (기존 차트 destroy 후 새로 생성)
    _, d002 = http_get("/api/devices/D002/usage")
    trend2 = d002.get("weeklyUsageTrend") if isinstance(d002, dict) else None
    destroy_ok = "destroy()" in js_function_body(js, "renderUsageChart")
    check("TE-12", "다른 가전(D002) 클릭 시 차트 갱신",
          "이전 차트 destroy + 새 데이터 [0, 1, 0, 1, 1, 0, 1]",
          f"{trend2} / destroy {'있음' if destroy_ok else '없음'}",
          trend2 == [0, 1, 0, 1, 1, 0, 1] and destroy_ok)

    # =========================================================================
    # 추가 시나리오 : 완료 조건의 검색 기준(모델/타입/상태/위치)과 필터 4종 전부
    # =========================================================================
    r = filter_devices(u001, search="tv")
    check("TE-13", '가전 검색 소문자 "tv" (대소문자 무시)', "D001 표시",
          f"{ids(r)}", ids(r) == ["D001"])

    r = filter_devices(u001, search="WashTower")
    check("TE-14", '가전 검색 "WashTower" (모델명)', "D002 표시", f"{ids(r)}",
          ids(r) == ["D002"])

    r = filter_devices(u001, search="Dormitory")
    check("TE-15", '가전 검색 "Dormitory" (위치)', "D001 표시", f"{ids(r)}",
          ids(r) == ["D001"])

    r = filter_devices(u003, search="Error")
    check("TE-16", '가전 검색 "Error" (상태)', "D006 표시", f"{ids(r)}",
          ids(r) == ["D006"])

    _, u004 = http_get("/api/subscribers/U004/devices")
    u004 = u004 if isinstance(u004, list) else []
    got = {
        "Offline": ids(filter_devices(u001, status="Offline")),
        "Standby": ids(filter_devices(u004, status="Standby")),
        "Error": ids(filter_devices(u003, status="Error")),
    }
    want = {"Offline": ["D002"], "Standby": ["D008"], "Error": ["D006"]}
    check("TE-17", "상태 필터 Offline(U001) / Standby(U004) / Error(U003)",
          "D002 / D008 / D006", f"{got}", got == want)

    r = filter_devices(u003, search="LG", status="Online")
    check("TE-18", 'U003 검색 "LG" + 필터 "Online" 동시 적용', "D004, D005 표시",
          f"{ids(r)}", ids(r) == ["D004", "D005"])

    _, u002 = http_get("/api/subscribers/U002/devices")
    u002 = u002 if isinstance(u002, list) else []
    r = filter_devices(u002, status="Error")
    check("TE-19", 'U002 상태 필터 "Error" (일치 없음)', '0개 → "No devices matched"',
          f"{len(r)}개", bool(u002) and r == [])

    # =========================================================================
    # 4) 데이터 검증 : 전체 사용자/가전 기준
    # =========================================================================
    all_devices = []
    for uid in ("U001", "U002", "U003", "U004", "U005"):
        _, body = http_get(f"/api/subscribers/{uid}/devices")
        if isinstance(body, list):
            all_devices.extend(body)

    bad = [(d.get("deviceId"), d.get("status")) for d in all_devices
           if d.get("status") not in VALID_DEVICE_STATUS]
    check("DATA-01", "가전 status 값 범위", "Online / Offline / Standby / Error 중 하나",
          "데이터 없음" if not all_devices else f"범위 밖: {bad}" if bad else
          f"{len(all_devices)}개 모두 정상", bool(all_devices) and not bad)

    usages, no_usage, name_mismatch = {}, [], []
    for d in all_devices:
        st, u = http_get(f"/api/devices/{d.get('deviceId')}/usage")
        if st != 200 or not isinstance(u, dict):
            no_usage.append(d.get("deviceId"))
            continue
        usages[d["deviceId"]] = u
        if u.get("deviceId") != d["deviceId"] or u.get("deviceName") != d.get("model"):
            name_mismatch.append(d["deviceId"])
    check("DATA-02", "목록의 모든 가전에 사용 현황 존재",
          "가전 목록의 모든 deviceId 가 /usage 200",
          "데이터 없음" if not all_devices else f"사용 현황 없음: {no_usage}" if no_usage
          else f"{len(usages)}개 모두 존재", bool(all_devices) and not no_usage)
    check("DATA-03", "사용 현황 deviceId / deviceName = 가전 목록 deviceId / model",
          "모두 일치", "데이터 없음" if not usages else
          f"불일치: {name_mismatch}" if name_mismatch else "모두 일치",
          bool(usages) and not name_mismatch)

    bad_trend = [k for k, u in usages.items()
                 if not (isinstance(u.get("weeklyUsageTrend"), list)
                         and len(u["weeklyUsageTrend"]) == 7
                         and all(isinstance(x, int) and x >= 0 for x in u["weeklyUsageTrend"]))]
    check("DATA-04", "weeklyUsageTrend 형식", "모든 가전 7개(Mon~Sun), 0 이상 정수",
          "데이터 없음" if not usages else f"형식 오류: {bad_trend}" if bad_trend
          else "모두 정상", bool(usages) and not bad_trend)

    bad = [(k, u.get("powerStatus"), u.get("healthStatus")) for k, u in usages.items()
           if u.get("powerStatus") not in VALID_POWER_STATUS
           or u.get("healthStatus") not in VALID_HEALTH_STATUS]
    check("DATA-05", "powerStatus / healthStatus 값 범위",
          "On/Off/Standby/Error/Cleaning, Normal/Warning",
          "데이터 없음" if not usages else f"범위 밖: {bad}" if bad else "모두 정상",
          bool(usages) and not bad)


# =============================================================================
# Markdown Report 생성
# =============================================================================
def render_report():
    total = len(results)
    passed = sum(1 for *_, p in results if p)
    failed = total - passed
    rate = (passed / total * 100) if total else 0.0

    lines = []
    lines.append("# requirement_2 검증 Report (TE)")
    lines.append("")
    lines.append("| 항목 | 내용 |")
    lines.append("|------|------|")
    lines.append("| **프로젝트** | webOS Subscription Management Dashboard |")
    lines.append("| **검증 대상** | requirement_2.md (가전 목록 + 사용 현황 + 차트) |")
    lines.append(f"| **검증 일시** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |")
    lines.append("| **작성자** | 김민지 |")
    lines.append("")
    lines.append(f"**총 {total}건 중 PASS {passed} / FAIL {failed} — Pass Rate {rate:.1f}%**")
    lines.append("")
    lines.append("| TC ID | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |")
    lines.append("|:-----:|----------------|-----------|-----------|:----:|")
    for tc_id, scenario, expected, actual, passed_ in results:
        mark = "✅ PASS" if passed_ else "❌ FAIL"
        lines.append(f"| {tc_id} | {scenario} | {expected} | {actual} | {mark} |")
    lines.append("")
    lines.append("## 수동 브라우저 검증 (직접 확인 후 기입)")
    lines.append("")
    lines.append("> 위 자동 결과 중 검색/필터는 app.js 규칙을 파이썬으로 재현한 결과이고,")
    lines.append("> 화면 표시·차트는 코드 구현 여부만 확인한 것입니다.")
    lines.append("> 실제 화면 동작은 아래 항목을 브라우저에서 확인해 판정란에 PASS / FAIL 을 적으세요.")
    lines.append("")
    lines.append("| ID | 확인 방법 | 기대 결과 | 실제 결과 | 판정 |")
    lines.append("|:--:|----------|-----------|-----------|:----:|")
    for m_id, how, expected in MANUAL_CHECKS:
        lines.append(f"| {m_id} | {how} | {expected} |  |  |")
    lines.append("")
    lines.append("## 확인 필요 사항")
    lines.append("")
    lines.append("- D007(LG CordZero R5)의 `powerStatus` 가 `Cleaning` 입니다. "
                 "오리엔테이션 명세(On / Off / Standby / Error)에는 없는 값이지만 "
                 "app.js 배지 규칙(노랑)에는 있어 DATA-05 에서 허용했습니다. PM 확인 필요.")
    lines.append("")
    lines.append("> 본 Report 는 `tests/req2_test_template.py` 로 생성되었습니다.")

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return passed, failed, total, rate


# =============================================================================
# main
# =============================================================================
def main():
    global BASE_URL
    print("=" * 60)
    print(" requirement_2 검증")
    print("=" * 60)

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    port = find_free_port()
    print(f"[서버 기동] 127.0.0.1:{port} ...")
    proc, ok = start_server(port)
    if not ok:
        print("[오류] 서버 기동 실패. requirements 설치 및 app/main.py 를 확인하세요.")
        stop_server(proc)
        sys.exit(1)

    BASE_URL = f"http://127.0.0.1:{port}"
    print("[서버 기동] 성공\n")

    run_tests()

    stop_server(proc)

    passed, failed, total, rate = render_report()
    print("\n" + "=" * 60)
    print(f" 결과: PASS {passed} / FAIL {failed} (총 {total}) - {rate:.1f}%")
    print(f" Report 저장: {os.path.relpath(REPORT_PATH, PROJECT_ROOT)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
