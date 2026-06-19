# Instrumentation & Real Workloads Implementation Plan (Plan A2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the merged capture harness so each run captures TTFT (true time-to-first-token) + task-level success + kernel performance, driven by two real workloads (a GPU-kernel coding task and a deep-research task), so the experiment fully demonstrates Claude Code's capability across the 5 orchestration conditions.

**Architecture:** A thin streaming TTFT proxy sits *behind* claude-tap (via `--tap-target`) and timestamps each request's SSE stream. Two workloads run in isolated per-run scratch dirs; the coding task carries a `check_kernel.sh` self-test tool and is scored (correctness + speedup) by the existing KernelGYM `/evaluate` endpoint, the research task by a section/citation scorer. The runner orchestrates services, runs the launcher, then collects TTFT rows, snapshots artifacts, scores, and writes everything into `run_meta.json`.

**Tech Stack:** Python 3.11+ (asyncio + httpx for the proxy; stdlib elsewhere), pytest, Bash, claude-tap, the drkernel-lab KernelGYM (`:10908`) + drkernel310 aarch64 env.

## Global Constraints

- Model fixed `claude-sonnet-4-6` (all conditions); reasoning **effort = default** (launchers set no `--effort`).
- Kernel problem (locked): `76_Gemm_Add_ReLU` from `/home/yubaifeng/e84381970/drkernel-lab/distill/problems/problems_sample.jsonl`.
- Coding success = `correctness == true AND decoy_kernel == false`; performance = `speedup = reference_runtime / kernel_runtime` (KernelGYM, mean of 100 CUDA-event trials, clipped 3.0).
- Research success = `report.md` exists + all 6 sections present + ≥12 distinct cited URLs.
- KernelGYM URL `http://127.0.0.1:10908`; drkernel python `/home/yubaifeng/e84381970/envs/drkernel310/bin/python3.10`.
- **`docker stop qwen` before any GPU eval** (it pins ~95 GB → OOM). `apt` is broken (no installs). Blackwell sm_121: CUDA-event timing sound; `torch.profiler` flaky (gym handles fallback).
- TTFT proxy must stream byte-transparently (no buffering, headers preserved) so caching/usage are unperturbed.
- Use the project venv `.venv/bin/python` (no bare `python`); run tests from the repo root.
- BUILD-ONLY: do NOT run the real 30-cell sweep / workload runs. Validate with unit tests, the live gym on pre-written kernels (local GPU, no model API), and at most one tiny `claude -p` probe for proxy fidelity.

This plan adds `httpx` to the dev/runtime deps (Task 1).

---

### Task 1: Add httpx dependency + SSE timing parser (`ttft_parse.py`)

**Files:**
- Modify: `pyproject.toml` (add `httpx>=0.27` to `dependencies`)
- Create: `harness/capture/ttft_parse.py`
- Test: `tests/test_ttft_parse.py`

**Interfaces:**
- Produces: `class SseTimer` with `feed(now: float, raw_line: str) -> None` and properties `t_message_start: float|None`, `t_first_text: float|None`, `t_done: float|None`; and `timing_row(request_id, t_send, t_done) -> dict`.

The Anthropic SSE stream emits lines like `event: message_start`, `event: content_block_delta`, `event: message_stop`. `SseTimer` records the wall-clock time of the first `message_start` (≈ prefill done), the first `content_block_delta` (≈ first token = TTFT), and `message_stop` (≈ done).

- [ ] **Step 1: Write the failing test**

`tests/test_ttft_parse.py`:
```python
from harness.capture.ttft_parse import SseTimer


def test_sse_timer_captures_milestones():
    t = SseTimer()
    t.feed(1.0, "event: message_start")
    t.feed(1.0, 'data: {"type":"message_start"}')
    t.feed(2.0, "event: content_block_start")
    t.feed(3.0, "event: content_block_delta")        # first token
    t.feed(4.0, "event: content_block_delta")        # later token (ignored)
    t.feed(5.0, "event: message_stop")
    assert t.t_message_start == 1.0
    assert t.t_first_text == 3.0
    assert t.t_done == 5.0


def test_timing_row_shape():
    t = SseTimer()
    t.feed(1.5, "event: message_start")
    t.feed(2.5, "event: content_block_delta")
    t.feed(3.5, "event: message_stop")
    row = t.timing_row("req_abc", t_send=1.0, t_done=3.6)
    assert row["request_id"] == "req_abc"
    assert row["ttft_s"] == 2.5 - 1.0
    assert row["prefill_s"] == 1.5 - 1.0
    assert row["total_s"] == 3.6 - 1.0
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_ttft_parse.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'harness.capture.ttft_parse'`.

- [ ] **Step 3: Implement + add dep**

In `pyproject.toml`, add `"httpx>=0.27",` to the `dependencies` list. Then `.venv/bin/pip install -e ".[dev]"`.

`harness/capture/ttft_parse.py`:
```python
from __future__ import annotations


class SseTimer:
    """Records SSE milestone wall-clock times from an Anthropic streaming response."""

    def __init__(self) -> None:
        self.t_message_start: float | None = None
        self.t_first_text: float | None = None
        self.t_done: float | None = None

    def feed(self, now: float, raw_line: str) -> None:
        line = raw_line.strip()
        if not line.startswith("event:"):
            return
        event = line[len("event:"):].strip()
        if event == "message_start" and self.t_message_start is None:
            self.t_message_start = now
        elif event == "content_block_delta" and self.t_first_text is None:
            self.t_first_text = now
        elif event == "message_stop":
            self.t_done = now

    def timing_row(self, request_id: str, t_send: float, t_done: float) -> dict:
        def rel(x: float | None) -> float | None:
            return None if x is None else x - t_send
        end = self.t_done if self.t_done is not None else t_done
        return {
            "request_id": request_id,
            "t_send_epoch": t_send,
            "prefill_s": rel(self.t_message_start),
            "ttft_s": rel(self.t_first_text),
            "total_s": end - t_send,
        }
```

