# Experiment Harness & Data Capture — Implementation Plan (Plan A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the harness that runs Claude Code on a (task × orchestration-condition × rep) cell, routes its API traffic through `claude-tap`, and writes all raw tracing data into `data/raw/<run_id>/`.

**Architecture:** A thin Python orchestrator (`harness/`) loads YAML config, computes a `run_id`, restores the task workspace, invokes a per-condition bash launcher that wraps `claude` inside `claude-tap`, then collects the session JSONL transcript(s) and writes `run_meta.json`. A pilot spike runs first to resolve the open questions (headless triggering of each pattern, proxy fidelity, transcript location) and to save real trace samples as fixtures for Plan B.

**Tech Stack:** Python 3.11+ (stdlib + PyYAML), pytest, Bash, `claude-tap` (PyPI), Claude Code CLI (`claude`).

## Global Constraints

- Model fixed for every run: `claude-sonnet-4-6`.
- Conditions (5): `single_agent`, `subagents`, `ralph_loop`, `dynamic_workflow`, `loop_dynamic`.
- Tasks (2): `coding`, `research`.
- Reps: `3` per cell → `5 × 2 × 3 = 30` runs.
- `run_id` format: `<task>__<condition>__<rep:02d>__<UTC-timestamp>`, timestamp `YYYYMMDDTHHMMSSZ`.
- Per-run raw layout: `data/raw/<run_id>/{tap/, transcripts/, otel/, run_meta.json}`.
- `data/raw/` is git-ignored (already in `.gitignore`); everything else is committed.
- All Claude Code traffic is routed through `claude-tap` (reverse proxy) so request bodies are captured.
- `claude-tap` invocation shape (verified): `claude-tap --tap-output-dir DIR --tap-no-live --tap-no-open -- <claude args>`.

---

### Task 1: Scaffold the Python package and test harness

**Files:**
- Create: `pyproject.toml`
- Create: `harness/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `README.md`

**Interfaces:**
- Produces: an installable package `harness` importable as `import harness`; `pytest` runs green.

- [ ] **Step 1: Write the failing smoke test**

`tests/test_smoke.py`:
```python
def test_harness_imports():
    import harness
    assert hasattr(harness, "__version__")
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `pytest tests/test_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'harness'` (package not installed yet).

- [ ] **Step 3: Create the package and project metadata**

`harness/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/__init__.py`: (empty file)

`pyproject.toml`:
```toml
[project]
name = "cc-experiment"
version = "0.1.0"
description = "Context-window & prefix-cache experiments on Claude Code"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["harness*"]
```

`README.md`:
```markdown
# Claude Code context-window & prefix-cache experiments

Harness that runs Claude Code under five orchestration conditions on a coding
and a research task, captures tracing data (claude-tap + session JSONL), and
feeds the analysis pipeline (Plan B).

## Setup
    make setup        # pip install -e ".[dev]"
    make tap-check    # verify claude-tap is on PATH

## Run one cell
    make run TASK=coding CONDITION=single_agent REP=1

## Run everything (30 runs)
    make run-all

See `docs/superpowers/specs/` for the design and `docs/superpowers/plans/` for plans.
```

- [ ] **Step 4: Install and run the test**

Run: `pip install -e ".[dev]" && pytest tests/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml harness/__init__.py tests/__init__.py tests/test_smoke.py README.md
git commit -m "chore: scaffold cc-experiment package and test harness"
```

---

### Task 2: Pilot spike — validate capture and resolve headless triggering

This task is an investigation, not TDD. Its deliverables are (a) a filled-in
`pilot-notes.md` with an exact command per condition and confirmed data
locations, and (b) real trace samples saved as fixtures for Plan B. **Every other
task in this plan and in Plan B depends on the facts recorded here.** Do not
guess — run the commands and record what actually happens.

