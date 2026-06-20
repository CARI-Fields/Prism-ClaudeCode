# Plan B — Analysis Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn captured `data/raw/<run_id>/` data into tidy parquet tables, figures (headline: prefix-cache-hit accumulation), and a report comparing orchestration conditions.

**Architecture:** Pure parsers (tap list / ttft / run_meta → rows) feed `build_tables.py` which writes `turns`/`components`/`runs` parquet; `metrics.py` computes the curves; `plots/` render figures; `report.py` stitches a markdown report. Built/tested against a committed real captured cell.

**Tech Stack:** Python 3.11+, pandas, pyarrow, matplotlib (Agg), pytest. Project venv `.venv/bin/python`.

## Global Constraints

- Use the project venv `.venv/bin/python` (no bare `python`); run tests from the repo root.
- **Real tap export shape:** a LIST of turn objects `{turn, timestamp(ISO), duration_ms, model, system, tools, messages, response}`; usage at `turn["response"]["usage"]` (`input_tokens, cache_read_input_tokens, cache_creation_input_tokens, cache_creation{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}, output_tokens`). No `request_id`.
- **ttft row:** `{request_id, t_send_epoch, prefill_s, ttft_s, total_s, status}`.
- **ttft↔tap join:** `tap_start = parse_iso(tap.timestamp) − duration_ms/1000`; match the nearest `ttft.t_send_epoch` within `0.5s`; unmatched → null latency (not dropped).
- **Prefix-cache-hit accumulation (headline):** per run, `cumsum(cache_read)` over `request_index`; companions `cumsum(cache_creation)`, `cumsum(input_tokens)`; ratio `cumsum(cache_read)/cumsum(cache_read+cache_creation+input)`.
- Component token estimates are anchored so per-request component tokens sum to that request's prompt tokens (`input + cache_read + cache_creation`).
- `data/processed/` and `figures/` are outputs; `data/processed/` is gitignored (large), `figures/` committed.

This plan adds `pandas`, `pyarrow`, `matplotlib` to deps (Task 1).

---

### Task 1: Deps, tokenizer, and the real-cell fixture

**Files:**
- Modify: `pyproject.toml` (add `pandas>=2.0`, `pyarrow>=15`, `matplotlib>=3.8`)
- Create: `analysis/__init__.py`, `analysis/parse/__init__.py` (empty)
- Create: `analysis/parse/tokenizer.py`
- Create: `tests/fixtures/real_cell/{tap.json, ttft.jsonl, run_meta.json}` (copied from a real run)
- Test: `tests/test_tokenizer.py`

**Interfaces:**
- Produces: `estimate_tokens(text: str) -> int`; `scale_to_total(parts: dict[str,float], total: int) -> dict[str,int]`.

- [ ] **Step 1: Add deps + copy the real-cell fixture**

```bash
.venv/bin/python - <<'PY'
import re
p="pyproject.toml"; s=open(p).read()
s=s.replace('"pyyaml>=6.0",', '"pyyaml>=6.0",\n    "pandas>=2.0",\n    "pyarrow>=15",\n    "matplotlib>=3.8",')
open(p,"w").write(s); print("deps added")
PY
.venv/bin/pip install -e ".[dev]" >/dev/null 2>&1 && echo installed
mkdir -p analysis/parse tests/fixtures/real_cell
: > analysis/__init__.py; : > analysis/parse/__init__.py
D=$(ls -d data/raw/coding__single_agent__01__* | head -1)
cp "$D"/tap/*.json tests/fixtures/real_cell/tap.json
cp "$D"/ttft/ttft.jsonl tests/fixtures/real_cell/ttft.jsonl
cp "$D"/run_meta.json tests/fixtures/real_cell/run_meta.json
echo "fixture: $(ls tests/fixtures/real_cell)"
```
Expected: deps installed; `tests/fixtures/real_cell/` has `tap.json ttft.jsonl run_meta.json`.

- [ ] **Step 2: Write the failing tokenizer test**

`tests/test_tokenizer.py`:
```python
from analysis.parse.tokenizer import estimate_tokens, scale_to_total


def test_estimate_tokens_chars_over_4():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 40) == 10


def test_scale_to_total_sums_to_total():
    parts = {"system": 30.0, "tools": 60.0, "messages": 10.0}
    out = scale_to_total(parts, total=1000)
    assert sum(out.values()) == 1000
    assert out["tools"] > out["system"] > out["messages"]


def test_scale_to_total_zero_parts():
    assert scale_to_total({"a": 0.0, "b": 0.0}, total=100) == {"a": 0, "b": 0}
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_tokenizer.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'analysis.parse.tokenizer'`.

- [ ] **Step 4: Implement**