- [ ] **Step 4: Run the tests to confirm they pass**

Run: `.venv/bin/python -m pytest tests/test_ttft_parse.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml harness/capture/ttft_parse.py tests/test_ttft_parse.py
git commit -m "feat: SSE timing parser for TTFT capture + httpx dep"
```

---

### Task 2: Streaming TTFT proxy (`ttft_proxy.py`)

**Files:**
- Create: `harness/capture/ttft_proxy.py`
- Test: `tests/test_ttft_proxy.py`

**Interfaces:**
- Consumes: `SseTimer` (Task 1).
- Produces: an ASGI/`http` app `make_app(upstream: str, out_path: Path)` runnable via `uvicorn`/`httpx`; and CLI `python -m harness.capture.ttft_proxy --port P --upstream URL --out FILE`. Per request it appends one JSON line (from `SseTimer.timing_row`, plus `status`) to `out_path`.

The proxy forwards the request to `upstream` with `stream=True`, relays response chunks **unbuffered** while feeding each decoded SSE line to an `SseTimer`, and on completion appends the timing row. It must not alter the body.

- [ ] **Step 1: Write the failing functional test (mock upstream, no real API)**

`tests/test_ttft_proxy.py`:
```python
import json
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from harness.capture.ttft_proxy import make_app


class _Server(uvicorn.Server):
    def install_signal_handlers(self):  # run in a thread
        pass


def _serve(app, port):
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    srv = _Server(cfg)
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    while not srv.started:
        time.sleep(0.01)
    return srv


def test_proxy_records_timing_and_forwards(tmp_path: Path):
    # fake upstream that streams an SSE response with a delay before first token
    async def upstream_app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/event-stream"),
                                (b"request-id", b"req_test123")]})
        chunks = [b"event: message_start\n\n", b"event: content_block_delta\n\n",
                  b"event: message_stop\n\n"]
        for i, c in enumerate(chunks):
            if i == 1:
                time.sleep(0.05)  # simulate prefill latency before first token
            await send({"type": "http.response.body", "body": c, "more_body": i < len(chunks) - 1})

    up = _serve(upstream_app, 8771)
    out = tmp_path / "ttft.jsonl"
    proxy = _serve(make_app(upstream="http://127.0.0.1:8771", out_path=out), 8772)

    r = httpx.post("http://127.0.0.1:8772/v1/messages", json={"x": 1}, timeout=10)
    assert r.status_code == 200
    assert b"message_stop" in r.content  # body forwarded intact
    up.should_exit = True; proxy.should_exit = True
    time.sleep(0.2)

    rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["request_id"] == "req_test123"
    assert rows[0]["ttft_s"] >= 0.04  # the injected delay shows up
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_ttft_proxy.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'harness.capture.ttft_proxy'`.

- [ ] **Step 3: Implement the proxy**

`harness/capture/ttft_proxy.py`:
```python
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route

from harness.capture.ttft_parse import SseTimer


def make_app(upstream: str, out_path: Path) -> Starlette:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    client = httpx.AsyncClient(base_url=upstream, timeout=httpx.Timeout(600.0))

    async def handler(request):
        body = await request.body()
        fwd_headers = {k: v for k, v in request.headers.items()
                       if k.lower() not in ("host", "content-length")}
        t_send = time.time()
        timer = SseTimer()
        req = client.build_request(request.method, request.url.path,
                                   params=request.url.query, headers=fwd_headers, content=body)
        upstream_resp = await client.send(req, stream=True)
        request_id = upstream_resp.headers.get("request-id", "")

        async def stream():
            buf = ""
            async for chunk in upstream_resp.aiter_raw():
                now = time.time()
                try:
                    buf += chunk.decode("utf-8", "ignore")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        timer.feed(now, line)
                except Exception:
                    pass
                yield chunk
            t_done = time.time()
            await upstream_resp.aclose()
            row = timer.timing_row(request_id, t_send, t_done)
            row["status"] = upstream_resp.status_code
            with out_path.open("a") as f:
                f.write(json.dumps(row) + "\n")

        resp_headers = {k: v for k, v in upstream_resp.headers.items()
                        if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")}
        return StreamingResponse(stream(), status_code=upstream_resp.status_code,
                                 headers=resp_headers)

    return Starlette(routes=[Route("/{path:path}", handler, methods=["POST", "GET"])])


def main(argv: list[str] | None = None) -> int:
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--upstream", default="https://api.anthropic.com")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    uvicorn.run(make_app(args.upstream, Path(args.out)), host="127.0.0.1", port=args.port,
                log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Add `"starlette>=0.37"` and `"uvicorn>=0.30"` to `pyproject.toml` dependencies, then `.venv/bin/pip install -e ".[dev]"`.

- [ ] **Step 4: Run the test to confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_ttft_proxy.py -v`
Expected: PASS (1 test) — forwards the body and records `ttft_s ≥ 0.04`.

- [ ] **Step 5: Commit**

```bash
git add harness/capture/ttft_proxy.py tests/test_ttft_proxy.py pyproject.toml
git commit -m "feat: streaming TTFT proxy (records prefill/ttft/total per request)"
```

---