**Files:**
- Create: `docs/superpowers/pilot-notes.md`
- Create: `tests/fixtures/sample_plain/` (one real run's `tap/` + `transcripts/`)
- Create: `tests/fixtures/sample_subagents/` (one real run that spawned a subagent)

- [ ] **Step 1: Install claude-tap and confirm it runs**

Run: `uv tool install claude-tap || pip install claude-tap`
Run: `claude-tap --help`
Record in `pilot-notes.md` under `## Tap version`: output of `claude-tap --version` and the exact help text for the `--tap-output-dir`, `--tap-no-live`, `--tap-no-open`, `--tap-port` flags.

- [ ] **Step 2: Capture a trivial run and record the trace format**

Run:
```bash
mkdir -p /tmp/pilot/tap
claude-tap --tap-output-dir /tmp/pilot/tap --tap-no-live --tap-no-open -- \
  --model claude-sonnet-4-6 -p "Say hello in one word."
```
Record under `## Tap output`: the directory tree of `/tmp/pilot/tap`, the trace
filename pattern, and — for one captured request — the JSON keys present in the
**request** body (`system`, `tools`, `messages`, `model`, …) and the **response**
body (`usage` with `input_tokens`, `output_tokens`, `cache_creation_input_tokens`,
`cache_read_input_tokens`, and any `cache_creation` sub-split). Paste one redacted
request+response pair.

- [ ] **Step 3: Locate the session JSONL transcript**

Find the transcript Claude Code wrote for that run:
```bash
ls -dt ~/.claude/projects/*/ | head
ls -t ~/.claude/projects/*/*.jsonl | head
```
Record under `## Transcript location`: the exact encoded project directory name
for the cwd used, and confirm the encoding rule (cwd with `/` replaced by `-`;
note whether `.` or `_` are also replaced). Paste one assistant message's
`message.usage` object from the JSONL.

- [ ] **Step 4: Proxy-fidelity cross-check**

Compare, for the same request, the `usage` numbers from the claude-tap trace
(Step 2) and the session JSONL (Step 3). Record under `## Proxy fidelity` whether
they match (token counts and cache read/write). If they differ, note the
deltas — this decides whether the proxy perturbs caching.

- [ ] **Step 5: Determine the headless trigger for each condition**

For each condition, find the exact invocation that reliably produces the pattern
under `claude -p`, and record it in a table under `## Condition commands`. Verify
each by inspecting the resulting transcript:

- `single_agent`: `claude -p "<prompt>"` with no delegation. Confirm: no
  `isSidechain` entries in the JSONL.
- `subagents`: a prompt that forces Task-tool delegation (e.g. "Use subagents to
  do X and Y in parallel"). Confirm: JSONL contains entries with
  `"isSidechain": true`. Save this run as the `sample_subagents` fixture.
- `ralph_loop`: an external loop — confirm a fresh session each iteration:
  ```bash
  for i in 1 2 3; do
    claude -p "Continue the task. Read PROGRESS.md, do one step, update PROGRESS.md."
  done
  ```
  Confirm: each iteration creates a **new** session JSONL (reset context).
- `loop_dynamic`: determine how to drive Claude Code's `/loop` self-paced mode
  non-interactively. Try `claude -p "/loop <prompt>"`; if that does not self-pace
  headlessly, record the fallback that preserves context across turns — e.g.
  `claude --continue -p "..."` / `claude --resume <session-id> -p "..."` in a loop.
  Record which works and the exact command. Confirm: iterations **reuse the same
  session** (retained context), contrasting with `ralph_loop`.
- `dynamic_workflow`: determine how to trigger the Workflow orchestration
  non-interactively (it requires explicit opt-in such as "use a workflow" /
  "ultracode"). Record the exact prompt/flags and whether it spawns multiple
  subagents. If pure `-p` cannot drive it, record the scripted fallback.

- [ ] **Step 6: Save fixtures and write the go/no-go**

Copy one plain run's `tap/` + `transcripts/` into `tests/fixtures/sample_plain/`
and the subagents run into `tests/fixtures/sample_subagents/` (redact auth headers
if claude-tap hasn't already). Record under `## Decision` a go/no-go for each
condition and the final command table. Note any condition that needs an
interactive/scripted harness instead of plain `-p`.

- [ ] **Step 7: Commit**

```bash
git add docs/superpowers/pilot-notes.md tests/fixtures/
git commit -m "docs: pilot spike — capture format, transcript location, per-condition commands"
```

---

### Task 3: Config schema, config files, and task workloads

**Files:**
- Create: `harness/config.py`
- Create: `config/experiment.yaml`
- Create: `config/conditions/{single_agent,subagents,ralph_loop,dynamic_workflow,loop_dynamic}.yaml`
- Create: `config/tasks/{coding,research}.yaml`
- Create: `tasks/coding/prompt.md`, `tasks/coding/workspace_seed/` (seed files), `tasks/research/prompt.md`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `ExperimentConfig(model: str, reps: int, conditions: list[str], tasks: list[str], data_raw: Path, claude_projects: Path, proxy_host: str, proxy_port: int)`
  - `TaskConfig(name: str, prompt_file: Path, workspace: Path | None, workspace_seed: Path | None)`
  - `ConditionConfig(name: str, launcher: Path, description: str)`
  - `load_experiment(path: Path) -> ExperimentConfig`
  - `load_task(path: Path) -> TaskConfig`
  - `load_condition(path: Path) -> ConditionConfig`

- [ ] **Step 1: Write the config files**

`config/experiment.yaml`:
```yaml
model: claude-sonnet-4-6
reps: 3
conditions: [single_agent, subagents, ralph_loop, dynamic_workflow, loop_dynamic]
tasks: [coding, research]
paths:
  data_raw: data/raw
  claude_projects: ~/.claude/projects
proxy:
  host: 127.0.0.1
  port: 8080
```

`config/conditions/single_agent.yaml`:
```yaml
name: single_agent
launcher: harness/conditions/single_agent.sh
description: One continuous session, no delegation (baseline).
```
`config/conditions/subagents.yaml`:
```yaml
name: subagents
launcher: harness/conditions/subagents.sh
description: Delegates work via the Task tool; isolated subagent contexts.
```
`config/conditions/ralph_loop.yaml`:
```yaml
name: ralph_loop
launcher: harness/conditions/ralph_loop.sh
description: External while-loop, fresh context each iteration (Ralph technique).
```
`config/conditions/dynamic_workflow.yaml`:
```yaml
name: dynamic_workflow
launcher: harness/conditions/dynamic_workflow.sh
description: Workflow-style orchestration; many short-lived subagents.
```
`config/conditions/loop_dynamic.yaml`:
```yaml
name: loop_dynamic
launcher: harness/conditions/loop_dynamic.sh
description: /loop self-paced; single session, retained context across turns.
```

`config/tasks/coding.yaml`:
```yaml
name: coding
prompt_file: tasks/coding/prompt.md
workspace: tasks/coding/workspace
workspace_seed: tasks/coding/workspace_seed
```
`config/tasks/research.yaml`:
```yaml
name: research
prompt_file: tasks/research/prompt.md
workspace: null
workspace_seed: null
```

- [ ] **Step 2: Write the task workloads**

`tasks/coding/prompt.md`:
```markdown
You are working in the current directory, a small Python project with a failing
test. Implement a `Stack` class in `stack.py` with methods `push(x)`, `pop()`,
`peek()`, and `is_empty()`. `pop`/`peek` on an empty stack must raise
`IndexError`. Make the tests in `test_stack.py` pass. Run `pytest -q` and confirm
all tests pass before finishing.
```

`tasks/coding/workspace_seed/test_stack.py`:
```python
import pytest
from stack import Stack

def test_push_pop():
    s = Stack()
    s.push(1); s.push(2)
    assert s.pop() == 2
    assert s.pop() == 1

def test_peek_and_is_empty():
    s = Stack()
    assert s.is_empty()
    s.push(42)
    assert not s.is_empty()
    assert s.peek() == 42

def test_pop_empty_raises():
    with pytest.raises(IndexError):
        Stack().pop()
```

`tasks/coding/workspace_seed/stack.py`:
```python
# TODO: implement Stack (the agent fills this in)
```

`tasks/research/prompt.md`:
```markdown
Research how prefix / prompt caching works across the Claude (Anthropic), OpenAI,
and Google Gemini APIs. Cover: how a cache hit is triggered, the cache lifetime
(TTL), what invalidates the cached prefix, and how each provider reports cache
usage in API responses. Write a one-page summary to `research_summary.md` with a
comparison table and at least 4 cited sources (include URLs).
```

- [ ] **Step 3: Write the failing config test**

`tests/test_config.py`:
```python
from pathlib import Path
from harness.config import load_experiment, load_task, load_condition

def test_load_experiment():
    exp = load_experiment(Path("config/experiment.yaml"))
    assert exp.model == "claude-sonnet-4-6"
    assert exp.reps == 3
    assert exp.conditions == [
        "single_agent", "subagents", "ralph_loop", "dynamic_workflow", "loop_dynamic"
    ]
    assert exp.tasks == ["coding", "research"]
    assert exp.proxy_port == 8080

def test_load_task_with_and_without_workspace():
    coding = load_task(Path("config/tasks/coding.yaml"))
    assert coding.name == "coding"
    assert coding.workspace == Path("tasks/coding/workspace")
    research = load_task(Path("config/tasks/research.yaml"))
    assert research.workspace is None

def test_load_condition():
    c = load_condition(Path("config/conditions/subagents.yaml"))
    assert c.name == "subagents"
    assert c.launcher == Path("harness/conditions/subagents.sh")
```

- [ ] **Step 4: Run it to confirm it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'harness.config'`.

- [ ] **Step 5: Implement the loader**

`harness/config.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ExperimentConfig:
    model: str
    reps: int
    conditions: list[str]
    tasks: list[str]
    data_raw: Path
    claude_projects: Path
    proxy_host: str
    proxy_port: int


def load_experiment(path: Path) -> ExperimentConfig:
    data = yaml.safe_load(Path(path).read_text())
    paths = data.get("paths", {})
    proxy = data.get("proxy", {})
    return ExperimentConfig(
        model=data["model"],
        reps=int(data["reps"]),
        conditions=list(data["conditions"]),
        tasks=list(data["tasks"]),
        data_raw=Path(paths.get("data_raw", "data/raw")),
        claude_projects=Path(paths.get("claude_projects", "~/.claude/projects")).expanduser(),
        proxy_host=proxy.get("host", "127.0.0.1"),
        proxy_port=int(proxy.get("port", 8080)),
    )


@dataclass(frozen=True)
class TaskConfig:
    name: str
    prompt_file: Path
    workspace: Path | None
    workspace_seed: Path | None


def load_task(path: Path) -> TaskConfig:
    data = yaml.safe_load(Path(path).read_text())
    ws = data.get("workspace")
    seed = data.get("workspace_seed")
    return TaskConfig(
        name=data["name"],
        prompt_file=Path(data["prompt_file"]),
        workspace=Path(ws) if ws else None,
        workspace_seed=Path(seed) if seed else None,
    )


@dataclass(frozen=True)
class ConditionConfig:
    name: str
    launcher: Path
    description: str


def load_condition(path: Path) -> ConditionConfig:
    data = yaml.safe_load(Path(path).read_text())
    return ConditionConfig(
        name=data["name"],
        launcher=Path(data["launcher"]),
        description=data.get("description", ""),
    )
```

- [ ] **Step 6: Run the test to confirm it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add harness/config.py config/ tasks/ tests/test_config.py
git commit -m "feat: config schema, experiment/condition/task configs, task workloads"
```

---

### Task 4: Run identity and metadata (`run_meta.py`)

**Files:**
- Create: `harness/run_meta.py`
- Test: `tests/test_run_meta.py`

**Interfaces:**
- Produces:
  - `make_run_id(task: str, condition: str, rep: int, ts: datetime) -> str`
  - `write_run_meta(run_dir: Path, meta: dict) -> Path`
  - `gather_versions() -> dict` (best-effort tool versions via subprocess)

- [ ] **Step 1: Write the failing test**

`tests/test_run_meta.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path

from harness.run_meta import make_run_id, write_run_meta


def test_make_run_id_pads_rep_and_uses_utc():
    ts = datetime(2026, 6, 18, 21, 0, 0, tzinfo=timezone.utc)
    assert make_run_id("coding", "subagents", 1, ts) == \
        "coding__subagents__01__20260618T210000Z"


def test_write_run_meta_roundtrips(tmp_path: Path):
    meta = {"task": "coding", "condition": "single_agent", "rep": 2}
    out = write_run_meta(tmp_path / "run", meta)
    assert out.name == "run_meta.json"
    assert json.loads(out.read_text())["condition"] == "single_agent"
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `pytest tests/test_run_meta.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'harness.run_meta'`.

- [ ] **Step 3: Implement**

`harness/run_meta.py`:
```python
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def make_run_id(task: str, condition: str, rep: int, ts: datetime) -> str:
    stamp = ts.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{task}__{condition}__{rep:02d}__{stamp}"


def write_run_meta(run_dir: Path, meta: dict) -> Path:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run_meta.json"
    path.write_text(json.dumps(meta, indent=2, sort_keys=True))
    return path


def _cmd(args: list[str]) -> str:
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except Exception as exc:  # tool missing / non-zero — record, don't crash
        return f"<error: {exc}>"


def gather_versions() -> dict:
    return {
        "claude": _cmd(["claude", "--version"]),
        "claude_tap": _cmd(["claude-tap", "--version"]),
        "git_sha": _cmd(["git", "rev-parse", "HEAD"]),
    }
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `pytest tests/test_run_meta.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add harness/run_meta.py tests/test_run_meta.py
git commit -m "feat: run_id scheme and run_meta writer"
```

---

### Task 5: Transcript collection (`collect_transcripts.py`)

**Files:**
- Create: `harness/capture/__init__.py`
- Create: `harness/capture/collect_transcripts.py`
- Test: `tests/test_collect_transcripts.py`

**Interfaces:**
- Produces:
  - `encode_project_dir(cwd: str) -> str`
  - `find_new_sessions(projects_dir: Path, project_cwd: str, since: float) -> list[Path]`
  - `collect(run_dir: Path, projects_dir: Path, project_cwd: str, since: float) -> list[Path]`

**Note:** `find_new_sessions` prefers the encoded project directory but falls back
to scanning all project directories by mtime, so it works even if the cwd changes
per run or the encoding has quirks (confirm the rule against Task 2 §Transcript
location).

- [ ] **Step 1: Write the failing test**

`tests/test_collect_transcripts.py`:
```python
from pathlib import Path

from harness.capture.collect_transcripts import (
    encode_project_dir, find_new_sessions, collect,
)


def test_encode_project_dir_replaces_slashes():
    assert encode_project_dir("/home/u/experiments/projects") == \
        "-home-u-experiments-projects"


def _touch(path: Path, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n")
    import os
    os.utime(path, (mtime, mtime))


def test_find_new_sessions_returns_only_recent(tmp_path: Path):
    projects = tmp_path / "projects"
    enc = encode_project_dir("/work/proj")
    old = projects / enc / "old.jsonl"
    new = projects / enc / "new.jsonl"
    _touch(old, 100.0)
    _touch(new, 200.0)
    found = find_new_sessions(projects, "/work/proj", since=150.0)
    assert [p.name for p in found] == ["new.jsonl"]


def test_collect_copies_into_run_dir(tmp_path: Path):
    projects = tmp_path / "projects"
    enc = encode_project_dir("/work/proj")
    _touch(projects / enc / "s.jsonl", 200.0)
    run_dir = tmp_path / "run"
    copied = collect(run_dir, projects, "/work/proj", since=150.0)
    assert (run_dir / "transcripts" / "s.jsonl").exists()
    assert len(copied) == 1
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `pytest tests/test_collect_transcripts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'harness.capture'`.

- [ ] **Step 3: Implement**

`harness/capture/__init__.py`: (empty file)

`harness/capture/collect_transcripts.py`:
```python
from __future__ import annotations

import shutil
from pathlib import Path


def encode_project_dir(cwd: str) -> str:
    """Claude Code stores transcripts under ~/.claude/projects/<encoded>, where
    <encoded> is the absolute cwd with each '/' replaced by '-'. (Confirm against
    pilot-notes.md whether '.' / '_' are also replaced; extend here if so.)"""
    return cwd.replace("/", "-")


def find_new_sessions(projects_dir: Path, project_cwd: str, since: float) -> list[Path]:
    root = Path(projects_dir).expanduser()
    if not root.is_dir():
        return []
    encoded = root / encode_project_dir(project_cwd)
    search_dirs = [encoded] if encoded.is_dir() else [d for d in root.iterdir() if d.is_dir()]
    found: list[Path] = []
    for d in search_dirs:
        found.extend(p for p in d.glob("*.jsonl") if p.stat().st_mtime >= since)
    return sorted(found)


def collect(run_dir: Path, projects_dir: Path, project_cwd: str, since: float) -> list[Path]:
    dest = Path(run_dir) / "transcripts"
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in find_new_sessions(projects_dir, project_cwd, since):
        out = dest / src.name
        shutil.copy2(src, out)
        copied.append(out)
    return copied
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `pytest tests/test_collect_transcripts.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add harness/capture/__init__.py harness/capture/collect_transcripts.py tests/test_collect_transcripts.py
git commit -m "feat: collect session JSONL transcripts produced during a run"
```

---

### Task 6: Capture and condition launcher scripts

These bash scripts wrap `claude` in `claude-tap`. **Fill the pattern-specific
`claude` invocation from Task 2 §Condition commands** — the claude-tap wrapper is
fixed and verified, only the trailing `claude` args differ per condition.

**Files:**
- Create: `harness/capture/run_tap.sh` (shared wrapper)
- Create: `harness/conditions/single_agent.sh`
- Create: `harness/conditions/subagents.sh`
- Create: `harness/conditions/ralph_loop.sh`
- Create: `harness/conditions/loop_dynamic.sh`
- Create: `harness/conditions/dynamic_workflow.sh`

**Interfaces:**
- Each launcher is called as:
  `<launcher>.sh <prompt_file> <run_dir> <model>`
  and must write claude-tap traces into `<run_dir>/tap/`.

- [ ] **Step 1: Write the shared tap wrapper**

`harness/capture/run_tap.sh`:
```bash
#!/usr/bin/env bash
# Wrap a claude invocation in claude-tap. Traces land in $TAP_DIR.
# Usage: run_tap.sh <tap_dir> -- <claude args...>
set -euo pipefail
TAP_DIR="$1"; shift
[ "$1" = "--" ] && shift
mkdir -p "$TAP_DIR"
exec claude-tap --tap-output-dir "$TAP_DIR" --tap-no-live --tap-no-open -- "$@"
```

- [ ] **Step 2: Write the single_agent launcher**

`harness/conditions/single_agent.sh`:
```bash
#!/usr/bin/env bash
# Usage: single_agent.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
"$HERE/../capture/run_tap.sh" "$RUN_DIR/tap" -- \
  --model "$MODEL" -p "$(cat "$PROMPT_FILE")"
```

- [ ] **Step 3: Write the subagents launcher**

`harness/conditions/subagents.sh` — identical wrapper; the prompt file already
instructs delegation, and per Task 2 the verified flag set induces subagents.
Append any flag Task 2 found necessary (e.g. raising the allowed tool set):
```bash
#!/usr/bin/env bash
# Usage: subagents.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
PROMPT="Use subagents (the Task tool) to parallelize. $(cat "$PROMPT_FILE")"
"$HERE/../capture/run_tap.sh" "$RUN_DIR/tap" -- \
  --model "$MODEL" -p "$PROMPT"
```

- [ ] **Step 4: Write the ralph_loop launcher**

`harness/conditions/ralph_loop.sh` — external loop, fresh context each iteration.
Set `RALPH_ITERS` (default from Task 2):
```bash
#!/usr/bin/env bash
# Usage: ralph_loop.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${RALPH_ITERS:-5}"
PROMPT="$(cat "$PROMPT_FILE")
Work incrementally: read PROGRESS.md if present, do one step, update PROGRESS.md."
for i in $(seq 1 "$ITERS"); do
  "$HERE/../capture/run_tap.sh" "$RUN_DIR/tap" -- \
    --model "$MODEL" -p "$PROMPT"
done
```

- [ ] **Step 5: Write the loop_dynamic and dynamic_workflow launchers**

`harness/conditions/loop_dynamic.sh` — single session, retained context. Use the
exact mechanism Task 2 confirmed works headlessly (shown here with the
`--continue` fallback; replace with the `/loop` form if Task 2 found it drives
self-pacing under `-p`):
```bash
#!/usr/bin/env bash
# Usage: loop_dynamic.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${LOOP_ITERS:-5}"
# Iteration 1 starts the session; later iterations --continue the SAME session
# so context is retained (contrast with ralph_loop).
"$HERE/../capture/run_tap.sh" "$RUN_DIR/tap" -- \
  --model "$MODEL" -p "$(cat "$PROMPT_FILE")"
for i in $(seq 2 "$ITERS"); do
  "$HERE/../capture/run_tap.sh" "$RUN_DIR/tap" -- \
    --model "$MODEL" --continue -p "Continue. Do the next step toward the goal."
done
```

`harness/conditions/dynamic_workflow.sh` — drive the Workflow orchestration with
the exact opt-in prompt/flags Task 2 confirmed:
```bash
#!/usr/bin/env bash
# Usage: dynamic_workflow.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
# "ultracode" / "use a workflow" is the opt-in that induces workflow orchestration
# (confirm exact wording/flags in pilot-notes.md §Condition commands).
PROMPT="ultracode: use a workflow to orchestrate this. $(cat "$PROMPT_FILE")"
"$HERE/../capture/run_tap.sh" "$RUN_DIR/tap" -- \
  --model "$MODEL" -p "$PROMPT"
```

- [ ] **Step 6: Make scripts executable and smoke-test one launcher**

Run:
```bash
chmod +x harness/capture/run_tap.sh harness/conditions/*.sh
mkdir -p /tmp/smoke
echo "Say hello in one word." > /tmp/smoke/prompt.md
harness/conditions/single_agent.sh /tmp/smoke/prompt.md /tmp/smoke/run claude-sonnet-4-6
```
Expected: command completes; `/tmp/smoke/run/tap/` contains at least one trace
JSONL. (Uses real API — one trivial call.)

- [ ] **Step 7: Commit**

```bash
git add harness/capture/run_tap.sh harness/conditions/
git commit -m "feat: claude-tap wrapper and per-condition launchers"
```

---

### Task 7: Runner — orchestrate one cell (`runner.py`)

**Files:**
- Create: `harness/workspace.py`
- Create: `harness/runner.py`
- Test: `tests/test_runner_plan.py`
- Test: `tests/test_workspace.py`

**Interfaces:**
- Consumes: `ExperimentConfig`, `TaskConfig`, `ConditionConfig` (Task 3);
  `make_run_id`, `write_run_meta`, `gather_versions` (Task 4); `collect` (Task 5).
- Produces:
  - `restore_workspace(seed: Path, live: Path) -> None`
  - `RunPlan(run_id: str, run_dir: Path, task: TaskConfig, condition: ConditionConfig, rep: int, model: str)`
  - `plan_run(exp, task, condition, rep, ts) -> RunPlan`
  - `execute(plan, exp, *, dry_run: bool=False) -> Path` (returns run_dir)
  - CLI: `python -m harness.runner --task T --condition C --rep N [--dry-run]`

- [ ] **Step 1: Write the failing workspace test**

`tests/test_workspace.py`:
```python
from pathlib import Path
from harness.workspace import restore_workspace

def test_restore_workspace_replaces_live_with_seed(tmp_path: Path):
    seed = tmp_path / "seed"; seed.mkdir()
    (seed / "stack.py").write_text("# TODO")
    live = tmp_path / "live"; live.mkdir()
    (live / "stack.py").write_text("done by a previous run")
    (live / "junk.txt").write_text("stale")
    restore_workspace(seed, live)
    assert (live / "stack.py").read_text() == "# TODO"
    assert not (live / "junk.txt").exists()
```

- [ ] **Step 2: Write the failing plan test**

`tests/test_runner_plan.py`:
```python
from datetime import datetime, timezone
from pathlib import Path

from harness.config import (
    ExperimentConfig, TaskConfig, ConditionConfig,
)
from harness.runner import plan_run


def _exp(tmp):
    return ExperimentConfig(
        model="claude-sonnet-4-6", reps=3,
        conditions=["single_agent"], tasks=["coding"],
        data_raw=Path(tmp) / "data/raw",
        claude_projects=Path(tmp) / "projects",
        proxy_host="127.0.0.1", proxy_port=8080,
    )


def test_plan_run_builds_run_id_and_dir(tmp_path):
    exp = _exp(tmp_path)
    task = TaskConfig("coding", Path("tasks/coding/prompt.md"), None, None)
    cond = ConditionConfig("single_agent", Path("harness/conditions/single_agent.sh"), "")
    ts = datetime(2026, 6, 18, 21, 0, 0, tzinfo=timezone.utc)
    plan = plan_run(exp, task, cond, rep=1, ts=ts)
    assert plan.run_id == "coding__single_agent__01__20260618T210000Z"
    assert plan.run_dir == exp.data_raw / plan.run_id
    assert plan.model == "claude-sonnet-4-6"
```

- [ ] **Step 3: Run both to confirm they fail**

Run: `pytest tests/test_workspace.py tests/test_runner_plan.py -v`
Expected: FAIL with `ModuleNotFoundError` for `harness.workspace` / `harness.runner`.

- [ ] **Step 4: Implement workspace restore**

`harness/workspace.py`:
```python
from __future__ import annotations

import shutil
from pathlib import Path


def restore_workspace(seed: Path, live: Path) -> None:
    """Reset the live working dir to a pristine copy of the seed."""
    live = Path(live)
    if live.exists():
        shutil.rmtree(live)
    shutil.copytree(Path(seed), live)
```

- [ ] **Step 5: Implement the runner**

`harness/runner.py`:
```python
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from harness.config import (
    ExperimentConfig, TaskConfig, ConditionConfig,
    load_experiment, load_task, load_condition,
)
from harness.run_meta import make_run_id, write_run_meta, gather_versions
from harness.capture.collect_transcripts import collect
from harness.workspace import restore_workspace


@dataclass(frozen=True)
class RunPlan:
    run_id: str
    run_dir: Path
    task: TaskConfig
    condition: ConditionConfig
    rep: int
    model: str


def plan_run(exp: ExperimentConfig, task: TaskConfig, condition: ConditionConfig,
             rep: int, ts: datetime) -> RunPlan:
    run_id = make_run_id(task.name, condition.name, rep, ts)
    return RunPlan(run_id, exp.data_raw / run_id, task, condition, rep, exp.model)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def execute(plan: RunPlan, exp: ExperimentConfig, *, dry_run: bool = False) -> Path:
    run_dir = plan.run_dir
    prompt_file = plan.task.prompt_file
    cwd = Path.cwd()

    if plan.task.workspace and plan.task.workspace_seed:
        restore_workspace(plan.task.workspace_seed, plan.task.workspace)
        cwd = plan.task.workspace

    if dry_run:
        print(f"[dry-run] run_id={plan.run_id}")
        print(f"[dry-run] run_dir={run_dir}")
        print(f"[dry-run] launcher={plan.condition.launcher} "
              f"prompt={prompt_file} model={plan.model} cwd={cwd}")
        return run_dir

    (run_dir / "tap").mkdir(parents=True, exist_ok=True)
    (run_dir / "transcripts").mkdir(parents=True, exist_ok=True)
    start = _now().timestamp()

    launcher = Path(plan.condition.launcher).resolve()
    subprocess.run(
        [str(launcher), str(Path(prompt_file).resolve()), str(run_dir.resolve()), plan.model],
        cwd=str(cwd), check=True,
    )

    transcripts = collect(run_dir, exp.claude_projects, str(Path(cwd).resolve()), since=start)
    write_run_meta(run_dir, {
        "run_id": plan.run_id,
        "task": plan.task.name,
        "condition": plan.condition.name,
        "rep": plan.rep,
        "model": plan.model,
        "started_utc": datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
        "transcripts": [p.name for p in transcripts],
        "versions": gather_versions(),
    })
    return run_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--config", default="config/experiment.yaml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    exp = load_experiment(Path(args.config))
    task = load_task(Path(f"config/tasks/{args.task}.yaml"))
    cond = load_condition(Path(f"config/conditions/{args.condition}.yaml"))
    plan = plan_run(exp, task, cond, args.rep, _now())
    execute(plan, exp, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the tests to confirm they pass**

Run: `pytest tests/test_workspace.py tests/test_runner_plan.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Dry-run the CLI (no API)**

Run: `python -m harness.runner --task coding --condition single_agent --rep 1 --dry-run`
Expected: prints `run_id=coding__single_agent__01__...`, the run_dir, and the launcher line. No network call.

- [ ] **Step 8: Commit**

```bash
git add harness/workspace.py harness/runner.py tests/test_workspace.py tests/test_runner_plan.py
git commit -m "feat: runner orchestrates one cell (plan + execute + dry-run)"
```

---

### Task 8: Run-all sweep and Makefile

**Files:**
- Modify: `harness/runner.py` (add `--all` sweep)
- Create: `Makefile`
- Test: `tests/test_runner_sweep.py`

**Interfaces:**
- Consumes: `ExperimentConfig` (`conditions`, `tasks`, `reps`).
- Produces:
  - `iter_cells(exp) -> list[tuple[str, str, int]]` yielding `(task, condition, rep)` for all cells, `rep` in `1..reps`.
  - CLI flag `--all` running every cell sequentially.

- [ ] **Step 1: Write the failing sweep test**

`tests/test_runner_sweep.py`:
```python
from pathlib import Path
from harness.config import ExperimentConfig
from harness.runner import iter_cells


def test_iter_cells_full_factorial():
    exp = ExperimentConfig(
        model="claude-sonnet-4-6", reps=3,
        conditions=["single_agent", "subagents", "ralph_loop",
                    "dynamic_workflow", "loop_dynamic"],
        tasks=["coding", "research"],
        data_raw=Path("data/raw"), claude_projects=Path("~/.claude/projects"),
        proxy_host="127.0.0.1", proxy_port=8080,
    )
    cells = iter_cells(exp)
    assert len(cells) == 30
    assert ("coding", "single_agent", 1) in cells
    assert ("research", "loop_dynamic", 3) in cells
    # reps are 1-indexed
    assert min(r for _, _, r in cells) == 1
    assert max(r for _, _, r in cells) == 3
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `pytest tests/test_runner_sweep.py -v`
Expected: FAIL with `ImportError: cannot import name 'iter_cells'`.

- [ ] **Step 3: Implement `iter_cells` and wire `--all`**

Add to `harness/runner.py`:
```python
def iter_cells(exp: ExperimentConfig) -> list[tuple[str, str, int]]:
    cells: list[tuple[str, str, int]] = []
    for task in exp.tasks:
        for condition in exp.conditions:
            for rep in range(1, exp.reps + 1):
                cells.append((task, condition, rep))
    return cells
```

In `main`, replace the body after building `exp` with:
```python
    if args.all:
        for task_name, cond_name, rep in iter_cells(exp):
            task = load_task(Path(f"config/tasks/{task_name}.yaml"))
            cond = load_condition(Path(f"config/conditions/{cond_name}.yaml"))
            plan = plan_run(exp, task, cond, rep, _now())
            print(f"=== {plan.run_id} ===")
            execute(plan, exp, dry_run=args.dry_run)
        return 0

    task = load_task(Path(f"config/tasks/{args.task}.yaml"))
    cond = load_condition(Path(f"config/conditions/{args.condition}.yaml"))
    plan = plan_run(exp, task, cond, args.rep, _now())
    execute(plan, exp, dry_run=args.dry_run)
    return 0
```
And add the flags / relax requirements in the parser:
```python
    ap.add_argument("--task")
    ap.add_argument("--condition")
    ap.add_argument("--rep", type=int)
    ap.add_argument("--all", action="store_true")
```
(remove `required=True` from `--task/--condition/--rep`; when not `--all`, argparse
values are used as before — a missing one with `--all` unset will raise a clear
`TypeError` in `make_run_id`, which is acceptable for an internal tool.)

- [ ] **Step 4: Run the test to confirm it passes**

Run: `pytest tests/test_runner_sweep.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Write the Makefile**

`Makefile`:
```makefile
.PHONY: setup tap-check run run-all dry-all clean test
PY ?= python

setup:
	pip install -e ".[dev]"

tap-check:
	claude-tap --help >/dev/null && echo "claude-tap OK"

test:
	pytest -q

# Single cell: make run TASK=coding CONDITION=single_agent REP=1
run:
	$(PY) -m harness.runner --task $(TASK) --condition $(CONDITION) --rep $(REP)

run-all:
	$(PY) -m harness.runner --all

dry-all:
	$(PY) -m harness.runner --all --dry-run

clean:
	rm -rf data/raw/*
```

- [ ] **Step 6: Verify the full suite and a dry sweep**

Run: `make test`
Expected: all tests PASS.
Run: `make dry-all`
Expected: prints 30 `=== <run_id> ===` blocks, no network calls.

- [ ] **Step 7: Commit**

```bash
git add harness/runner.py Makefile tests/test_runner_sweep.py
git commit -m "feat: full-factorial run-all sweep and Makefile targets"
```

---

## Self-Review

**Spec coverage (Plan A scope = capture layer of the spec):**
- §2 design / 5 conditions / 30 runs → Tasks 3 (configs), 6 (launchers), 8 (`iter_cells` asserts 30). ✓
- §2 fixed model `claude-sonnet-4-6` → Global Constraints + config + every launcher passes `--model`. ✓
- §3 claude-tap capture + session JSONL → Tasks 2 (validate), 6 (wrapper), 5 (transcripts). ✓
- §3 `run_meta.json` fields → Task 4 + Task 7 `execute`. ✓
- §3 proxy fidelity check → Task 2 Step 4. ✓
- §7 `run_id` scheme + Makefile targets → Tasks 4, 8. ✓
- §9 open questions (headless triggering, encoding, proxy fidelity) → Task 2 resolves all; launchers reference its findings. ✓
- OTEL is optional/out-of-scope for Plan A (spec §3 marks it optional) — `otel/` dir is created but not populated here; note for a later task if enabled.

**Placeholder scan:** Launcher pattern-triggers in Task 6 intentionally defer the
*exact* per-condition `claude` args to Task 2's recorded findings — this is a
real dependency, not a placeholder; the claude-tap wrapper and script structure
are fully concrete. No "TBD"/"add error handling"/"similar to Task N" present.

**Type consistency:** `RunPlan`, `ExperimentConfig`/`TaskConfig`/`ConditionConfig`,
`make_run_id`, `collect`, `restore_workspace`, `plan_run`/`execute`/`iter_cells`
signatures match across Tasks 3–8. `find_new_sessions`/`collect` use `since:
float` (epoch seconds) consistently with `start = _now().timestamp()` in Task 7.

---

## Hand-off to Plan B

Plan A's outputs that Plan B consumes (the capture contract):
- `data/raw/<run_id>/tap/*.jsonl` — request/response bodies (component decomposition source).
- `data/raw/<run_id>/transcripts/*.jsonl` — per-turn `usage` incl. cache read/write, sidechains.
- `data/raw/<run_id>/run_meta.json` — `{run_id, task, condition, rep, model, started_utc, transcripts, versions}`.
- `tests/fixtures/sample_plain/`, `tests/fixtures/sample_subagents/` — real samples for Plan B's parser tests.

Plan B (analysis pipeline → tidy tables → metrics → figures → report) is written
**after** Task 2 completes, so its parser fixtures and exact JSON field names come
from real captured data rather than assumptions.

---

## Addendum (2026-06-19): Pilot findings & revised capture layer

The pilot (Task 2, commit `faaf90c`; see `docs/superpowers/pilot-notes.md`) confirmed
all five condition triggers but found the capture mechanism differs from this plan's
original (file-based) assumption. Revisions below supersede the earlier capture design.

1. **claude-tap stores traces in SQLite, not files.** v0.1.120 writes to
   `~/.local/share/claude-tap/traces.sqlite3` (`sessions`: id, started_at, client,
   record_count; `records`; `record_blobs`). `--tap-output-dir` is a legacy no-op.
   Verified wrapper: `.venv/bin/claude-tap --tap-no-live --tap-no-open -- <claude args>`.
   Per-run trace capture is a **post-run extraction** keyed on the run's time window:
   `claude-tap export --session-id <id> --format json -o <file>`.
2. **Subagent/workflow transcripts are nested**, not top-level: sidechains at
   `<encoded>/<uuid>/subagents/agent-*.jsonl`, workflow agents at
   `<encoded>/<uuid>/subagents/workflows/<wf>/agent-*.jsonl`. `collect_transcripts`
   must recurse and preserve relative paths.
3. **Model must be forced.** Plain `claude -p` dispatches the default (opus-4-8);
   launchers pass `--model claude-sonnet-4-6` to honor the fixed-model control.
4. **Confirmed:** transcript encoding is `/`→`-` only; proxy fidelity is exact
   (0 token delta vs JSONL); `loop_dynamic` uses `claude --continue -p` (the `/loop`
   slash command does not self-pace headlessly); `dynamic_workflow` uses
   "use a workflow" in the prompt.

### Revised/added tasks
- **Task 6 (launchers)** — per pilot §Condition commands; each wraps
  `.venv/bin/claude-tap --tap-no-live --tap-no-open -- --model "$MODEL" -p ...`.
  Also fix Makefile `tap-check` → `.venv/bin/claude-tap`.
- **Task 9 (new) — `harness/capture/collect_tap.py`** — `find_tap_sessions(db, since,
  until)` selects `sessions.id` by `started_at` window; `collect_tap(run_dir, ...)`
  exports each via the claude-tap CLI into `<run_dir>/tap/<id>.json`. TDD
  `find_tap_sessions` against a temp SQLite fixture.
- **Task 10 (new) — recursive transcripts + runner wiring** — `collect_transcripts`
  recurses (`rglob`) and preserves relative paths under `transcripts/`;
  `runner.execute` records an end timestamp and calls `collect_tap` for the window.

### Plan B hand-off (revised)
Plan B parsers read the **claude-tap JSON export** format (not files) and the
**nested** session/subagent JSONLs. Fixtures: `tests/fixtures/sample_plain/`,
`tests/fixtures/sample_subagents/` (with `transcripts/subagents/agent-*.jsonl`).
