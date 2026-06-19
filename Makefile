# Run all targets from the repo root.
.PHONY: setup tap-check run run-all dry-all clean test
PY ?= .venv/bin/python

setup:
	test -d .venv || python3 -m venv .venv
	$(PY) -m pip install -e ".[dev]"

tap-check:
	claude-tap --help >/dev/null && echo "claude-tap OK"

test:
	$(PY) -m pytest -q

# Single cell: make run TASK=coding CONDITION=single_agent REP=1
run:
	$(PY) -m harness.runner --task $(TASK) --condition $(CONDITION) --rep $(REP)

run-all:
	$(PY) -m harness.runner --all

dry-all:
	$(PY) -m harness.runner --all --dry-run

clean:
	rm -rf data/raw/*