### Task 3: Collect TTFT rows for a run (`collect_ttft.py`)

**Files:**
- Create: `harness/capture/collect_ttft.py`
- Test: `tests/test_collect_ttft.py`

**Interfaces:**
- Produces: `collect_ttft(run_dir: Path, src: Path, since: float, until: float) -> list[dict]` — reads the proxy's JSONL `src`, keeps rows whose `t_send_epoch` is in `[since, until]`, writes them to `run_dir/ttft/ttft.jsonl`, returns the kept rows.

- [ ] **Step 1: Write the failing test**

`tests/test_collect_ttft.py`:
```python
import json
from pathlib import Path
from harness.capture.collect_ttft import collect_ttft


def test_collect_ttft_filters_window(tmp_path: Path):
    src = tmp_path / "all.jsonl"
    src.write_text(
        json.dumps({"request_id": "a", "t_send_epoch": 100.0, "ttft_s": 0.2}) + "\n"
        + json.dumps({"request_id": "b", "t_send_epoch": 200.0, "ttft_s": 0.3}) + "\n"
    )
    run_dir = tmp_path / "run"
    rows = collect_ttft(run_dir, src, since=150.0, until=250.0)
    assert [r["request_id"] for r in rows] == ["b"]
    out = run_dir / "ttft" / "ttft.jsonl"
    assert out.exists()
    assert json.loads(out.read_text().strip())["request_id"] == "b"
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_collect_ttft.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`harness/capture/collect_ttft.py`:
```python
from __future__ import annotations

import json
from pathlib import Path


def collect_ttft(run_dir: Path, src: Path, since: float, until: float) -> list[dict]:
    src = Path(src)
    kept: list[dict] = []
    if src.exists():
        for line in src.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ts = row.get("t_send_epoch")
            if ts is not None and since <= ts <= until:
                kept.append(row)
    dest = Path(run_dir) / "ttft"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "ttft.jsonl").write_text("".join(json.dumps(r) + "\n" for r in kept))
    return kept
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_collect_ttft.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add harness/capture/collect_ttft.py tests/test_collect_ttft.py
git commit -m "feat: collect per-run TTFT rows by time window"
```

---

### Task 4: Code-block extractor (`score/extract.py`)

**Files:**
- Create: `harness/score/__init__.py` (empty)
- Create: `harness/score/extract.py`
- Test: `tests/test_extract.py`

**Interfaces:**
- Produces: `extract_last_code_block(text: str) -> str | None` — returns the content of the LAST fenced code block (matches the gym's `r"\`\`\`(?:\w+)?\s*\n?(.*?)\`\`\`"`, last match), stripped; `None` if none.

- [ ] **Step 1: Write the failing test**

`tests/test_extract.py`:
```python
from harness.score.extract import extract_last_code_block


def test_extracts_last_python_block():
    text = "intro\n```python\nold = 1\n```\nmiddle\n```python\nimport triton\nx = 2\n```\nend"
    assert extract_last_code_block(text) == "import triton\nx = 2"


def test_returns_none_when_no_block():
    assert extract_last_code_block("no code here") is None
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_extract.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`harness/score/extract.py`:
```python
from __future__ import annotations

import re

_BLOCK = re.compile(r"```(?:\w+)?\s*\n?(.*?)```", re.DOTALL)


def extract_last_code_block(text: str) -> str | None:
    matches = _BLOCK.findall(text or "")
    return matches[-1].strip() if matches else None
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_extract.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add harness/score/__init__.py harness/score/extract.py tests/test_extract.py
git commit -m "feat: last-code-block extractor for kernel scoring"
```

---

### Task 5: Kernel scorer (`score/score_coding.py`)

**Files:**
- Create: `harness/score/score_coding.py`
- Test: `tests/test_score_coding.py`

**Interfaces:**
- Consumes: `extract_last_code_block` (Task 4).
- Produces:
  - `build_eval_request(reference_code, kernel_code, task_id) -> dict`
  - `score_kernel(kernel_code, reference_code, kernel_url, task_id="exp") -> dict` (POSTs to `<kernel_url>/evaluate`, returns normalized `{compiled, correctness, decoy_kernel, speedup, reference_runtime_ms, kernel_runtime_ms, success}` where `success = correctness and not decoy_kernel`).

- [ ] **Step 1: Write the failing test (request shape — pure, no network)**

`tests/test_score_coding.py`:
```python
from harness.score.score_coding import build_eval_request, normalize_eval_result


def test_build_eval_request_shape():
    req = build_eval_request("REF", "KERN", "t1")
    assert req == {"task_id": "t1", "reference_code": "REF", "kernel_code": "KERN",
                   "entry_point": "Model", "backend": "triton", "workflow": "kernelbench"}


def test_normalize_success_rule():
    r = normalize_eval_result({"compiled": True, "correctness": True, "decoy_kernel": False,
                               "speedup": 1.8, "reference_runtime": 2.0, "kernel_runtime": 1.1})
    assert r["success"] is True and r["speedup"] == 1.8
    r2 = normalize_eval_result({"correctness": True, "decoy_kernel": True})
    assert r2["success"] is False
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_score_coding.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`harness/score/score_coding.py`:
```python
from __future__ import annotations

import json
import urllib.request


def build_eval_request(reference_code: str, kernel_code: str, task_id: str) -> dict:
    return {
        "task_id": task_id,
        "reference_code": reference_code,
        "kernel_code": kernel_code,
        "entry_point": "Model",
        "backend": "triton",
        "workflow": "kernelbench",
    }


