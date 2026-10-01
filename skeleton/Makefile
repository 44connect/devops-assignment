# webOS Subscription Service - Makefile (Windows / macOS)
#
# 실제 동작은 tasks.py 에 있습니다.
# make 가 없는 Windows 에서는 `python tasks.py <command>` 로 동일하게 실행하세요.

ifeq ($(OS),Windows_NT)
    PYTHON := python
else
    PYTHON := python3
endif

PORT ?= 8000
REQ ?=
export PORT REQ

TARGETS := help install build check run test ci clean
.PHONY: $(TARGETS)

$(TARGETS):
	$(PYTHON) tasks.py $@