`analysis/parse/tokenizer.py`:
```python
from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough local token estimate (~4 chars/token). Used for relative composition;
    callers anchor totals to reported usage via scale_to_total."""
    return len(text or "") // 4


def scale_to_total(parts: dict[str, float], total: int) -> dict[str, int]:
    """Scale part sizes so they sum to `total` (largest-remainder rounding)."""
    s = sum(parts.values())
    if s <= 0:
        return {k: 0 for k in parts}
    raw = {k: v / s * total for k, v in parts.items()}
    out = {k: int(v) for k, v in raw.items()}
    rem = total - sum(out.values())
    for k in sorted(parts, key=lambda k: raw[k] - out[k], reverse=True):
        if rem <= 0:
            break
        out[k] += 1
        rem -= 1
    return out
```

- [ ] **Step 5: Run to confirm pass + commit**

Run: `.venv/bin/python -m pytest tests/test_tokenizer.py -v` → PASS (3).
```bash
git add pyproject.toml analysis/__init__.py analysis/parse/__init__.py analysis/parse/tokenizer.py tests/test_tokenizer.py tests/fixtures/real_cell/
git commit -m "feat: analysis deps, token estimator, real-cell fixture"
```

---

### Task 2: Parse tap (turns + components)

**Files:**
- Create: `analysis/parse/parse_tap.py`
- Test: `tests/test_parse_tap.py`

**Interfaces:**
- Consumes: `estimate_tokens` (Task 1).
- Produces:
  - `parse_iso(ts: str) -> float` (ISO → epoch seconds)
  - `tap_turns(tap: list) -> list[dict]` — per request: `request_index, ts_start_epoch, input_tokens, output_tokens, cache_read, cache_creation_5m, cache_creation_1h, duration_ms, model`
  - `tap_components(tap: list) -> list[dict]` — per (request_index, component) with `bytes, est_tokens` (components: `system_prompt, tools, messages`), token-anchored to the request's prompt tokens.

- [ ] **Step 1: Write the failing test (against the real fixture)**

`tests/test_parse_tap.py`:
```python
import json
from pathlib import Path
from analysis.parse.parse_tap import parse_iso, tap_turns, tap_components

FIX = Path("tests/fixtures/real_cell/tap.json")


def test_parse_iso_to_epoch():
    assert abs(parse_iso("2026-06-19T21:02:44.554578+00:00") - 1781902964.554578) < 1e-3


def test_tap_turns_shape_and_start_time():
    tap = json.loads(FIX.read_text())
    rows = tap_turns(tap)
    assert len(rows) == len(tap)
    r0 = rows[0]
    for k in ("request_index", "ts_start_epoch", "input_tokens", "output_tokens",
              "cache_read", "cache_creation_5m", "cache_creation_1h", "duration_ms", "model"):
        assert k in r0
    assert r0["request_index"] == 0
    # start = completion timestamp - duration
    assert r0["ts_start_epoch"] == parse_iso(tap[0]["timestamp"]) - tap[0]["duration_ms"] / 1000


def test_tap_components_anchored_to_prompt_tokens():
    tap = json.loads(FIX.read_text())
    comps = tap_components(tap)
    # all three components present for request 0
    c0 = [c for c in comps if c["request_index"] == 0]
    assert {c["component"] for c in c0} == {"system_prompt", "tools", "messages"}
    # est_tokens for a request sum to its prompt tokens (input+cache_read+cache_creation)
    u = tap[0]["response"]["usage"]
    prompt = u["input_tokens"] + u["cache_read_input_tokens"] + u["cache_creation_input_tokens"]
    assert sum(c["est_tokens"] for c in c0) == prompt
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_parse_tap.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`analysis/parse/parse_tap.py`:
```python
from __future__ import annotations

import json
from datetime import datetime

from analysis.parse.tokenizer import scale_to_total


