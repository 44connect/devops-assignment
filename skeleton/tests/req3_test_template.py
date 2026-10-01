"""
requirement_3.md 검증 스크립트  (TE)

실행 방법
--------
    # 프로젝트 루트(skeleton)에서
    python tests/req3_test_template.py

결과
----
    tests/reports/req3_report_template.md

필요 패키지: requirements.txt 의 패키지 외에는 파이썬 표준 라이브러리만 사용합니다.
Node.js 가 있으면 app.js 의 badgeClass() 를 실제로 실행해서 검증하고,
없으면 badgeClass() 안의 매핑 표를 읽어서 같은 규칙으로 계산합니다.

────────────────────────────────────────────────────────────────────────
검증 흐름 (requirement_3.md 기준)
  1) 개발자 테스트  : badgeClass() 매핑, CSS 색상 클래스, 화면 적용 위치
  2) TE 시나리오    : 실제 데이터의 상태 값이 기대한 색상 badge 로 표시되는가?
  3) 데이터 검증    : 데이터에 나오는 모든 상태 값에 색상이 지정되어 있는가?
  4) CI/CD (수동)  : GitHub Actions 실행, Render 배포 → tests/manual/req3_manual.json
────────────────────────────────────────────────────────────────────────
"""

import os
import re
import sys
import time
import json
import shutil
import socket
import colorsys
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
REPORT_PATH = os.path.join(REPORT_DIR, "req3_report_template.md")
# 수동 검증 결과. 스크립트를 다시 돌려도 Report 에 그대로 반영된다.
MANUAL_RESULTS_PATH = os.path.join(THIS_DIR, "manual", "req3_manual.json")

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


# requirement_3.md 색상 매핑 표 (상태 값 → CSS 클래스, 색상)
EXPECTED_BADGE = {
    "Active": ("status-active", "초록"), "Online": ("status-active", "초록"),
    "Normal": ("status-active", "초록"),
    "Paused": ("status-paused", "파랑"), "Standby": ("status-paused", "파랑"),
    "Expired": ("status-expired", "빨강"), "Error": ("status-expired", "빨강"),
    "Warning": ("status-expired", "빨강"),
    "Offline": ("status-offline", "회색"),
    "On": ("status-on", "노랑"), "Cleaning": ("status-on", "노랑"),
    "Off": ("status-off", "회색"),      # 연회색
}

# 수동 검증 항목 (자동 테스트가 볼 수 없는 실제 화면 / GitHub / Render 동작)
#   (ID, 확인 방법, 기대 결과)  → 결과는 tests/manual/req3_manual.json 에 기록
MANUAL_CHECKS = [
    ("UI-01", "구독자 Table Status 컬럼", "Active 초록 / Paused 파랑 / Expired 빨강"),
    ("UI-02", "U001 클릭 → 가전 Table", "D001 Online 초록 / D002 Offline 회색"),
    ("UI-03", "U003 클릭 → D006 클릭",
     "가전 상태 Error 빨강 / Power Status Error 빨강 / Health Status Warning 빨강"),
    ("UI-04", "U004 클릭 → D007, D008 클릭",
     "D008 Standby 파랑 / D007 Power Cleaning 노랑 / D008 Power Standby 파랑"),
    ("UI-05", "U001 → D001, D002 클릭", "D001 Power On 노랑 + Health Normal 초록 / D002 Power Off 연회색"),
    ("UI-06", "U003 행 클릭 (선택 행 안의 Paused badge)", "선택 행 배경과 badge 가 구분되어 보임"),
    ("UI-07", "개발자도구(F12) Console 탭", "JS 에러 없음"),
    ("CI-10", "dev / main 에 push 또는 PR", "GitHub Actions 탭에서 CI 자동 실행"),
    ("CI-11", "CI 로그: 서버 기동 + /health", "통과 (초록 체크)"),
    ("CI-12", "CI 로그: API 테스트", "3개 엔드포인트 포함 검증 테스트 전체 통과"),
    ("CI-13", "CI 통과 후 Render 배포", "https://<서비스>.onrender.com 접속 + /health OK"),
]


