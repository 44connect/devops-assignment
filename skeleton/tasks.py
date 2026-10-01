"""
빌드/실행 스크립트 (Windows / macOS 공용, 표준 라이브러리만 사용)

사용법
------
    python tasks.py <command>      # Windows
    python3 tasks.py <command>     # macOS
    make <command>                 # make 가 설치된 경우 (Makefile 이 이 파일을 호출)

포트 변경: PORT 환경변수 (예: make run PORT=8001)
테스트 지정: make test REQ=2  /  python tasks.py test 2
"""

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

# Windows 콘솔(cp949)에서도 한글이 깨지지 않도록 출력 인코딩을 UTF-8 로 설정
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PORT = os.environ.get("PORT", "8000")

SOURCES = ["app/main.py", "app/api/subscribers.py", "app/api/devices.py"]


def run(*args):
    shown = [str(a.relative_to(ROOT)) if isinstance(a, Path) else a for a in args]
    print("$", " ".join(shown), flush=True)
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)


def ensure_venv():
    if not PY.exists():
        print(f"$ python -m venv {VENV.name}")
        venv.create(VENV, with_pip=True)


# =============================================================================
# 명령
# =============================================================================
def install():
    """가상환경 생성 + 패키지 설치"""
    ensure_venv()
    run(PY, "-m", "pip", "install", "--upgrade", "pip")
    run(PY, "-m", "pip", "install", "-r", "requirements.txt")


def check():
    """Python 문법 검사 (CI와 동일)"""
    ensure_venv()
    for src in SOURCES:
        run(PY, "-m", "py_compile", src)


def build():
    """install + 문법 검사"""
    install()
    check()


def serve():
    """개발 서버 실행 (http://localhost:PORT)"""
    ensure_venv()
    run(PY, "-m", "uvicorn", "app.main:app", "--reload", "--port", PORT)


def test():
    """요구사항 검증 테스트 실행 (전체, 또는 REQ=2 처럼 지정)"""
    ensure_venv()
    req = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("REQ", "")
    pattern = f"req{req}_test_template.py" if req else "req*_test_template.py"
    scripts = sorted((ROOT / "tests").glob(pattern))
    if not scripts:
        print(f"테스트 파일 없음: tests/{pattern}")
        sys.exit(1)

    # 하나가 실패해도 나머지는 계속 실행하고, 마지막에 실패 여부를 반환
    failed = []
    for script in scripts:
        try:
            run(PY, script)
        except subprocess.CalledProcessError:
            failed.append(script.name)
    if failed:
        print(f"실행 실패: {', '.join(failed)}")
        sys.exit(1)


def ci():
    """build + test (push 전 로컬 CI)"""
    build()
    test()


def clean():
    """가상환경, 캐시 삭제 (tests/reports 의 검증 Report 는 유지)"""
    targets = [VENV, *ROOT.rglob("__pycache__")]
    for path in targets:
        if path.exists():
            print(f"$ remove {path.relative_to(ROOT)}")
            shutil.rmtree(path, ignore_errors=True)


COMMANDS = {
    "install": install,
    "build": build,
    "check": check,
    "run": serve,
    "test": test,
    "ci": ci,
    "clean": clean,
}


def show_help():
    print("사용법: python tasks.py <command>  (또는 make <command>)\n")
    for name, func in COMMANDS.items():
        print(f"  {name:8} {func.__doc__.replace('PORT', PORT)}")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "help"
    if name not in COMMANDS:
        show_help()
        sys.exit(0 if name == "help" else 1)
    try:
        COMMANDS[name]()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