def parse_iso(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def _usage(turn: dict) -> dict:
    return (turn.get("response") or {}).get("usage") or {}


def tap_turns(tap: list) -> list[dict]:
    rows = []
    for i, turn in enumerate(tap):
        u = _usage(turn)
        cc = u.get("cache_creation") or {}
        ts = turn.get("timestamp")
        dur = turn.get("duration_ms") or 0
        start = parse_iso(ts) - dur / 1000 if ts else None
        rows.append({
            "request_index": i,
            "ts_start_epoch": start,
            "input_tokens": u.get("input_tokens", 0),
            "output_tokens": u.get("output_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "cache_creation_5m": cc.get("ephemeral_5m_input_tokens", 0),
            "cache_creation_1h": cc.get("ephemeral_1h_input_tokens", 0),
            "duration_ms": dur,
            "model": turn.get("model"),
        })
    return rows


def _component_bytes(value) -> int:
    """Size of a request component (system/tools/messages). Handles inline content
    and claude-tap blob references (which carry a 'bytes' field)."""
    if value is None:
        return 0
    if isinstance(value, dict) and "__claude_tap_blob_ref__" in value:
        return int(value["__claude_tap_blob_ref__"].get("bytes", 0))
    if isinstance(value, list):
        return sum(_component_bytes(v) for v in value)
    return len(json.dumps(value, ensure_ascii=False))


def tap_components(tap: list) -> list[dict]:
    rows = []
    for i, turn in enumerate(tap):
        u = _usage(turn)
        prompt = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                  + u.get("cache_creation_input_tokens", 0))
        sizes = {
            "system_prompt": float(_component_bytes(turn.get("system"))),
            "tools": float(_component_bytes(turn.get("tools"))),
            "messages": float(_component_bytes(turn.get("messages"))),
        }
        est = scale_to_total(sizes, prompt)
        for comp in ("system_prompt", "tools", "messages"):
            rows.append({"request_index": i, "component": comp,
                         "bytes": int(sizes[comp]), "est_tokens": est[comp]})
    return rows
```

- [ ] **Step 4: Run to confirm pass + commit**

Run: `.venv/bin/python -m pytest tests/test_parse_tap.py -v` → PASS (3).
```bash
git add analysis/parse/parse_tap.py tests/test_parse_tap.py
git commit -m "feat: parse real list-format tap into turn + component rows"
```

---

### Task 3: Parse ttft + start-time join

**Files:**
- Create: `analysis/parse/parse_ttft.py`
- Test: `tests/test_parse_ttft.py`

**Interfaces:**
- Produces:
  - `load_ttft(path: Path) -> list[dict]`
  - `join_ttft(turn_rows: list[dict], ttft_rows: list[dict], tol: float = 0.5) -> list[dict]` — adds `ttft_s, prefill_s, total_s` to each turn row by matching `turn["ts_start_epoch"]` to the nearest `ttft["t_send_epoch"]` within `tol`; null when no match.

- [ ] **Step 1: Write the failing test**

`tests/test_parse_ttft.py`:
```python
import json
from pathlib import Path
from analysis.parse.parse_ttft import load_ttft, join_ttft
from analysis.parse.parse_tap import tap_turns


def test_load_ttft():
    rows = load_ttft(Path("tests/fixtures/real_cell/ttft.jsonl"))
    assert rows and "t_send_epoch" in rows[0] and "ttft_s" in rows[0]


def test_join_matches_by_start_time():
    tap = json.loads(Path("tests/fixtures/real_cell/tap.json").read_text())
    turns = tap_turns(tap)
    ttft = load_ttft(Path("tests/fixtures/real_cell/ttft.jsonl"))
    joined = join_ttft(turns, ttft)
    # at least one turn got a real latency match
    assert any(j["ttft_s"] is not None for j in joined)
    # a matched turn's total_s is close to its duration
    for j in joined:
        if j["ttft_s"] is not None:
            assert abs(j["total_s"] - j["duration_ms"] / 1000) < 2.0
            break


def test_join_null_when_no_match():
    turns = [{"request_index": 0, "ts_start_epoch": 1000.0, "duration_ms": 10}]
    ttft = [{"t_send_epoch": 5000.0, "ttft_s": 1.0, "prefill_s": 0.5, "total_s": 2.0}]
    j = join_ttft(turns, ttft)
    assert j[0]["ttft_s"] is None
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_parse_ttft.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`analysis/parse/parse_ttft.py`:
```python
from __future__ import annotations

import json
from pathlib import Path


def load_ttft(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def join_ttft(turn_rows: list[dict], ttft_rows: list[dict], tol: float = 0.5) -> list[dict]:
    out = []
    for turn in turn_rows:
        start = turn.get("ts_start_epoch")
        best, best_d = None, tol
        if start is not None:
            for t in ttft_rows:
                d = abs(t["t_send_epoch"] - start)
                if d <= best_d:
                    best, best_d = t, d
        row = dict(turn)
        row["ttft_s"] = best["ttft_s"] if best else None
        row["prefill_s"] = best["prefill_s"] if best else None
        row["total_s"] = best["total_s"] if best else None
        out.append(row)
    return out
```

- [ ] **Step 4: Run to confirm pass + commit**

Run: `.venv/bin/python -m pytest tests/test_parse_ttft.py -v` → PASS (3).
```bash
git add analysis/parse/parse_ttft.py tests/test_parse_ttft.py
git commit -m "feat: ttft load + start-time join to tap turns"
```

---

### Task 4: Parse run_meta + subagent count

**Files:**
- Create: `analysis/parse/parse_meta.py`
- Test: `tests/test_parse_meta.py`

**Interfaces:**
- Produces: `run_summary(meta: dict, run_dir: Path) -> dict` — `task, condition, rep, model, success, correctness, speedup, completion_time_s, num_subagents` (from counting nested `transcripts/**/subagents/*.jsonl` under `run_dir`).

- [ ] **Step 1: Write the failing test**

`tests/test_parse_meta.py`:
```python
import json
from pathlib import Path
from analysis.parse.parse_meta import run_summary


def test_run_summary_fields(tmp_path):
    meta = json.loads(Path("tests/fixtures/real_cell/run_meta.json").read_text())
    s = run_summary(meta, tmp_path)  # tmp_path has no subagents
    assert s["task"] == "coding" and s["condition"] == "single_agent"
    assert "success" in s and "speedup" in s and "correctness" in s
    assert s["num_subagents"] == 0


def test_run_summary_counts_subagents(tmp_path):
    meta = {"task": "coding", "condition": "subagents", "rep": 1, "model": "m",
            "success": False, "score": {"correctness": False, "speedup": 0.0}}
    sub = tmp_path / "transcripts" / "u" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-1.jsonl").write_text("{}")
    (sub / "agent-2.jsonl").write_text("{}")
    s = run_summary(meta, tmp_path)
    assert s["num_subagents"] == 2
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_parse_meta.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`analysis/parse/parse_meta.py`:
```python
from __future__ import annotations

from pathlib import Path


def run_summary(meta: dict, run_dir: Path) -> dict:
    score = meta.get("score") or {}
    subs = list((Path(run_dir) / "transcripts").rglob("subagents/*.jsonl"))
    return {
        "task": meta.get("task"),
        "condition": meta.get("condition"),
        "rep": meta.get("rep"),
        "model": meta.get("model"),
        "success": meta.get("success"),
        "correctness": score.get("correctness"),
        "speedup": score.get("speedup"),
        "completion_time_s": meta.get("completion_time_s"),
        "num_subagents": len(subs),
    }
```

- [ ] **Step 4: Run to confirm pass + commit**

Run: `.venv/bin/python -m pytest tests/test_parse_meta.py -v` → PASS (2).
```bash
git add analysis/parse/parse_meta.py tests/test_parse_meta.py
git commit -m "feat: run_meta summary + subagent counting"
```

---

### Task 5: Build tidy tables

**Files:**
- Create: `analysis/build_tables.py`
- Test: `tests/test_build_tables.py`

**Interfaces:**
- Consumes: `tap_turns`, `tap_components`, `load_ttft`, `join_ttft`, `run_summary`.
- Produces:
  - `build_run(run_dir: Path) -> tuple[list[dict], list[dict], dict]` → (turns, components, run-row) for one run, with `run_id, task, condition, rep` stamped on every row and run-level aggregates (`num_requests, total_input, total_cache_read, total_cache_creation, cache_hit_ratio, peak_prompt_tokens, output_tokens_total`).
  - `build_all(raw_dir: Path, out_dir: Path) -> dict` → writes `turns.parquet`, `components.parquet`, `runs.parquet` into `out_dir`; returns row counts.

- [ ] **Step 1: Write the failing test**

`tests/test_build_tables.py`:
```python
import json, shutil
from pathlib import Path
import pandas as pd
from analysis.build_tables import build_run, build_all


def _make_run(tmp):
    d = tmp / "data/raw/coding__single_agent__01__20260619T210033Z"
    (d / "tap").mkdir(parents=True); (d / "ttft").mkdir(); (d / "transcripts").mkdir()
    shutil.copy("tests/fixtures/real_cell/tap.json", d / "tap/s.json")
    shutil.copy("tests/fixtures/real_cell/ttft.jsonl", d / "ttft/ttft.jsonl")
    shutil.copy("tests/fixtures/real_cell/run_meta.json", d / "run_meta.json")
    return d


def test_build_run(tmp_path):
    d = _make_run(tmp_path)
    turns, comps, run = build_run(d)
    assert turns and all(t["condition"] == "single_agent" for t in turns)
    assert run["num_requests"] == len(turns)
    assert run["total_cache_read"] == sum(t["cache_read"] for t in turns)
    assert 0.0 <= run["cache_hit_ratio"] <= 1.0


def test_build_all_writes_parquet(tmp_path):
    _make_run(tmp_path)
    out = tmp_path / "processed"
    counts = build_all(tmp_path / "data/raw", out)
    assert counts["runs"] == 1 and counts["turns"] > 0
    df = pd.read_parquet(out / "turns.parquet")
    assert {"run_id", "condition", "cache_read", "ttft_s"}.issubset(df.columns)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_build_tables.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`analysis/build_tables.py`:
```python
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from analysis.parse.parse_tap import tap_turns, tap_components
from analysis.parse.parse_ttft import load_ttft, join_ttft
from analysis.parse.parse_meta import run_summary


def build_run(run_dir: Path):
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "run_meta.json").read_text())
    tap_files = sorted((run_dir / "tap").glob("*.json"))
    tap = json.loads(tap_files[0].read_text()) if tap_files else []
    turns = join_ttft(tap_turns(tap), load_ttft(run_dir / "ttft" / "ttft.jsonl"))
    comps = tap_components(tap)
    run_id = run_dir.name
    stamp = {"run_id": run_id, "task": meta.get("task"),
             "condition": meta.get("condition"), "rep": meta.get("rep")}
    for r in turns:
        r.update(stamp)
    for c in comps:
        c.update(stamp)
    summary = run_summary(meta, run_dir)
    summary["run_id"] = run_id
    total_in = sum(t["input_tokens"] for t in turns)
    total_cr = sum(t["cache_read"] for t in turns)
    total_cc = sum(t["cache_creation_5m"] + t["cache_creation_1h"] for t in turns)
    denom = total_in + total_cr + total_cc
    summary.update({
        "num_requests": len(turns),
        "total_input": total_in,
        "total_cache_read": total_cr,
        "total_cache_creation": total_cc,
        "cache_hit_ratio": (total_cr / denom) if denom else 0.0,
        "peak_prompt_tokens": max((t["input_tokens"] + t["cache_read"]
                                   + t["cache_creation_5m"] + t["cache_creation_1h"]
                                   for t in turns), default=0),
        "output_tokens_total": sum(t["output_tokens"] for t in turns),
    })
    return turns, comps, summary


def build_all(raw_dir: Path, out_dir: Path) -> dict:
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_turns, all_comps, all_runs = [], [], []
    for d in sorted(raw_dir.iterdir()):
        if not (d / "run_meta.json").exists():
            continue
        try:
            t, c, r = build_run(d)
        except Exception as exc:
            print(f"skip {d.name}: {exc}")
            continue
        all_turns += t; all_comps += c; all_runs.append(r)
    pd.DataFrame(all_turns).to_parquet(out_dir / "turns.parquet")
    pd.DataFrame(all_comps).to_parquet(out_dir / "components.parquet")
    pd.DataFrame(all_runs).to_parquet(out_dir / "runs.parquet")
    return {"turns": len(all_turns), "components": len(all_comps), "runs": len(all_runs)}
```

- [ ] **Step 4: Run to confirm pass + commit**

Run: `.venv/bin/python -m pytest tests/test_build_tables.py -v` → PASS (2).
```bash
git add analysis/build_tables.py tests/test_build_tables.py
git commit -m "feat: build turns/components/runs parquet from data/raw"
```

---

### Task 6: Metrics — cache accumulation + context growth

**Files:**
- Create: `analysis/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Produces:
  - `cache_accumulation(turns: pd.DataFrame) -> pd.DataFrame` — per `run_id` ordered by `request_index`, adds `cum_cache_read, cum_cache_creation, cum_input, cum_hit_ratio`.
  - `context_growth(components: pd.DataFrame) -> pd.DataFrame` — per `run_id`, cumulative `est_tokens` by component over `request_index`.

- [ ] **Step 1: Write the failing test**

`tests/test_metrics.py`:
```python
import pandas as pd
from analysis.metrics import cache_accumulation, context_growth


def test_cache_accumulation_cumsum_and_ratio():
    df = pd.DataFrame([
        {"run_id": "r", "request_index": 0, "cache_read": 0, "cache_creation_5m": 0,
         "cache_creation_1h": 100, "input_tokens": 10},
        {"run_id": "r", "request_index": 1, "cache_read": 90, "cache_creation_5m": 0,
         "cache_creation_1h": 0, "input_tokens": 10},
    ])
    out = cache_accumulation(df).sort_values("request_index")
    assert list(out["cum_cache_read"]) == [0, 90]
    assert list(out["cum_cache_creation"]) == [100, 100]
    # ratio at row 1 = 90 / (90+100+20)
    assert abs(out.iloc[1]["cum_hit_ratio"] - 90 / 210) < 1e-9


def test_context_growth_cumulative_by_component():
    df = pd.DataFrame([
        {"run_id": "r", "request_index": 0, "component": "tools", "est_tokens": 50},
        {"run_id": "r", "request_index": 1, "component": "tools", "est_tokens": 60},
    ])
    out = context_growth(df)
    row = out[(out.request_index == 1) & (out.component == "tools")].iloc[0]
    assert row["cum_est_tokens"] == 110
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_metrics.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`analysis/metrics.py`:
```python
from __future__ import annotations

import pandas as pd


def cache_accumulation(turns: pd.DataFrame) -> pd.DataFrame:
    df = turns.sort_values(["run_id", "request_index"]).copy()
    df["cache_creation"] = df["cache_creation_5m"] + df["cache_creation_1h"]
    g = df.groupby("run_id")
    df["cum_cache_read"] = g["cache_read"].cumsum()
    df["cum_cache_creation"] = g["cache_creation"].cumsum()
    df["cum_input"] = g["input_tokens"].cumsum()
    denom = df["cum_cache_read"] + df["cum_cache_creation"] + df["cum_input"]
    df["cum_hit_ratio"] = (df["cum_cache_read"] / denom).fillna(0.0)
    return df


def context_growth(components: pd.DataFrame) -> pd.DataFrame:
    df = components.sort_values(["run_id", "component", "request_index"]).copy()
    df["cum_est_tokens"] = df.groupby(["run_id", "component"])["est_tokens"].cumsum()
    return df
```

- [ ] **Step 4: Run to confirm pass + commit**

Run: `.venv/bin/python -m pytest tests/test_metrics.py -v` → PASS (2).
```bash
git add analysis/metrics.py tests/test_metrics.py
git commit -m "feat: cache-accumulation + context-growth metrics"
```

---

### Task 7: Headline figure — prefix-cache-hit accumulation

**Files:**
- Create: `analysis/plots/__init__.py` (empty), `analysis/plots/style.py`, `analysis/plots/cache_accumulation.py`
- Test: `tests/test_plot_cache.py`

**Interfaces:**
- Consumes: `cache_accumulation` (Task 6).
- Produces: `plot_cache_accumulation(turns: pd.DataFrame, out_path: Path) -> Path` — writes a PNG: x=`request_index`, y=`cum_cache_read`, one line per `condition` (mean across runs of a condition), titled per task; returns the path.

- [ ] **Step 1: Write the failing test**

`tests/test_plot_cache.py`:
```python
import pandas as pd
from pathlib import Path
from analysis.plots.cache_accumulation import plot_cache_accumulation


def test_plot_writes_png(tmp_path):
    df = pd.DataFrame([
        {"run_id": "a", "condition": "single_agent", "task": "coding", "request_index": i,
         "cache_read": 100 * i, "cache_creation_5m": 0, "cache_creation_1h": 10,
         "input_tokens": 5} for i in range(4)
    ])
    out = plot_cache_accumulation(df, tmp_path / "cache.png")
    assert out.exists() and out.stat().st_size > 0
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_plot_cache.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`analysis/plots/style.py`:
```python
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # no display
import matplotlib.pyplot as plt  # noqa: E402


def new_fig(title: str, xlabel: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    return fig, ax
```

`analysis/plots/cache_accumulation.py`:
```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.metrics import cache_accumulation
from analysis.plots.style import new_fig, plt


def plot_cache_accumulation(turns: pd.DataFrame, out_path: Path) -> Path:
    acc = cache_accumulation(turns)
    # attach condition/task (constant per run_id)
    meta = turns.groupby("run_id")[["condition", "task"]].first()
    acc = acc.merge(meta, on="run_id", how="left", suffixes=("", "_m"))
    task = acc["task"].dropna().iloc[0] if "task" in acc and acc["task"].notna().any() else ""
    fig, ax = new_fig(f"Prefix-cache-hit accumulation ({task})",
                      "request index", "cumulative cache_read tokens")
    for cond, g in acc.groupby("condition"):
        curve = g.groupby("request_index")["cum_cache_read"].mean()
        ax.plot(curve.index, curve.values, marker="o", label=str(cond))
    ax.legend(title="condition")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)
    return out_path
```

- [ ] **Step 4: Run to confirm pass; render on REAL data; commit**

Run: `.venv/bin/python -m pytest tests/test_plot_cache.py -v` → PASS.
Render the headline figure on the real captured cells:
```bash
.venv/bin/python - <<'PY'
import pandas as pd
from analysis.build_tables import build_all
from analysis.plots.cache_accumulation import plot_cache_accumulation
build_all("data/raw", "data/processed")
df = pd.read_parquet("data/processed/turns.parquet")
print(plot_cache_accumulation(df, "figures/cache_accumulation.png"))
PY
```
Expected: prints `figures/cache_accumulation.png`; the file exists (the headline curve on real data).
```bash
git add analysis/plots/__init__.py analysis/plots/style.py analysis/plots/cache_accumulation.py tests/test_plot_cache.py figures/cache_accumulation.png
git commit -m "feat: prefix-cache-hit accumulation figure (headline) + real render"
```

---

### Task 8: Remaining figures — context growth, latency, success/speedup

**Files:**
- Create: `analysis/plots/context_growth.py`, `analysis/plots/latency.py`, `analysis/plots/success_speedup.py`
- Test: `tests/test_plots_rest.py`

**Interfaces:**
- Consumes: `context_growth` (Task 6), `turns`/`runs` frames.
- Produces:
  - `plot_context_growth(components, out_path) -> Path` — stacked area of cumulative `est_tokens` by component vs `request_index` (one run, or first run per condition).
  - `plot_latency(turns, out_path) -> Path` — scatter/box of `prefill_s`/`ttft_s`/`total_s` (non-null) by condition.
  - `plot_success_speedup(runs, out_path) -> Path` — grouped bars: success rate + mean speedup by condition.

- [ ] **Step 1: Write the failing tests**

`tests/test_plots_rest.py`:
```python
import pandas as pd
from analysis.plots.context_growth import plot_context_growth
from analysis.plots.latency import plot_latency
from analysis.plots.success_speedup import plot_success_speedup


def test_context_growth_png(tmp_path):
    df = pd.DataFrame([
        {"run_id": "a", "request_index": i, "component": c, "est_tokens": 10 * (i + 1)}
        for i in range(3) for c in ("system_prompt", "tools", "messages")
    ])
    out = plot_context_growth(df, tmp_path / "ctx.png")
    assert out.exists() and out.stat().st_size > 0


def test_latency_png(tmp_path):
    df = pd.DataFrame([
        {"condition": "single_agent", "prefill_s": 2.9, "ttft_s": 3.0, "total_s": 128.0},
        {"condition": "single_agent", "prefill_s": 3.7, "ttft_s": 3.7, "total_s": 3.9},
        {"condition": "subagents", "prefill_s": None, "ttft_s": None, "total_s": None},
    ])
    out = plot_latency(df, tmp_path / "lat.png")
    assert out.exists() and out.stat().st_size > 0


def test_success_speedup_png(tmp_path):
    df = pd.DataFrame([
        {"condition": "single_agent", "success": False, "speedup": 0.0},
        {"condition": "subagents", "success": True, "speedup": 1.4},
    ])
    out = plot_success_speedup(df, tmp_path / "ss.png")
    assert out.exists() and out.stat().st_size > 0
```

- [ ] **Step 2: Run to confirm fail**

Run: `.venv/bin/python -m pytest tests/test_plots_rest.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`analysis/plots/context_growth.py`:
```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.metrics import context_growth
from analysis.plots.style import new_fig, plt


def plot_context_growth(components: pd.DataFrame, out_path: Path) -> Path:
    cg = context_growth(components)
    run_id = cg["run_id"].iloc[0]
    g = cg[cg.run_id == run_id]
    pivot = g.pivot_table(index="request_index", columns="component",
                          values="cum_est_tokens", aggfunc="last").fillna(method="ffill").fillna(0)
    fig, ax = new_fig(f"Context growth by component ({run_id[:24]})",
                      "request index", "cumulative est. tokens")
    ax.stackplot(pivot.index, *[pivot[c] for c in pivot.columns], labels=list(pivot.columns))
    ax.legend(loc="upper left")
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)
    return out_path
```

`analysis/plots/latency.py`:
```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.plots.style import new_fig, plt


def plot_latency(turns: pd.DataFrame, out_path: Path) -> Path:
    df = turns.dropna(subset=["ttft_s"]).copy()
    fig, ax = new_fig("Latency: TTFT vs total by condition", "condition", "seconds")
    conds = list(df["condition"].dropna().unique()) or ["(none)"]
    for i, cond in enumerate(conds):
        sub = df[df["condition"] == cond]
        ax.scatter([i - 0.1] * len(sub), sub["ttft_s"], alpha=0.6, label="ttft_s" if i == 0 else None, color="tab:blue")
        ax.scatter([i + 0.1] * len(sub), sub["total_s"], alpha=0.6, label="total_s" if i == 0 else None, color="tab:red")
    ax.set_xticks(range(len(conds))); ax.set_xticklabels(conds, rotation=20)
    ax.set_yscale("symlog"); ax.legend()
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)
    return out_path
```

`analysis/plots/success_speedup.py`:
```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.plots.style import new_fig, plt


def plot_success_speedup(runs: pd.DataFrame, out_path: Path) -> Path:
    g = runs.groupby("condition").agg(
        success_rate=("success", lambda s: float(pd.Series(s).fillna(False).mean())),
        mean_speedup=("speedup", lambda s: float(pd.Series(s).fillna(0).mean())),
    )
    fig, ax = new_fig("Success rate & mean speedup by condition", "condition", "value")
    x = range(len(g)); w = 0.35
    ax.bar([i - w / 2 for i in x], g["success_rate"], w, label="success rate")
    ax.bar([i + w / 2 for i in x], g["mean_speedup"], w, label="mean speedup")
    ax.set_xticks(list(x)); ax.set_xticklabels(list(g.index), rotation=20); ax.legend()
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)
    return out_path
```

- [ ] **Step 4: Run to confirm pass + commit**

Run: `.venv/bin/python -m pytest tests/test_plots_rest.py -v` → PASS (3).
```bash
git add analysis/plots/context_growth.py analysis/plots/latency.py analysis/plots/success_speedup.py tests/test_plots_rest.py
git commit -m "feat: context-growth, latency, success/speedup figures"
```

---

### Task 9: Report generator + Makefile + end-to-end

**Files:**
- Create: `analysis/report.py`
- Modify: `Makefile` (add `analyze` target)
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `build_all` + all four plot functions + `runs.parquet`.
- Produces: `generate(raw_dir, processed_dir, figures_dir, report_path) -> Path` — builds tables, renders all figures, writes `report.md` (a runs summary table + the figures embedded), returns the report path.

- [ ] **Step 1: Write the failing test**

`tests/test_report.py`:
```python
import shutil
from pathlib import Path
from analysis.report import generate


def _make_run(tmp):
    d = tmp / "data/raw/coding__single_agent__01__20260619T210033Z"
    (d / "tap").mkdir(parents=True); (d / "ttft").mkdir(); (d / "transcripts").mkdir()
    shutil.copy("tests/fixtures/real_cell/tap.json", d / "tap/s.json")
    shutil.copy("tests/fixtures/real_cell/ttft.jsonl", d / "ttft/ttft.jsonl")
    shutil.copy("tests/fixtures/real_cell/run_meta.json", d / "run_meta.json")


def test_generate_report(tmp_path):
    _make_run(tmp_path)
    rep = generate(tmp_path / "data/raw", tmp_path / "processed",
                   tmp_path / "figures", tmp_path / "report.md")
    text = Path(rep).read_text()
    assert "Prefix-cache" in text or "cache_accumulation" in text
    assert "| condition |" in text or "condition" in text
    assert (tmp_path / "figures" / "cache_accumulation.png").exists()
```

- [ ] **Step 2: Run to confirm fail**

Run: `.venv/bin/python -m pytest tests/test_report.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`analysis/report.py`:
```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.build_tables import build_all
from analysis.plots.cache_accumulation import plot_cache_accumulation
from analysis.plots.context_growth import plot_context_growth
from analysis.plots.latency import plot_latency
from analysis.plots.success_speedup import plot_success_speedup


def generate(raw_dir, processed_dir, figures_dir, report_path) -> Path:
    raw_dir, processed_dir = Path(raw_dir), Path(processed_dir)
    figures_dir, report_path = Path(figures_dir), Path(report_path)
    figures_dir.mkdir(parents=True, exist_ok=True)
    build_all(raw_dir, processed_dir)
    turns = pd.read_parquet(processed_dir / "turns.parquet")
    comps = pd.read_parquet(processed_dir / "components.parquet")
    runs = pd.read_parquet(processed_dir / "runs.parquet")

    figs = {
        "cache_accumulation.png": plot_cache_accumulation(turns, figures_dir / "cache_accumulation.png"),
        "context_growth.png": plot_context_growth(comps, figures_dir / "context_growth.png"),
        "latency.png": plot_latency(turns, figures_dir / "latency.png"),
        "success_speedup.png": plot_success_speedup(runs, figures_dir / "success_speedup.png"),
    }
    cols = [c for c in ("run_id", "task", "condition", "success", "speedup",
                        "num_requests", "total_cache_read", "cache_hit_ratio",
                        "completion_time_s") if c in runs.columns]
    table_md = runs[cols].to_markdown(index=False)

    lines = ["# Experiment Report\n",
             f"Runs analyzed: **{len(runs)}**.  (Build-only subset; narrative filled after the full sweep.)\n",
             "## Runs\n", table_md, "\n",
             "## Prefix-cache-hit accumulation (headline)\n",
             "![cache](../figures/cache_accumulation.png)\n",
             "## Context growth by component\n", "![ctx](../figures/context_growth.png)\n",
             "## Latency (TTFT vs total)\n", "![lat](../figures/latency.png)\n",
             "## Success rate & speedup\n", "![ss](../figures/success_speedup.png)\n"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    return report_path
```

- [ ] **Step 4: Add the Makefile target**

Append to `Makefile`:
```makefile
analyze:
	$(PY) -c "from analysis.report import generate; print(generate('data/raw','data/processed','figures','reports/report.md'))"
```

- [ ] **Step 5: Run test + real end-to-end + commit**

Run: `.venv/bin/python -m pytest tests/test_report.py -v` → PASS.
Run: `make analyze` → prints `reports/report.md`; `figures/*.png` + `reports/report.md` exist (real 2-cell data).
Run: `make test` → full suite green.
```bash
git add analysis/report.py Makefile tests/test_report.py reports/report.md figures/
git commit -m "feat: report generator + analyze target + real-data report"
```

---

## Self-Review

**Spec coverage:**
- §2 headline cache accumulation → Tasks 6 (metric), 7 (figure). ✓
- §3 real tap list format + usage location + no-request_id + start-time join → Tasks 2, 3 (verified against real fixture). ✓
- §4 tidy tables (turns/components/runs) → Task 5. ✓
- §5 figures 1–5 + cost(table) → Tasks 7, 8, 9. ✓
- §6 module layout → matches Tasks 1–9 file paths. ✓
- §7 build/validate against real_cell + `make analyze` → Tasks 1 (fixture), 7/9 (real renders). ✓
- §3 stale-fixture note → Task 1 copies a REAL cell into `tests/fixtures/real_cell/`; parsers tested only against it. ✓

**Placeholder scan:** every code step has complete code; live/real-render steps are concrete commands with expected output. No "TBD"/"add handling"/"similar to". ✓

**Type consistency:** `tap_turns`/`tap_components` row keys (`request_index, ts_start_epoch, cache_read, cache_creation_5m/1h, est_tokens, component`) are consumed unchanged by `join_ttft` (Task 3), `build_run` (Task 5), `cache_accumulation`/`context_growth` (Task 6), and the plots (7,8). `run_summary` keys (`success, correctness, speedup, num_subagents`) flow into `runs` (Task 5) and `plot_success_speedup` (Task 8). ✓

---

## Notes for execution

- The real-cell fixture (Task 1) is copied from the live `data/raw/coding__single_agent__01__*` cell — it exists now. Run Task 1's copy before the rest.
- `make analyze` runs on whatever is in `data/raw/`: the 2 complete coding cells now; the 2 research cells after the rate limit resets (re-run, then `make analyze` again — no code change).
- `PY` in the Makefile is `.venv/bin/python` (set by Plan A2's Makefile).