def read_text(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def read_js():
    """app.js 를 읽어 주석(// ...)을 제거한 문자열을 반환."""
    return re.sub(r"(?<!:)//.*", "", read_text("app", "static", "app.js"))


def js_function_body(js, name, with_header=False):
    """주석 제거된 js 에서 function name(...) { ... } 을 중괄호 짝으로 추출."""
    m = re.search(r"(async\s+)?function\s+" + name + r"\s*\([^)]*\)\s*\{", js)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(js) and depth:
        depth += {"{": 1, "}": -1}.get(js[i], 0)
        i += 1
    return js[m.start():i] if with_header else js[m.end():i - 1]


def run_badge_class(values):
    """badgeClass() 를 values 각각에 적용한 결과 목록과 실행 방식을 반환.

    Node.js 가 있으면 app.js 의 함수를 그대로 실행하고, 없으면 함수 안의
    `키: "status-xxx"` 매핑을 읽어 같은 규칙(소문자 비교, 없으면 "badge")으로 계산.
    """
    fn = js_function_body(read_js(), "badgeClass", with_header=True)
    if not fn:
        return None, "badgeClass() 없음"

    node = shutil.which("node")
    if node:
        script = fn + "\nconst v = JSON.parse(process.argv[1]);" \
                      "\nconsole.log(JSON.stringify(v.map(badgeClass)));"
        try:
            out = subprocess.run([node, "-e", script, json.dumps(values)],
                                 capture_output=True, text=True, timeout=10)
            if out.returncode == 0:
                return json.loads(out.stdout), "node 실행"
            return None, f"node 오류: {out.stderr.strip().splitlines()[-1:]}"
        except Exception as e:
            return None, f"node 오류: {e}"

    mapping = dict(re.findall(r'(\w+)\s*:\s*["\'](status-[\w-]+)["\']', fn))
    if not mapping:
        return None, "node 없음, 매핑 해석 실패"
    return ([f"badge {mapping[(v or '').lower()]}" if (v or "").lower() in mapping
             else "badge" for v in values], "매핑 정적 해석 (node 없음)")


def css_colors():
    """style.css 에서 .status-xxx 클래스별 글자색(color)을 읽어 {클래스: hex}."""
    css = read_text("app", "static", "style.css")
    colors = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        m = re.search(r"(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{6})", body)
        if not m:
            continue
        for cls in re.findall(r"\.(status-[\w-]+)", selectors):
            colors[cls] = m.group(1)
    return colors


def color_name(hex_color):
    """hex 색상을 초록/파랑/빨강/회색/노랑 으로 분류 (채도 낮으면 회색)."""
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    hue = h * 360
    if s < 0.25:
        return "회색"
    if hue < 15 or hue >= 330:
        return "빨강"
    if hue < 65:
        return "노랑"
    if hue < 170:
        return "초록"
    return "파랑"


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
    colors = css_colors()

    def badge_of(value):
        """상태 값 → (badgeClass 결과, 화면 색상 이름)."""
        out, _ = run_badge_class([value])
        cls = out[0] if out else None
        name = None
        if cls:
            extra = [c for c in cls.split() if c != "badge"]
            if extra and extra[0] in colors:
                name = color_name(colors[extra[0]])
        return cls, name

    # =========================================================================
    # 1) 개발자 테스트
    # =========================================================================
    values = list(EXPECTED_BADGE)
    out, how = run_badge_class(values)
    if out is None:
        check("DEV-01", "badgeClass() 매핑 표 12개 값", "표와 같은 CSS 클래스", how, False)
    else:
        wrong = [(v, o) for v, o in zip(values, out)
                 if o != f"badge {EXPECTED_BADGE[v][0]}"]
        check("DEV-01", "badgeClass() 매핑 표 12개 값", "표와 같은 CSS 클래스",
              f"불일치: {wrong} ({how})" if wrong else f"12개 일치 ({how})", not wrong)

    edge = ["ACTIVE", "online", "Unknown", "", None, "constructor"]
    want = ["badge status-active", "badge status-active", "badge", "badge", "badge", "badge"]
    out, how = run_badge_class(edge)
    passed = out == want
    check("DEV-02", "대소문자 무시 / 모르는 값·빈 값·null → 기본 badge",
          "ACTIVE·online → status-active, 나머지 → badge",
          f"{out} ({how})" if not passed else f"모두 기대값 ({how})", passed)

    needed = sorted({c for c, _ in EXPECTED_BADGE.values()})
    wrong = {c: (colors.get(c), color_name(colors[c]) if c in colors else None)
             for c in needed}
    bad = {c: v for c, v in wrong.items()
           if v[0] is None
           or v[1] != next(n for cc, n in EXPECTED_BADGE.values() if cc == c)}
    check("DEV-03", "style.css 색상 클래스 6개 정의 + 색상",
          "status-active 초록 / paused 파랑 / expired 빨강 / offline 회색 / on 노랑 / off 회색",
          f"문제: {bad}" if bad else "6개 모두 정의, 색상 일치", not bad)

    js = read_js()
    sites = {
        "구독 상태 (renderSubscribers)": js_function_body(js, "renderSubscribers"),
        "가전 상태 (renderDevices)": js_function_body(js, "renderDevices"),
        "전원·건강 상태 (selectDevice)": js_function_body(js, "selectDevice"),
    }
    lacking = [k for k, body in sites.items() if "badgeClass(" not in body]
    check("DEV-04", "badge 적용 위치", "구독 상태 / 가전 상태 / 전원·건강 상태 모두 badgeClass() 사용",
          f"미적용: {lacking}" if lacking else "3곳 모두 적용", not lacking)

    # =========================================================================
    # 2) TE 시나리오 : 실제 API 데이터의 상태 값 → 화면 색상
    # =========================================================================
    _, subs = http_get("/api/subscribers")
    subs = {u.get("userId"): u for u in subs} if isinstance(subs, list) else {}

    def device(user_id, device_id):
        _, ds = http_get(f"/api/subscribers/{user_id}/devices")
        return next((d for d in ds if d.get("deviceId") == device_id), {}) \
            if isinstance(ds, list) else {}

    def usage(device_id):
        _, u = http_get(f"/api/devices/{device_id}/usage")
        return u if isinstance(u, dict) else {}

    scenarios = [
        # (TC, 시나리오, 대상 설명, 실제 상태 값, 기대 상태 값, 기대 색상)
        ("TE-1", "Active 상태 구독자 확인", "U001 status",
         subs.get("U001", {}).get("status"), "Active", "초록"),
        ("TE-2", "Paused 상태 구독자 확인", "U003 status",
         subs.get("U003", {}).get("status"), "Paused", "파랑"),
        ("TE-3", "Expired 상태 구독자 확인", "U005 status",
         subs.get("U005", {}).get("status"), "Expired", "빨강"),
        ("TE-4", "Online 상태 가전 확인", "D001 status",
         device("U001", "D001").get("status"), "Online", "초록"),
        ("TE-5", "Offline 상태 가전 확인", "D002 status",
         device("U001", "D002").get("status"), "Offline", "회색"),
        ("TE-6", "Error 상태 가전 확인", "D006 status",
         device("U003", "D006").get("status"), "Error", "빨강"),
        ("TE-7", "Power On 상태 확인", "D001 powerStatus",
         usage("D001").get("powerStatus"), "On", "노랑"),
        ("TE-8", "Health Normal 상태 확인", "D001 healthStatus",
         usage("D001").get("healthStatus"), "Normal", "초록"),
        ("TE-9", "Health Warning 상태 확인", "D006 healthStatus",
         usage("D006").get("healthStatus"), "Warning", "빨강"),
        # 추가: 문서 예시에 없는 나머지 상태 값
        ("TE-14", "Standby 상태 가전 확인", "D008 status",
         device("U004", "D008").get("status"), "Standby", "파랑"),
        ("TE-15", "Power Cleaning 상태 확인", "D007 powerStatus",
         usage("D007").get("powerStatus"), "Cleaning", "노랑"),
        ("TE-16", "Power Off 상태 확인", "D002 powerStatus",
         usage("D002").get("powerStatus"), "Off", "회색"),
        ("TE-17", "Power Standby 상태 확인", "D004 powerStatus",
         usage("D004").get("powerStatus"), "Standby", "파랑"),
        ("TE-18", "Power Error 상태 확인", "D006 powerStatus",
         usage("D006").get("powerStatus"), "Error", "빨강"),
    ]
    for tc, scenario, target, value, want_value, want_color in scenarios:
        cls, name = badge_of(value)
        passed = value == want_value and name == want_color
        check(tc, scenario, f"{want_value} → {want_color} badge",
              f"{target}={value} → {cls} ({name or '색상 없음'})", passed)

    # =========================================================================
    # 3) 데이터 검증 : 데이터에 나오는 모든 상태 값에 색상이 있는가
    # =========================================================================
    found = {}
    for u in subs.values():
        found.setdefault(u.get("status"), "구독 상태")
    for uid in subs:
        _, ds = http_get(f"/api/subscribers/{uid}/devices")
        for d in ds if isinstance(ds, list) else []:
            found.setdefault(d.get("status"), "가전 상태")
            u = usage(d.get("deviceId"))
            found.setdefault(u.get("powerStatus"), "전원 상태")
            found.setdefault(u.get("healthStatus"), "건강 상태")
    found.pop(None, None)
    vals = sorted(found)
    out, how = run_badge_class(vals)
    plain = [v for v, o in zip(vals, out or []) if o == "badge"] if out else vals
    check("DATA-01", "데이터의 모든 상태 값에 색상 지정",
          "기본 badge(색 없음)로 나오는 값 없음",
          "데이터 없음" if not vals else f"색 없음: {plain}" if plain
          else f"{len(vals)}개 값 모두 색상 지정: {vals}",
          bool(vals) and not plain)


# =============================================================================
# Markdown Report 생성
# =============================================================================
MANUAL_MARKS = {"PASS": "✅ PASS", "FAIL": "❌ FAIL", "N/A": "➖ N/A"}


def load_manual_results():
    """tests/manual/req3_manual.json 을 읽는다. 없으면 빈 결과.

    형식: {"checked_at": "...", "results": {"UI-01": {"actual": "...", "verdict": "PASS",
                                                      "note": "(선택)"}}}
    """
    try:
        with open(MANUAL_RESULTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def render_report():
    total = len(results)
    passed = sum(1 for *_, p in results if p)
    failed = total - passed
    rate = (passed / total * 100) if total else 0.0

    lines = []
    lines.append("# requirement_3 검증 Report (TE)")
    lines.append("")
    lines.append("| 항목 | 내용 |")
    lines.append("|------|------|")
    lines.append("| **프로젝트** | webOS Subscription Management Dashboard |")
    lines.append("| **검증 대상** | requirement_3.md (상태 badge + CI/CD) |")
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
    manual = load_manual_results()
    m_results = manual.get("results", {})
    lines.append("## 수동 검증 (화면 / CI / 배포)")
    lines.append("")
    lines.append("> 자동 결과의 색상은 badgeClass() 결과와 style.css 의 글자색으로 판정한 것입니다.")
    lines.append("> 실제 화면, GitHub Actions, Render 배포는 직접 확인한 뒤 `tests/manual/req3_manual.json` 에 기록하면")
    lines.append("> 스크립트를 다시 실행해도 아래 표에 그대로 반영됩니다. (자동 Pass Rate 에는 포함되지 않음)")
    if manual.get("checked_at"):
        lines.append(f"> 수동 확인 일시: {manual['checked_at']}")
    lines.append("")
    lines.append("| ID | 확인 방법 | 기대 결과 | 실제 결과 | 판정 |")
    lines.append("|:--:|----------|-----------|-----------|:----:|")
    for m_id, how, expected in MANUAL_CHECKS:
        r = m_results.get(m_id, {})
        actual = r.get("actual", "")
        if r.get("note"):
            actual = f"{actual} ({r['note']})" if actual else r["note"]
        mark = MANUAL_MARKS.get(r.get("verdict", ""), "미확인" if not r else r.get("verdict"))
        lines.append(f"| {m_id} | {how} | {expected} | {actual} | {mark} |")
    lines.append("")
    lines.append("> 본 Report 는 `tests/req3_test_template.py` 로 생성되었습니다.")

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
    print(" requirement_3 검증")
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

    # FAIL 이 하나라도 있으면 종료 코드 1 → make test / CI 가 실패로 인식해 배포를 막는다
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