def normalize_eval_result(raw: dict) -> dict:
    correctness = bool(raw.get("correctness"))
    decoy = bool(raw.get("decoy_kernel"))
    return {
        "compiled": bool(raw.get("compiled", raw.get("correctness", False))),
        "correctness": correctness,
        "decoy_kernel": decoy,
        "speedup": raw.get("speedup"),
        "reference_runtime_ms": raw.get("reference_runtime"),
        "kernel_runtime_ms": raw.get("kernel_runtime"),
        "success": correctness and not decoy,
    }


def score_kernel(kernel_code: str, reference_code: str, kernel_url: str,
                 task_id: str = "exp") -> dict:
    body = json.dumps(build_eval_request(reference_code, kernel_code, task_id)).encode()
    req = urllib.request.Request(f"{kernel_url}/evaluate", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=900) as resp:
        return normalize_eval_result(json.loads(resp.read()))
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_score_coding.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Live integration validation (local GPU, NO model API)**

Bring up the gym and score a known-good reference-as-kernel (a trivially-correct torch passthrough will be a decoy; instead use a minimal real Triton kernel sample if available, else assert the endpoint returns the expected keys). Concretely, verify the endpoint is reachable and returns the normalized shape:
```bash
sg docker -c "docker stop qwen" 2>/dev/null || true
bash /home/yubaifeng/e84381970/drkernel-lab/sandbox/gpu-kernelgym/start_gpu_newstd.sh &
sleep 20 && curl -s http://127.0.0.1:10908/health
```
Record in the report that `/health` is OK and that `score_kernel` returns a dict with `success`/`speedup` keys on a sample submission. (Do not run the model.)

- [ ] **Step 6: Commit**

```bash
git add harness/score/score_coding.py tests/test_score_coding.py
git commit -m "feat: kernel scorer via KernelGYM /evaluate (correctness + speedup)"
```

---

### Task 6: Research scorer (`score/score_research.py`)

**Files:**
- Create: `harness/score/score_research.py`
- Test: `tests/test_score_research.py`

**Interfaces:**
- Produces: `score_research(report_path: Path, required_sections: list[str], min_citations: int = 12) -> dict` returning `{exists, sections_present, citation_count, success}` where `success = exists and all sections present and citation_count >= min_citations`. `count_citations(text) -> int` counts distinct http(s) URLs.

- [ ] **Step 1: Write the failing test**

`tests/test_score_research.py`:
```python
from pathlib import Path
from harness.score.score_research import score_research, count_citations


def test_count_citations_distinct():
    text = "see https://a.com and https://a.com and http://b.org"
    assert count_citations(text) == 2


def test_score_research_success(tmp_path: Path):
    report = tmp_path / "report.md"
    urls = "\n".join(f"https://src{i}.com" for i in range(12))
    report.write_text("# FlashAttention\n# Quantized GEMM\n# KV-cache\n"
                      "# Triton vs CUDA\n# Hardware features\n# Autotuning\n" + urls)
    secs = ["FlashAttention", "Quantized GEMM", "KV-cache", "Triton vs CUDA",
            "Hardware features", "Autotuning"]
    r = score_research(report, secs, min_citations=12)
    assert r["success"] is True
    assert r["citation_count"] == 12 and r["sections_present"] == 6


def test_score_research_missing_report(tmp_path: Path):
    r = score_research(tmp_path / "nope.md", ["A"], min_citations=1)
    assert r["exists"] is False and r["success"] is False
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_score_research.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`harness/score/score_research.py`:
```python
from __future__ import annotations

import re
from pathlib import Path

_URL = re.compile(r"https?://[^\s)\]}>\"']+")


def count_citations(text: str) -> int:
    return len({m.rstrip(".,") for m in _URL.findall(text or "")})


def score_research(report_path: Path, required_sections: list[str],
                   min_citations: int = 12) -> dict:
    p = Path(report_path)
    if not p.exists():
        return {"exists": False, "sections_present": 0, "citation_count": 0, "success": False}
    text = p.read_text()
    low = text.lower()
    present = sum(1 for s in required_sections if s.lower() in low)
    cites = count_citations(text)
    success = present == len(required_sections) and cites >= min_citations
    return {"exists": True, "sections_present": present,
            "citation_count": cites, "success": success}
```

- [ ] **Step 4: Run the tests to confirm they pass**

Run: `.venv/bin/python -m pytest tests/test_score_research.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add harness/score/score_research.py tests/test_score_research.py
git commit -m "feat: research scorer (sections + distinct citations)"
```

---

### Task 7: Workload files (kernel prompt/reference/tool + research prompt)

**Files:**
- Create: `tasks/coding/prompt.md` (the problem `prompt_text`)
- Create: `tasks/coding/reference_code.py` (the problem `reference_code`)
- Create: `tasks/coding/check_kernel.sh` (agent self-test tool)
- Create: `tasks/research/prompt.md` (the 6-section survey)
- Create: `scripts/extract_problem.py` (one-off generator that writes the two coding files from the JSONL)

**Interfaces:**
- `check_kernel.sh <solution.py>` prints `compiled/correctness/decoy/speedup` by POSTing to KernelGYM using the drkernel310 python + this task's `reference_code.py`.

- [ ] **Step 1: Generate the coding prompt + reference from the locked problem**

`scripts/extract_problem.py`:
```python
import json
import sys
from pathlib import Path

SRC = "/home/yubaifeng/e84381970/drkernel-lab/distill/problems/problems_sample.jsonl"
NAME = "76_Gemm_Add_ReLU"
out = Path("tasks/coding")
out.mkdir(parents=True, exist_ok=True)
for line in open(SRC):
    p = json.loads(line)
    if p["name"] == NAME:
        (out / "prompt.md").write_text(p["prompt_text"])
        (out / "reference_code.py").write_text(p["reference_code"])
        print("wrote tasks/coding/{prompt.md,reference_code.py}")
        sys.exit(0)
