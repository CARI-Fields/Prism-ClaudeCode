# Run all targets from the repo root.
.PHONY: setup tap-check run run-all dry-all clean test ttft-up services-up analyze serve deploy-space
PY ?= .venv/bin/python

setup:
	test -d .venv || python3 -m venv .venv
	$(PY) -m pip install -e ".[dev]"

tap-check:
	.venv/bin/claude-tap --help >/dev/null && echo "claude-tap OK"

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

ttft-up:
	bash harness/capture/start_ttft.sh 8770 /tmp/cc-exp-ttft.jsonl

services-up:
	sg docker -c "docker stop qwen" || true
	bash /home/yubaifeng/e84381970/drkernel-lab/sandbox/gpu-kernelgym/start_gpu_newstd.sh &
	$(MAKE) ttft-up

analyze:
	$(PY) -c "from analysis.report import generate; print(generate('data/raw','data/processed','figures','reports/report.md'))"

serve:
	DATA_DIR=data/processed $(PY) -m uvicorn serve.app:app --reload --port 8799

deploy-space:
	bash scripts/deploy_space.sh
