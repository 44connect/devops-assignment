"""
requirement_1.md 검증 템플릿 스크립트  (학생용)

이 파일은 무엇인가요?
--------------------
여러분(TE 역할)이 requirement_1 을 "직접 검증"하고, 그 결과를
Markdown Report 파일로 만드는 방법을 익히기 위한 '템플릿'입니다.

이미 동작하는 예제 몇 개가 들어 있습니다. 실행하면 바로 Report 가 생깁니다.
그다음, 아래 `TODO` 부분을 채워서 나머지 TE 시나리오를 완성하세요.

실행 방법
--------
    # 프로젝트 루트에서
    python tests/req1_test_template.py

결과
----
    tests/reports/req1_report_template.md   (여러분이 만든 검증 Report)

필요 패키지: fastapi, uvicorn (requirements.txt 에 이미 포함)
             그 외에는 파이썬 표준 라이브러리만 사용합니다.

────────────────────────────────────────────────────────────────────────
검증 흐름 3단계 (requirement_1.md 기준)
  1) 개발자 테스트  : 코드가 문법적으로 올바르고 함수가 값을 반환하는가?
  2) API 테스트     : 서버를 켜고 /api/subscribers 가 실제로 동작하는가?
  3) TE 시나리오    : 검색/필터가 "기대 결과"대로 동작하는가?
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
# 경로 설정 (수정할 필요 없음)
# =============================================================================
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
REPORT_DIR = os.path.join(THIS_DIR, "reports")
REPORT_PATH = os.path.join(REPORT_DIR, "req1_report_template.md")

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
# HTTP 유틸 (수정할 필요 없음)
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


def http_get_text(path, timeout=5):
    """(status_code, text) 반환. 실패 시 (None, None)."""
    try:
        with urllib.request.urlopen(BASE_URL + path, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


REQUIRED_FIELDS = {"userId", "name", "plan", "status", "deviceCount"}


def ids(subs):
    return [u["userId"] for u in subs]


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


# 검색/필터 로직 (app.js renderSubscribers 와 동일한 규칙을 파이썬으로 재현)
def filter_subscribers(subs, search="", status=""):
    s = (search or "").lower()
    out = []
    for u in subs:
        matches_search = (
            s in str(u.get("name", "")).lower()
            or s in str(u.get("plan", "")).lower()
            or s in str(u.get("status", "")).lower()
            or s in str(u.get("userId", "")).lower()
        )
        matches_status = (not status) or u.get("status") == status
        if matches_search and matches_status:
            out.append(u)
    return out


# =============================================================================
# 서버 기동 유틸 (수정할 필요 없음)
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
# 검증 실행부  ★★★ 여기서부터 여러분이 채웁니다 ★★★
# =============================================================================
def run_tests():
    # -------------------------------------------------------------------------
    # [예제 1] 개발자 테스트 : get_subscribers() 함수가 5명을 반환하는가?
    #   서버 없이도 함수를 직접 불러서 확인할 수 있습니다.
    # -------------------------------------------------------------------------
    try:
        from app.api.subscribers import get_subscribers
        data = get_subscribers()
        passed = isinstance(data, list) and len(data) == 5
        actual = f"{len(data)}명 반환" if isinstance(data, list) else "list 아님/None"
    except Exception as e:
        passed, actual = False, f"예외: {e}"
    check("DEV-01", "get_subscribers() 함수 직접 호출", "5명 반환", actual, passed)

    # -------------------------------------------------------------------------
    # [예제 2] API 테스트 : GET /api/subscribers 가 200 을 반환하는가?
    # -------------------------------------------------------------------------
    status, body = http_get("/api/subscribers")
    check("API-01", "GET /api/subscribers 호출", "200 OK",
          f"status={status}", status == 200)

    # 이후 TE 시나리오에서 재사용하기 위해 목록을 확보
    subscribers = body if isinstance(body, list) else []

    # -------------------------------------------------------------------------
    # [예제 3] TE 시나리오 #1 : /api/subscribers 호출 → 5명 반환
    # -------------------------------------------------------------------------
    passed = len(subscribers) == 5
    check("TE-1", "/api/subscribers 호출", "5명의 사용자 목록 반환",
          f"{len(subscribers)}명", passed)

    # -------------------------------------------------------------------------
    # [예제 4] TE 시나리오 #3 : 검색 "Kim" → Kim Minsoo 만 표시
    #   filter_subscribers() 를 사용해 검색 결과를 계산합니다.
    # -------------------------------------------------------------------------
    r = filter_subscribers(subscribers, search="Kim")
    passed = len(r) == 1 and r and r[0]["name"] == "Kim Minsoo"
    check("TE-3", '검색창에 "Kim" 입력', "Kim Minsoo만 표시",
          f'{len(r)}명: {[u["name"] for u in r]}', passed)

    # -------------------------------------------------------------------------
    # 개발자 테스트 : 응답 필드 (PM 확정 형식: userId/name/plan/status/deviceCount)
    # -------------------------------------------------------------------------
    missing = [
        u.get("userId", "?") for u in subscribers
        if not REQUIRED_FIELDS.issubset(u)
        or not isinstance(u.get("deviceCount"), int)
    ]
    check("DEV-02", "응답 필드 검증 (userId/name/plan/status/deviceCount)",
          "모든 항목에 필드 존재, deviceCount는 number",
          f"누락/타입오류: {missing}" if missing or not subscribers
          else "모든 항목 정상",
          bool(subscribers) and not missing)

    # -------------------------------------------------------------------------
    # 개발자 테스트 : app.js 구현 여부 (정적 검사, 주석 제외)
    # -------------------------------------------------------------------------
    js = read_js()
    fetch_body = js_function_body(js, "fetchSubscribers")
    passed = "fetch(" in fetch_body and "/api/subscribers" in fetch_body \
        and "renderSubscribers(" in fetch_body
    check("DEV-03", "fetchSubscribers() 구현",
          "/api/subscribers fetch 후 renderSubscribers() 호출",
          "구현됨" if passed else "미구현", passed)

    render_body = js_function_body(js, "renderSubscribers")
    needs = {
        "filter": ".filter(" in render_body,
        "toLowerCase": "toLowerCase()" in render_body,
        "행 생성": "createElement" in render_body or "innerHTML" in render_body,
        "selectSubscriber": "selectSubscriber(" in render_body,
        "selected 클래스": "selected" in render_body.replace("selectedUserId", ""),
    }
    lacking = [k for k, ok in needs.items() if not ok]
    check("DEV-04", "renderSubscribers() 검색/필터 + 행 렌더링 + 행 클릭",
          "filter / 소문자 비교 / 행 생성 / 클릭 / selected 클래스",
          f"누락: {lacking}" if lacking else "모두 구현", not lacking)

    active = {
        "search 리스너": bool(re.search(
            r'^\s*document\.getElementById\("subscriber-search"\)'
            r'\.addEventListener\("input",\s*renderSubscribers\)', js, re.M)),
        "filter 리스너": bool(re.search(
            r'^\s*document\.getElementById\("subscriber-status-filter"\)'
            r'\.addEventListener\("change",\s*renderSubscribers\)', js, re.M)),
        "초기 fetchSubscribers()": bool(
            re.search(r"^\s*fetchSubscribers\(\);", js, re.M)),
    }
    lacking = [k for k, ok in active.items() if not ok]
    check("DEV-05", "이벤트 리스너 + 초기 fetchSubscribers() 주석 해제",
          "셋 다 활성화", f"비활성: {lacking}" if lacking else "활성화",
          not lacking)

    # -------------------------------------------------------------------------
    # API 테스트
    # -------------------------------------------------------------------------
    status_h, body_h = http_get("/health")
    check("API-02", "GET /health 호출", '200 OK, {"status":"ok"}',
          f"status={status_h}, body={body_h}",
          status_h == 200 and body_h == {"status": "ok"})

    # -------------------------------------------------------------------------
    # TE 시나리오 #2 : 대시보드 접속 시 Table 자동 표시
    #   페이지(/)가 뜨고, 초기 fetchSubscribers() 호출이 활성화되어 있으며,
    #   필터가 없을 때 전체 5명이 표시 대상인지 확인
    # -------------------------------------------------------------------------
    status_p, html = http_get_text("/")
    page_ok = status_p == 200 and html and 'id="subscriber-body"' in html
    r = filter_subscribers(subscribers)
    passed = bool(page_ok) and active["초기 fetchSubscribers()"] and len(r) == 5
    check("TE-2", "대시보드 접속 시 Table 자동 표시", "5명 목록 표시",
          f"페이지 status={status_p} / 초기 호출 "
          f"{'활성' if active['초기 fetchSubscribers()'] else '비활성'} / {len(r)}명",
          passed)

    # TE 시나리오 #4 : 검색 "Premium" → Premium 플랜 사용자만
    r = filter_subscribers(subscribers, search="Premium")
    passed = ids(r) == ["U001", "U004"]
    check("TE-4", '검색창에 "Premium" 입력', "Premium 플랜 사용자만 표시 (U001, U004)",
          f"{len(r)}명: {ids(r)}", passed)

    # TE 시나리오 #5 : 상태 필터 "Active"
    r = filter_subscribers(subscribers, status="Active")
    passed = ids(r) == ["U001", "U002", "U004"]
    check("TE-5", '상태 필터 "Active" 선택', "Active 사용자만 표시 (U001, U002, U004)",
          f"{len(r)}명: {ids(r)}", passed)

    # TE 시나리오 #6 : 상태 필터 "Expired" → Jung Hyerin
    r = filter_subscribers(subscribers, status="Expired")
    passed = [u["name"] for u in r] == ["Jung Hyerin"]
    check("TE-6", '상태 필터 "Expired" 선택', "Jung Hyerin만 표시",
          f'{len(r)}명: {[u["name"] for u in r]}', passed)

    # TE 시나리오 #7 : 검색 + 필터 동시 적용
    r = filter_subscribers(subscribers, search="Kim", status="Active")
    r_none = filter_subscribers(subscribers, search="Kim", status="Expired")
    passed = ids(r) == ["U001"] and r_none == []
    check("TE-7", '검색("Kim") + 필터("Active" / "Expired") 동시 적용',
          "두 조건 모두 만족하는 결과만 (U001 / 0명)",
          f"{ids(r)} / {len(r_none)}명", passed)

    # TE 시나리오 #8 : 검색어 삭제 시 전체 복원
    r = filter_subscribers(subscribers, search="")
    passed = len(r) == 5
    check("TE-8", "검색어 삭제 시", "전체 목록(5명) 복원", f"{len(r)}명", passed)

    # -------------------------------------------------------------------------
    # 추가 시나리오 (PM 요청 사항)
    # -------------------------------------------------------------------------
    # 대소문자 구분 없음 : "kim" → Kim Minsoo
    r = filter_subscribers(subscribers, search="kim")
    passed = [u["name"] for u in r] == ["Kim Minsoo"]
    check("TE-9", '검색창에 소문자 "kim" 입력 (대소문자 무시)', "Kim Minsoo만 표시",
          f'{len(r)}명: {[u["name"] for u in r]}', passed)

    # status 도 검색 대상 : "Active" 검색 → Active 사용자 전부 (버그 아님)
    r = filter_subscribers(subscribers, search="Active")
    passed = ids(r) == ["U001", "U002", "U004"]
    check("TE-10", '검색창에 "Active" 입력 (status 검색)',
          "Active 사용자 전부 표시 (U001, U002, U004)",
          f"{len(r)}명: {ids(r)}", passed)

    # userId 검색 : "U003" → Park Junho
    r = filter_subscribers(subscribers, search="U003")
    passed = [u["name"] for u in r] == ["Park Junho"]
    check("TE-11", '검색창에 "U003" 입력 (userId 검색)', "Park Junho만 표시",
          f'{len(r)}명: {[u["name"] for u in r]}', passed)

    # 일치 결과 없음
    r = filter_subscribers(subscribers, search="zzz")
    check("TE-12", '검색창에 "zzz" 입력 (일치 없음)', "0명 표시 (빈 Table)",
          f"{len(r)}명", subscribers != [] and r == [])


# =============================================================================
# Markdown Report 생성 (수정할 필요 없음)
# =============================================================================
def render_report():
    total = len(results)
    passed = sum(1 for *_, p in results if p)
    failed = total - passed
    rate = (passed / total * 100) if total else 0.0

    lines = []
    lines.append("# requirement_1 검증 Report (TE 실습)")
    lines.append("")
    lines.append("| 항목 | 내용 |")
    lines.append("|------|------|")
    lines.append("| **프로젝트** | webOS Subscription Management Dashboard |")
    lines.append("| **검증 대상** | requirement_1.md |")
    lines.append(f"| **검증 일시** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |")
    lines.append("| **작성자** | (여기에 이름을 적으세요) |")
    lines.append("")
    lines.append(f"**총 {total}건 중 PASS {passed} / FAIL {failed} — Pass Rate {rate:.1f}%**")
    lines.append("")
    lines.append("| TC ID | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |")
    lines.append("|:-----:|----------------|-----------|-----------|:----:|")
    for tc_id, scenario, expected, actual, passed_ in results:
        mark = "✅ PASS" if passed_ else "❌ FAIL"
        lines.append(f"| {tc_id} | {scenario} | {expected} | {actual} | {mark} |")
    lines.append("")
    lines.append("> 본 Report 는 `tests/req1_test_template.py` 로 생성되었습니다.")

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return passed, failed, total, rate


# =============================================================================
# main (수정할 필요 없음)
# =============================================================================
def main():
    global BASE_URL
    print("=" * 60)
    print(" requirement_1 검증 (학생용 템플릿)")
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