print("problem not found", file=sys.stderr); sys.exit(1)
```
Run: `.venv/bin/python scripts/extract_problem.py`
Expected: writes the two files. Verify `prompt.md` starts with "You write custom Triton kernels…".

- [ ] **Step 2: Write `check_kernel.sh`**

`tasks/coding/check_kernel.sh`:
```bash
#!/usr/bin/env bash
# Self-test tool given to the agent. Usage: check_kernel.sh <solution.py>
# Scores the kernel against the task reference via KernelGYM and prints the verdict.
set -euo pipefail
SOL="$1"
DRPY="${DRKERNEL_PY:-/home/yubaifeng/e84381970/envs/drkernel310/bin/python3.10}"
URL="${KERNELGYM_URL:-http://127.0.0.1:10908}"
REF="$(dirname "$0")/reference_code.py"
"$DRPY" - "$SOL" "$REF" "$URL" <<'PY'
import json, sys, urllib.request
sol, ref, url = sys.argv[1], sys.argv[2], sys.argv[3]
body = json.dumps({"task_id":"selftest","reference_code":open(ref).read(),
    "kernel_code":open(sol).read(),"entry_point":"Model","backend":"triton",
    "workflow":"kernelbench"}).encode()
req = urllib.request.Request(url+"/evaluate", data=body,
    headers={"Content-Type":"application/json"}, method="POST")
r = json.loads(urllib.request.urlopen(req, timeout=900).read())
print(f"compiled={r.get('compiled')} correctness={r.get('correctness')} "
      f"decoy={r.get('decoy_kernel')} speedup={r.get('speedup')}")
PY
```
Run: `chmod +x tasks/coding/check_kernel.sh`

- [ ] **Step 3: Write the research prompt**

`tasks/research/prompt.md`:
```markdown
Write a comprehensive technical report to `report.md` surveying GPU kernel
optimization for LLM inference (2023–2026). Include these six sections, each
with at least two cited sources (URLs) and concrete numbers where available,
plus a comparison table:

1. FlashAttention family (v1 → v3 and variants) — ideas and performance
2. Quantized GEMM kernels (FP8 / INT8 / INT4) for LLM matmuls
3. KV-cache / paged-attention kernels (e.g. PagedAttention)
4. Triton vs CUDA C++ vs CUTLASS / CuTe — productivity and performance tradeoffs
5. Hardware-specific features (Hopper TMA / wgmma, Blackwell FP4 / FP8, async copy)
6. Autotuning and compilers (Triton autotune, TVM, torch.compile / Inductor)

Use web search and cite at least 12 distinct source URLs total. Finish only
after `report.md` contains all six sections, the comparison table, and the citations.
```

- [ ] **Step 4: Validate `check_kernel.sh` against the live gym (local GPU, NO model API)**

With the gym up (Task 5 Step 5), write a tiny reference-equivalent Triton solution by hand to `/tmp/sol.py` (or reuse a known sample), then:
```bash
KERNELGYM_URL=http://127.0.0.1:10908 tasks/coding/check_kernel.sh /tmp/sol.py
```
Expected: prints a `compiled=… correctness=… decoy=… speedup=…` line. Record the output in the report.

- [ ] **Step 5: Commit**

```bash
git add tasks/coding/prompt.md tasks/coding/reference_code.py tasks/coding/check_kernel.sh tasks/research/prompt.md scripts/extract_problem.py
git commit -m "feat: kernel + research workload files and self-test tool"
```

---

### Task 8: Service orchestration (`services.py`)

**Files:**
- Create: `harness/services.py`
- Test: `tests/test_services.py`

**Interfaces:**
- Produces:
  - `health(url: str, timeout=2.0) -> bool` (GET `<url>` returns 2xx)
  - `ensure_services(cfg) -> dict` (best-effort: `docker stop qwen`; start the TTFT proxy if not up; check Redis + KernelGYM health; return `{ttft, kernelgym, redis}` booleans). Pure-testable parts: `health`.

- [ ] **Step 1: Write the failing test**

`tests/test_services.py`:
```python
import threading, time
import uvicorn
from harness.services import health


class _S(uvicorn.Server):
    def install_signal_handlers(self): pass


async def ok_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def test_health_true_when_up_false_when_down():
    cfg = uvicorn.Config(ok_app, host="127.0.0.1", port=8799, log_level="error")
    s = _S(cfg); th = threading.Thread(target=s.run, daemon=True); th.start()
    while not s.started: time.sleep(0.01)
    assert health("http://127.0.0.1:8799") is True
    s.should_exit = True; time.sleep(0.2)
    assert health("http://127.0.0.1:8799") is False
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_services.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`harness/services.py`:
```python
from __future__ import annotations

import subprocess
import urllib.request


def health(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def stop_qwen() -> None:
    # Frees ~95 GB unified memory; ignore errors (container may be absent).
    subprocess.run(["sg", "docker", "-c", "docker stop qwen"],
                   capture_output=True, text=True)


def ensure_services(kernelgym_url: str, redis_health_url: str | None = None) -> dict:
    stop_qwen()
    return {
        "kernelgym": health(f"{kernelgym_url}/health"),
        "redis": health(redis_health_url) if redis_health_url else None,
    }
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_services.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add harness/services.py tests/test_services.py
git commit -m "feat: service health checks + qwen stop"
```

---

### Task 9: Feedback-loop launchers + `--tap-target` wiring

**Files:**
- Modify: `harness/capture/run_tap.sh` (add `--tap-target` to route through the TTFT proxy)
- Modify: `harness/conditions/ralph_loop.sh`, `harness/conditions/loop_dynamic.sh` (inject eval feedback)
- Create: `harness/conditions/_feedback.sh` (shared: score current solution.py, emit a feedback line)

**Interfaces:**
- `run_tap.sh` now reads env `TTFT_PORT`; if set, passes `--tap-target http://127.0.0.1:$TTFT_PORT` to claude-tap.
- Launchers receive `<prompt_file> <run_dir> <model>` and run inside the per-run scratch cwd (set by the runner). The coding scratch dir contains `check_kernel.sh`, `reference_code.py`; the agent writes `solution.py`.

- [ ] **Step 1: Add `--tap-target` to `run_tap.sh`**

Replace the `exec` line in `harness/capture/run_tap.sh` with:
```bash
TAP_ARGS=(--tap-no-live --tap-no-open)
if [ -n "${TTFT_PORT:-}" ]; then TAP_ARGS+=(--tap-target "http://127.0.0.1:${TTFT_PORT}"); fi
exec "$TAP" "${TAP_ARGS[@]}" -- "$@"
```

- [ ] **Step 2: Write the shared feedback helper**

`harness/conditions/_feedback.sh`:
```bash
#!/usr/bin/env bash
# Prints an eval-feedback block for the current solution.py, or "" if none yet.
# Usage: _feedback.sh <scratch_dir>
set -euo pipefail
DIR="$1"
[ -f "$DIR/solution.py" ] || { echo ""; exit 0; }
if [ -x "$DIR/check_kernel.sh" ]; then
  OUT="$("$DIR/check_kernel.sh" "$DIR/solution.py" 2>&1 || true)"
  echo "Previous attempt eval result: $OUT. Improve correctness first, then speedup."
fi
```

- [ ] **Step 3: Rewrite `ralph_loop.sh` to inject feedback (fresh context each iteration)**

`harness/conditions/ralph_loop.sh`:
```bash
#!/usr/bin/env bash
# Usage: ralph_loop.sh <prompt_file> <run_dir> <model>   (external loop, fresh context, eval feedback)
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${RALPH_ITERS:-5}"
BASE="$(cat "$PROMPT_FILE")"
for i in $(seq 1 "$ITERS"); do
  FB="$("$HERE/_feedback.sh" "$PWD")"
  PROMPT="$BASE
$FB
Write your kernel to solution.py and run: bash check_kernel.sh solution.py to test it."
  "$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$PROMPT"
done
```

- [ ] **Step 4: Rewrite `loop_dynamic.sh` to inject feedback (retained context)**

`harness/conditions/loop_dynamic.sh`:
```bash
#!/usr/bin/env bash
# Usage: loop_dynamic.sh <prompt_file> <run_dir> <model>   (same session, retained context, eval feedback)
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${LOOP_ITERS:-5}"
# NOTE: --continue resumes the most-recent session for this cwd. Cells MUST run sequentially.
BASE="$(cat "$PROMPT_FILE")
Write your kernel to solution.py and run: bash check_kernel.sh solution.py to test it."
"$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$BASE"
for i in $(seq 2 "$ITERS"); do
  FB="$("$HERE/_feedback.sh" "$PWD")"
  "$HERE/../capture/run_tap.sh" -- --model "$MODEL" --continue -p "$FB
Continue improving solution.py; re-test with check_kernel.sh."
done
```

- [ ] **Step 5: Make scripts executable + syntax-check (no live run)**

Run:
```bash
chmod +x harness/conditions/_feedback.sh
bash -n harness/conditions/ralph_loop.sh harness/conditions/loop_dynamic.sh harness/capture/run_tap.sh harness/conditions/_feedback.sh
```
Expected: no output (syntax OK).

- [ ] **Step 6: Commit**

```bash
git add harness/capture/run_tap.sh harness/conditions/_feedback.sh harness/conditions/ralph_loop.sh harness/conditions/loop_dynamic.sh
git commit -m "feat: --tap-target wiring + eval-feedback loops for kernel task"
```

---

### Task 10: Runner wiring — scratch cwd, TTFT window, scoring, run_meta

**Files:**
- Modify: `config/experiment.yaml` (add instrumentation config)
- Modify: `config/tasks/coding.yaml`, `config/tasks/research.yaml` (task `kind` + required sections + seed files)
- Modify: `harness/config.py` (carry new fields)
- Modify: `harness/runner.py` (`execute`: scratch dir, services, ttft collect, artifact snapshot, scoring, run_meta)
- Test: `tests/test_runner_score_wiring.py`

**Interfaces:**
- Consumes: `collect_ttft`, `score_kernel`/`score_research` + `extract_last_code_block`, `ensure_services`, `restore_workspace`.
- Produces: `score_run(plan, scratch_dir, exp) -> dict` (dispatches on task kind; returns the metric dict merged into `run_meta`).

- [ ] **Step 1: Extend config**

Append to `config/experiment.yaml`:
```yaml
instrumentation:
  drkernel_python: /home/yubaifeng/e84381970/envs/drkernel310/bin/python3.10
  kernelgym_url: http://127.0.0.1:10908
  ttft_port: 8770
  ttft_log: /tmp/cc-exp-ttft.jsonl
  problem_name: 76_Gemm_Add_ReLU
```
Set `config/tasks/coding.yaml` to add `kind: coding` and `seed_files: [tasks/coding/check_kernel.sh, tasks/coding/reference_code.py]`; `config/tasks/research.yaml` to add `kind: research` and `required_sections: ["FlashAttention", "Quantized GEMM", "KV-cache", "Triton vs CUDA", "Hardware", "Autotuning"]`.

Extend `harness/config.py` `ExperimentConfig` with `kernelgym_url: str`, `drkernel_python: str`, `ttft_port: int`, `ttft_log: Path`, and `TaskConfig` with `kind: str`, `required_sections: list[str]`, `seed_files: list[Path]` (parse with `.get(...)` defaults so existing tests still pass).

- [ ] **Step 2: Write the failing wiring test (boundaries stubbed — no live calls)**

`tests/test_runner_score_wiring.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path

import harness.runner as R
from harness.config import ExperimentConfig, TaskConfig, ConditionConfig
from harness.runner import plan_run, execute


def _exp(tmp):
    return ExperimentConfig(
        model="claude-sonnet-4-6", reps=1, conditions=["single_agent"], tasks=["research"],
        data_raw=tmp / "data/raw", claude_projects=tmp / "projects",
        proxy_host="127.0.0.1", proxy_port=8080,
        kernelgym_url="http://127.0.0.1:10908",
        drkernel_python="/usr/bin/true", ttft_port=8770, ttft_log=tmp / "ttft.jsonl",
    )


def test_execute_scores_research_and_writes_meta(tmp_path, monkeypatch):
    exp = _exp(tmp_path)
    prompt = tmp_path / "prompt.md"; prompt.write_text("write report.md")
    task = TaskConfig("research", prompt, None, None, kind="research",
                      required_sections=["A"], seed_files=[])
    cond = ConditionConfig("single_agent", tmp_path / "l.sh", "")
    plan = plan_run(exp, task, cond, 1, datetime(2026, 6, 19, 12, tzinfo=timezone.utc))

    monkeypatch.setattr(R.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(R, "collect", lambda *a, **k: [])
    monkeypatch.setattr(R, "collect_tap", lambda *a, **k: [])
    monkeypatch.setattr(R, "collect_ttft", lambda *a, **k: [{"ttft_s": 0.3}])
    monkeypatch.setattr(R, "ensure_services", lambda *a, **k: {"kernelgym": True})
    monkeypatch.setattr(R, "gather_versions", lambda: {})
    # research scorer sees no report.md in the scratch dir -> success False, but recorded
    out = execute(plan, exp, dry_run=False)
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["task"] == "research"
    assert "success" in meta and "ttft" in meta
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_runner_score_wiring.py -v`
Expected: FAIL (execute lacks scoring/ttft wiring / new config fields).

- [ ] **Step 4: Implement the wiring**

Add imports to `harness/runner.py`:
```python
from harness.capture.collect_ttft import collect_ttft
from harness.services import ensure_services
from harness.score.score_research import score_research
from harness.score.score_coding import score_kernel
from harness.score.extract import extract_last_code_block
```
Add a scorer dispatch:
```python
def score_run(task, scratch_dir: Path, exp) -> dict:
    if task.kind == "research":
        return {"score": score_research(scratch_dir / "report.md", task.required_sections)}
    if task.kind == "coding":
        sol = scratch_dir / "solution.py"
        ref = Path("tasks/coding/reference_code.py")
        if sol.exists() and ref.exists():
            res = score_kernel(sol.read_text(), ref.read_text(), exp.kernelgym_url)
        else:
            res = {"success": False, "reason": "no solution.py"}
        return {"score": res}
    return {"score": {"success": None}}
```
In `execute` (non-dry path), replace the body so it: creates a per-run scratch dir `run_dir/"workspace"`, copies `task.seed_files` into it, runs `ensure_services`, records `start_dt`, runs the launcher **with `cwd=scratch` and `env` including `TTFT_PORT`**, records `end_dt`, then `collect`, `collect_tap`, `collect_ttft(run_dir, exp.ttft_log, start_dt.timestamp(), end_dt.timestamp())`, snapshots artifacts (the scratch dir is already under run_dir), computes `score_run`, and writes `run_meta` with the extra keys:
```python
    scratch = run_dir / "workspace"; scratch.mkdir(parents=True, exist_ok=True)
    for f in plan.task.seed_files:
        shutil.copy2(f, scratch / Path(f).name)
    ensure_services(exp.kernelgym_url)
    (run_dir / "tap").mkdir(parents=True, exist_ok=True)
    start_dt = _now(); start = start_dt.timestamp()
    env = {**os.environ, "TTFT_PORT": str(exp.ttft_port),
           "KERNELGYM_URL": exp.kernelgym_url, "DRKERNEL_PY": exp.drkernel_python}
    launcher = Path(plan.condition.launcher).resolve()
    subprocess.run([str(launcher), str(Path(prompt_file).resolve()),
                    str(run_dir.resolve()), plan.model],
                   cwd=str(scratch), check=True, env=env)
    end_dt = _now()
    transcripts = collect(run_dir, exp.claude_projects, str(scratch.resolve()), since=start)
    tap_files = collect_tap(run_dir, start_dt, end_dt)
    ttft_rows = collect_ttft(run_dir, exp.ttft_log, start, end_dt.timestamp())
    score = score_run(plan.task, scratch, exp)["score"]
    write_run_meta(run_dir, {
        "run_id": plan.run_id, "task": plan.task.name, "condition": plan.condition.name,
        "rep": plan.rep, "model": plan.model,
        "started_utc": start_dt.isoformat(), "ended_utc": end_dt.isoformat(),
        "completion_time_s": (end_dt - start_dt).total_seconds(),
        "transcripts": [str(p.relative_to(run_dir)) for p in transcripts],
        "tap": [str(p.relative_to(run_dir)) for p in tap_files],
        "ttft": ttft_rows, "success": score.get("success"), "score": score,
        "versions": gather_versions(),
    })
    return run_dir
```
Add `import os` and `import shutil` to `runner.py` if not present.

- [ ] **Step 5: Run the wiring test to confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_runner_score_wiring.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite + dry-all**

Run: `make test` → all green (Plan A tests + the new ones).
Run: `.venv/bin/python -m harness.runner --all --dry-run | grep -c '^=== '` → 30.

- [ ] **Step 7: Commit**

```bash
git add config/ harness/config.py harness/runner.py tests/test_runner_score_wiring.py
git commit -m "feat: wire scratch dir, TTFT, services, scoring into runner + run_meta"
```

---

### Task 11: TTFT proxy fidelity probe + start helper (single tiny live check)

**Files:**
- Create: `harness/capture/start_ttft.sh` (launch the proxy in the background on `ttft_port`)
- Modify: `Makefile` (add `ttft-up` + `services-up` targets)
- Create: `docs/superpowers/a2-validation.md` (record the fidelity probe result)

**Interfaces:**
- `start_ttft.sh <port> <out>` runs `python -m harness.capture.ttft_proxy` in the background.

- [ ] **Step 1: Write the start helper + Makefile targets**

`harness/capture/start_ttft.sh`:
```bash
#!/usr/bin/env bash
# Usage: start_ttft.sh <port> <out_jsonl>
set -euo pipefail
PORT="$1"; OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/../../.venv/bin/python"
nohup "$PY" -m harness.capture.ttft_proxy --port "$PORT" --out "$OUT" >/tmp/ttft_proxy.log 2>&1 &
echo "ttft_proxy pid $! on :$PORT -> $OUT"
```
Add to `Makefile`:
```makefile
ttft-up:
	bash harness/capture/start_ttft.sh 8770 /tmp/cc-exp-ttft.jsonl

services-up:
	sg docker -c "docker stop qwen" || true
	bash /home/yubaifeng/e84381970/drkernel-lab/sandbox/gpu-kernelgym/start_gpu_newstd.sh &
	$(MAKE) ttft-up
```
Run: `chmod +x harness/capture/start_ttft.sh && bash -n harness/capture/start_ttft.sh`

- [ ] **Step 2: One tiny fidelity probe through the full chain (single trivial `claude -p`)**

This is the ONLY model call in this plan — a one-word probe to confirm the chain works and caching is unperturbed:
```bash
make ttft-up
TTFT_PORT=8770 harness/conditions/single_agent.sh <(echo "Reply with only READY.") /tmp/fidchk claude-sonnet-4-6
```
Then confirm: (a) `/tmp/cc-exp-ttft.jsonl` gained a row with `ttft_s`/`prefill_s`/`total_s`; (b) the run's claude-tap usage (from SQLite) matches what the JSONL transcript reports for the same request (re-use the Plan A fidelity method). Record both in `docs/superpowers/a2-validation.md`. If usage differs, STOP and report — the proxy is perturbing requests.

- [ ] **Step 3: Commit**

```bash
git add harness/capture/start_ttft.sh Makefile docs/superpowers/a2-validation.md
git commit -m "feat: TTFT proxy start helper + fidelity probe results"
```

---

## Self-Review

**Spec coverage:**
- §3 TTFT proxy → Tasks 1, 2, 3, 9 (`--tap-target`), 11 (fidelity). ✓
- §4 kernel workload + self-test + feedback loops + external scorer → Tasks 5, 7, 9. ✓
- §5 research workload + scorer → Tasks 6, 7. ✓
- §6 per-run scorer + artifact capture + run_meta keys → Task 10. ✓
- §7 isolated workspaces + service orchestration → Tasks 8, 10. ✓
- §8 metric coverage (TTFT, success, speedup) → Tasks 3/10 (ttft), 5/6/10 (success+speedup). ✓
- §10 locked params (sonnet, default effort, problem 76) → Global Constraints + Task 7. ✓
- §9 qwen-stop / gym health → Task 8. ✓

**Placeholder scan:** Live-dependent steps (gym scoring, fidelity probe) are concrete commands with expected output, not placeholders; their bodies are fully specified. No "TBD"/"handle errors"/"similar to". ✓

**Type consistency:** `score_kernel`/`normalize_eval_result` keys (`success`, `speedup`, `correctness`, `decoy_kernel`) consistent across Tasks 5, 10. `collect_ttft(run_dir, src, since, until)` signature consistent across Tasks 3, 10. `score_research(report_path, required_sections, min_citations)` consistent across Tasks 6, 10. `SseTimer.timing_row` keys (`ttft_s`, `prefill_s`, `total_s`, `request_id`, `t_send_epoch`) consistent across Tasks 1, 2, 3. ✓

---

## Hand-off to Plan B (analysis)

Plan B now has, per run in `data/raw/<run_id>/`: `tap/` (bodies + usage), `transcripts/` (nested), `ttft/ttft.jsonl` (prefill/ttft/total per request), `workspace/` (artifacts: `solution.py` / `report.md`), and `run_meta.json` with `success`, `completion_time_s`, `score` (coding: `correctness`/`speedup`/runtimes; research: sections/citations). Figures: cache-accumulation, context-growth-by-component, **plus** TTFT/latency distributions, success rate, and speedup — across the 5 conditions.
