# Report Backend API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a thin FastAPI + DuckDB read API that serves the processed experiment Parquet as JSON, gated by a shared token, deployable as a Docker Hugging Face Space.

**Architecture:** A new `serve/` package exposes read-only endpoints (`/api/runs`, `/api/turns`, `/api/components`, `/api/component-texts`, `/api/token-rates`, `/api/manifest`, `/healthz`). Each endpoint runs a DuckDB query over `data/processed/*.parquet` and returns raw rows — no presentation logic (the frontend owns that, per the P2 split in the spec). Access is gated by a bearer token; CORS is locked to the Vercel origin. The manifest reuses `analysis/report_variants.py` so masthead/switcher copy isn't duplicated.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, DuckDB, pytest + `fastapi.testclient` (httpx), Docker (HF Space, port 7860).

**Spec:** `docs/superpowers/specs/2026-06-25-report-frontend-backend-split-design.md`

## Global Constraints

- Python `>=3.11` (matches `pyproject.toml`).
- **No database** — DuckDB queries Parquet files in place; JSON is the wire format only.
- **Read-only** — no write endpoints, no user state.
- Endpoints return **raw query rows** (P2 split): no ECharts configs, no aggregation beyond what a single SQL query expresses.
- **Auth:** every `/api/*` route requires `Authorization: Bearer <API_TOKEN>` when `API_TOKEN` is set; `/healthz` is always open. Empty/unset `API_TOKEN` = auth disabled (dev only); production MUST set it.
- **DuckDB Parquet paths come from trusted config** (`DATA_DIR` + fixed filenames) and may be formatted into SQL; **all user-supplied values** (`run_id`, `request_index`) MUST be passed as DuckDB prepared-statement parameters (`?`).
- Reuse `analysis.report_variants` (`VARIANTS`, `STRATEGY_DESC`, `TASK_META`) for the manifest — do not re-type that copy.
- Follow the repo's flat test convention: `tests/test_*.py`, fixtures self-built in `tmp_path`.

## File Structure

| File | Responsibility |
|---|---|
| `serve/__init__.py` | Package marker |
| `serve/config.py` | `Settings` + `get_settings()` — reads `DATA_DIR`, `API_TOKEN`, `ALLOWED_ORIGINS` from env each call (no caching, so tests can monkeypatch) |
| `serve/queries.py` | DuckDB read functions returning `list[dict]` / `dict`; the only module that touches Parquet |
| `serve/auth.py` | `require_token` FastAPI dependency |
| `serve/app.py` | FastAPI app: routes + CORS, wiring queries behind `require_token` |
| `serve/requirements.txt` | Pinned deps for the HF Space Docker image |
| `serve/Dockerfile` | HF Space image (port 7860) |
| `serve/README.md` | HF Space card (front-matter: `sdk: docker`, `app_port: 7860`) |
| `scripts/deploy_space.sh` | Sync `serve/` + needed `analysis/` files + `data/processed/*` into the Space clone and push |
| `tests/test_serve_api.py` | TestClient coverage of every endpoint + the token gate |
| `pyproject.toml` | add `fastapi`, `duckdb` deps |
| `Makefile` | add `serve` (local run) + `deploy-space` targets |

---

### Task 1: Dependencies + config

**Files:**
- Modify: `pyproject.toml` (add `fastapi`, `duckdb`)
- Create: `serve/__init__.py`, `serve/config.py`
- Test: `tests/test_serve_api.py` (config portion)

**Interfaces:**
- Produces: `serve.config.Settings(data_dir: str, api_token: str, allowed_origins: list[str])` and `serve.config.get_settings() -> Settings`.

- [ ] **Step 1: Add dependencies to pyproject.toml**

In `pyproject.toml`, under `[project].dependencies`, add two entries:

```toml
    "fastapi>=0.110",
    "duckdb>=1.0",
```

- [ ] **Step 2: Install them into the venv**

Run: `.venv/bin/pip install "fastapi>=0.110" "duckdb>=1.0"`
Expected: installs successfully; `.venv/bin/python -c "import fastapi, duckdb"` exits 0.

- [ ] **Step 3: Create the package marker**

Create `serve/__init__.py` (empty file).

- [ ] **Step 4: Write the failing test for config**

Create `tests/test_serve_api.py`:

```python
import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient


def test_get_settings_reads_env(monkeypatch):
    from serve.config import get_settings
    monkeypatch.setenv("DATA_DIR", "/tmp/x")
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.app, https://b.app")
    s = get_settings()
    assert s.data_dir == "/tmp/x"
    assert s.api_token == "abc"
    assert s.allowed_origins == ["https://a.app", "https://b.app"]
```

- [ ] **Step 5: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_serve_api.py::test_get_settings_reads_env -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'serve.config'`.

- [ ] **Step 6: Implement config**

Create `serve/config.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    data_dir: str
    api_token: str
    allowed_origins: list[str]


def get_settings() -> Settings:
    origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
    return Settings(
        data_dir=os.environ.get("DATA_DIR", "data/processed"),
        api_token=os.environ.get("API_TOKEN", ""),
        allowed_origins=[o.strip() for o in origins.split(",") if o.strip()],
    )
```

- [ ] **Step 7: Run it to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_serve_api.py::test_get_settings_reads_env -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml serve/__init__.py serve/config.py tests/test_serve_api.py
git commit -m "feat(serve): add fastapi+duckdb deps and config"
```

---

### Task 2: DuckDB query layer

**Files:**
- Create: `serve/queries.py`
- Test: `tests/test_serve_api.py` (query functions)

**Interfaces:**
- Consumes: `serve.config.get_settings`; `analysis.report_variants.{VARIANTS, STRATEGY_DESC, TASK_META}`.
- Produces:
  - `get_runs() -> list[dict]`
  - `get_turns() -> list[dict]`
  - `get_components() -> list[dict]`
  - `get_component_texts(run_id: str, request_index: int | None = None) -> list[dict]`
  - `get_token_rates() -> dict`
  - `get_manifest() -> dict` with keys `variants`, `strategy_desc`, `task_meta`, `available` (a `list[dict]` of `{task, condition, runs}`).

- [ ] **Step 1: Add a shared fixture that builds a tiny dataset**

Append to `tests/test_serve_api.py`:

```python
@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    pd.DataFrame({
        "run_id": ["r1", "r2"], "task": ["coding", "research"],
        "condition": ["single_agent", "subagents"], "rep": [1, 1],
        "success": [True, False], "speedup": [1.5, float("nan")],
    }).to_parquet(tmp_path / "runs.parquet")
    pd.DataFrame({
        "run_id": ["r1", "r1"], "request_index": [0, 1],
        "task": ["coding", "coding"], "condition": ["single_agent", "single_agent"],
        "rep": [1, 1], "input_tokens": [10, 20],
    }).to_parquet(tmp_path / "turns.parquet")
    pd.DataFrame({
        "run_id": ["r1"], "request_index": [0], "component": ["base system prompt"],
        "bytes": [100], "est_tokens": [25], "request_type": ["main-agent"],
        "task": ["coding"], "condition": ["single_agent"], "rep": [1],
    }).to_parquet(tmp_path / "components.parquet")
    pd.DataFrame({
        "run_id": ["r1", "r2"], "request_index": [0, 0],
        "component": ["base system prompt", "base system prompt"],
        "request_type": ["main-agent", "main-agent"], "text": ["hi", "yo"],
        "truncated": [False, False], "bytes": [2, 2], "stable": [True, True],
        "task": ["coding", "research"], "condition": ["single_agent", "subagents"],
        "rep": [1, 1],
    }).to_parquet(tmp_path / "component_texts.parquet")
    (tmp_path / "token_rates.json").write_text(json.dumps({"base system prompt": 0.21}))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("API_TOKEN", "secret123")
    return tmp_path
```

- [ ] **Step 2: Write the failing tests for the query layer**

Append to `tests/test_serve_api.py`:

```python
def test_get_runs(data_dir):
    from serve import queries
    rows = queries.get_runs()
    assert len(rows) == 2
    assert {r["run_id"] for r in rows} == {"r1", "r2"}


def test_nan_serialized_as_null(data_dir):
    from serve import queries
    rows = {r["run_id"]: r for r in queries.get_runs()}
    assert rows["r2"]["speedup"] is None  # NaN must become JSON null, not float('nan')


def test_component_texts_filters_by_run(data_dir):
    from serve import queries
    rows = queries.get_component_texts("r1")
    assert len(rows) == 1
    assert rows[0]["run_id"] == "r1"
    assert rows[0]["text"] == "hi"


def test_manifest_reuses_variants(data_dir):
    from serve import queries
    m = queries.get_manifest()
    assert {v["key"] for v in m["variants"]} == {"multi_agent", "long_horizon"}
    assert {a["condition"] for a in m["available"]} == {"single_agent", "subagents"}
    assert "single_agent" in m["strategy_desc"]
```

- [ ] **Step 3: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_serve_api.py -k "get_runs or component_texts or manifest" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'serve.queries'`.

- [ ] **Step 4: Implement the query layer**

Create `serve/queries.py`:

```python
from __future__ import annotations

import json
import math
from pathlib import Path

import duckdb

from analysis.report_variants import STRATEGY_DESC, TASK_META, VARIANTS
from serve.config import get_settings


def _data_dir() -> Path:
    return Path(get_settings().data_dir)


def _parquet(name: str) -> str:
    # Path is trusted config (DATA_DIR + fixed filename), safe to format into SQL.
    return str(_data_dir() / name)


def _clean(v):
    # Starlette's JSONResponse uses allow_nan=False, so NaN/Inf (common in the
    # research_* columns for coding runs) would 500 the endpoint. Coerce to None.
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _rows(sql: str, params: list | None = None) -> list[dict]:
    con = duckdb.connect()
    try:
        cur = con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [{c: _clean(v) for c, v in zip(cols, row)} for row in cur.fetchall()]
    finally:
        con.close()


def get_runs() -> list[dict]:
    return _rows(f"SELECT * FROM read_parquet('{_parquet('runs.parquet')}')")


def get_turns() -> list[dict]:
    return _rows(f"SELECT * FROM read_parquet('{_parquet('turns.parquet')}')")


def get_components() -> list[dict]:
    return _rows(f"SELECT * FROM read_parquet('{_parquet('components.parquet')}')")


def get_component_texts(run_id: str, request_index: int | None = None) -> list[dict]:
    path = _parquet("component_texts.parquet")
    if request_index is None:
        return _rows(
            f"SELECT * FROM read_parquet('{path}') WHERE run_id = ?", [run_id]
        )
    return _rows(
        f"SELECT * FROM read_parquet('{path}') WHERE run_id = ? AND request_index = ?",
        [run_id, request_index],
    )


def get_token_rates() -> dict:
    return json.loads((_data_dir() / "token_rates.json").read_text())


def get_manifest() -> dict:
    available = _rows(
        f"SELECT task, condition, COUNT(*) AS runs "
        f"FROM read_parquet('{_parquet('runs.parquet')}') "
        f"GROUP BY task, condition ORDER BY task, condition"
    )
    return {
        "variants": VARIANTS,
        "strategy_desc": STRATEGY_DESC,
        "task_meta": TASK_META,
        "available": available,
    }
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_serve_api.py -k "get_runs or component_texts or manifest" -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add serve/queries.py tests/test_serve_api.py
git commit -m "feat(serve): duckdb query layer over processed parquet"
```

---

### Task 3: Token-gate dependency

**Files:**
- Create: `serve/auth.py`
- Test: `tests/test_serve_api.py` (auth)

**Interfaces:**
- Consumes: `serve.config.get_settings`.
- Produces: `serve.auth.require_token(authorization: str | None = Header(...)) -> None` — raises `HTTPException(401)` on mismatch when a token is configured; no-op when `api_token` is falsy.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_serve_api.py`:

```python
def test_require_token_rejects_missing(monkeypatch):
    from fastapi import HTTPException
    from serve.auth import require_token
    monkeypatch.setenv("API_TOKEN", "secret123")
    with pytest.raises(HTTPException) as exc:
        require_token(authorization=None)
    assert exc.value.status_code == 401


def test_require_token_accepts_match(monkeypatch):
    from serve.auth import require_token
    monkeypatch.setenv("API_TOKEN", "secret123")
    assert require_token(authorization="Bearer secret123") is None


def test_require_token_disabled_when_unset(monkeypatch):
    from serve.auth import require_token
    monkeypatch.setenv("API_TOKEN", "")
    assert require_token(authorization=None) is None
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_serve_api.py -k require_token -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'serve.auth'`.

- [ ] **Step 3: Implement the dependency**

Create `serve/auth.py`:

```python
from __future__ import annotations

from fastapi import Header, HTTPException, status

from serve.config import get_settings


def require_token(authorization: str | None = Header(default=None)) -> None:
    token = get_settings().api_token
    if not token:
        return  # auth disabled (no token configured) — dev only
    if authorization != f"Bearer {token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing token",
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_serve_api.py -k require_token -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add serve/auth.py tests/test_serve_api.py
git commit -m "feat(serve): shared bearer-token gate dependency"
```

---

### Task 4: FastAPI app + routes + CORS

**Files:**
- Create: `serve/app.py`
- Test: `tests/test_serve_api.py` (endpoint integration)

**Interfaces:**
- Consumes: `serve.queries.*`, `serve.auth.require_token`, `serve.config.get_settings`.
- Produces: `serve.app.app` (a `FastAPI` instance) with routes `GET /healthz`, `GET /api/manifest`, `GET /api/runs`, `GET /api/turns`, `GET /api/components`, `GET /api/component-texts`, `GET /api/token-rates`.

- [ ] **Step 1: Write the failing endpoint tests**

Append to `tests/test_serve_api.py`:

```python
@pytest.fixture
def client(data_dir):
    from serve.app import app
    return TestClient(app)


def test_healthz_open(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_requires_token(client):
    assert client.get("/api/runs").status_code == 401


def test_runs_endpoint_with_token(client):
    r = client.get("/api/runs", headers={"Authorization": "Bearer secret123"})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_component_texts_query_param(client):
    r = client.get(
        "/api/component-texts",
        params={"run_id": "r1"},
        headers={"Authorization": "Bearer secret123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1 and body[0]["run_id"] == "r1"


def test_manifest_endpoint(client):
    r = client.get("/api/manifest", headers={"Authorization": "Bearer secret123"})
    assert r.status_code == 200
    assert {v["key"] for v in r.json()["variants"]} == {"multi_agent", "long_horizon"}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_serve_api.py -k "healthz or requires_token or runs_endpoint or component_texts_query or manifest_endpoint" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'serve.app'`.

- [ ] **Step 3: Implement the app**

Create `serve/app.py`:

```python
from __future__ import annotations

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from serve import queries
from serve.auth import require_token
from serve.config import get_settings

app = FastAPI(title="CC experiment report API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)

_GATE = [Depends(require_token)]


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/api/manifest", dependencies=_GATE)
def manifest() -> dict:
    return queries.get_manifest()


@app.get("/api/runs", dependencies=_GATE)
def runs() -> list[dict]:
    return queries.get_runs()


@app.get("/api/turns", dependencies=_GATE)
def turns() -> list[dict]:
    return queries.get_turns()


@app.get("/api/components", dependencies=_GATE)
def components() -> list[dict]:
    return queries.get_components()


@app.get("/api/component-texts", dependencies=_GATE)
def component_texts(
    run_id: str = Query(...), request_index: int | None = Query(default=None)
) -> list[dict]:
    return queries.get_component_texts(run_id, request_index)


@app.get("/api/token-rates", dependencies=_GATE)
def token_rates() -> dict:
    return queries.get_token_rates()
```

- [ ] **Step 4: Run the full test file to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_serve_api.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Smoke-run the server against real data**

Run: `DATA_DIR=data/processed API_TOKEN=dev .venv/bin/uvicorn serve.app:app --port 8799 &` then
`sleep 2 && curl -s localhost:8799/healthz && curl -s -H "Authorization: Bearer dev" localhost:8799/api/manifest | head -c 200`
Expected: `{"status":"ok"}` then JSON beginning with the manifest's `variants`. Kill with `kill %1`.

- [ ] **Step 6: Commit**

```bash
git add serve/app.py tests/test_serve_api.py
git commit -m "feat(serve): fastapi app, routes, and CORS"
```

---

### Task 5: Containerize for the HF Space

**Files:**
- Create: `serve/requirements.txt`, `serve/Dockerfile`, `serve/README.md`
- Modify: `Makefile` (add `serve` target)

**Interfaces:**
- Produces: a Docker image that runs `uvicorn serve.app:app` on port 7860, reading Parquet from `/app/data/processed`.

- [ ] **Step 1: Pin Space dependencies**

Create `serve/requirements.txt`:

```
fastapi>=0.110
uvicorn[standard]>=0.30
duckdb>=1.0
pandas>=2.0
pyarrow>=15
```

- [ ] **Step 2: Write the Dockerfile**

Create `serve/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY serve/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY serve/ ./serve/
COPY analysis/__init__.py ./analysis/__init__.py
COPY analysis/report_variants.py ./analysis/report_variants.py
COPY data/processed/ ./data/processed/

ENV DATA_DIR=/app/data/processed
EXPOSE 7860
CMD ["uvicorn", "serve.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

- [ ] **Step 3: Write the HF Space card**

Create `serve/README.md`:

```markdown
---
title: CC Experiment Report API
emoji: 📊
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# CC Experiment Report API

FastAPI + DuckDB read-only API over the processed experiment Parquet.
Set the `API_TOKEN` and `ALLOWED_ORIGINS` secrets in Space settings.
See `docs/superpowers/specs/2026-06-25-report-frontend-backend-split-design.md`.
```

- [ ] **Step 4: Add a local-run Make target**

In `Makefile`, add to `.PHONY` and append a target:

```makefile
serve:
	DATA_DIR=data/processed $(PY) -m uvicorn serve.app:app --reload --port 8799
```

- [ ] **Step 5: Build and smoke-test the image**

Run (this environment uses the `docker` group via `sg docker`):
```bash
sg docker -c "docker build -f serve/Dockerfile -t cc-report-api ."
sg docker -c "docker run --rm -e API_TOKEN=dev -p 7860:7860 cc-report-api" &
sleep 3
curl -s localhost:7860/healthz
curl -s -H "Authorization: Bearer dev" localhost:7860/api/runs | head -c 120
```
Expected: `{"status":"ok"}` then a JSON array of run rows. Stop with `sg docker -c "docker stop \$(docker ps -q --filter ancestor=cc-report-api)"`.

- [ ] **Step 6: Commit**

```bash
git add serve/requirements.txt serve/Dockerfile serve/README.md Makefile
git commit -m "feat(serve): dockerfile + hf space card + local run target"
```

---

### Task 6: Deploy plumbing

**Files:**
- Create: `scripts/deploy_space.sh`
- Modify: `Makefile` (add `deploy-space` target)

**Interfaces:**
- Produces: `make deploy-space` — syncs `serve/`, the needed `analysis/` files, and `data/processed/*` into a local clone of the Space git repo (`SPACE_DIR`) and pushes. Refines the spec's tentative `make deploy-data` name (it deploys app + data together).

- [ ] **Step 1: Write the deploy script**

Create `scripts/deploy_space.sh`:

```bash
#!/usr/bin/env bash
# Sync the API source + processed parquet into the HF Space repo clone and push.
# Usage: SPACE_DIR=/path/to/space-clone make deploy-space
set -euo pipefail
SPACE_DIR="${SPACE_DIR:?set SPACE_DIR to a local clone of the HF Space git repo}"
REPO_ROOT="$(git rev-parse --show-toplevel)"

rsync -a --delete "$REPO_ROOT/serve/" "$SPACE_DIR/serve/"
mkdir -p "$SPACE_DIR/analysis" "$SPACE_DIR/data/processed"
cp "$REPO_ROOT/analysis/__init__.py"        "$SPACE_DIR/analysis/__init__.py"
cp "$REPO_ROOT/analysis/report_variants.py" "$SPACE_DIR/analysis/report_variants.py"
cp "$REPO_ROOT"/data/processed/*.parquet    "$SPACE_DIR/data/processed/"
cp "$REPO_ROOT/data/processed/token_rates.json" "$SPACE_DIR/data/processed/"
# HF Space expects Dockerfile + README.md + requirements.txt at the repo root.
cp "$REPO_ROOT/serve/Dockerfile"    "$SPACE_DIR/Dockerfile"
cp "$REPO_ROOT/serve/README.md"     "$SPACE_DIR/README.md"
cp "$REPO_ROOT/serve/requirements.txt" "$SPACE_DIR/requirements.txt"

cd "$SPACE_DIR"
git add -A
git commit -m "deploy: sync API + data" || echo "nothing to commit"
git push
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/deploy_space.sh`

- [ ] **Step 3: Verify it parses (no Space clone needed)**

Run: `bash -n scripts/deploy_space.sh && echo "syntax ok"`
Expected: `syntax ok`. (A full run requires `SPACE_DIR` pointing at an HF Space clone you've created and authenticated; that is a manual one-time setup step, not part of CI.)

- [ ] **Step 4: Add the Make target**

In `Makefile`, add `deploy-space` to `.PHONY` and append:

```makefile
deploy-space:
	bash scripts/deploy_space.sh
```

- [ ] **Step 5: Commit**

```bash
git add scripts/deploy_space.sh Makefile
git commit -m "feat(serve): deploy script + make deploy-space target"
```

---

## Manual setup (one-time, outside this plan)

These require your accounts/secrets and are done by hand once:
1. Create a Docker HF Space; `git clone` it locally; set `SPACE_DIR` to that path.
2. In the Space **Settings → Secrets**, set `API_TOKEN` (the shared token) and `ALLOWED_ORIGINS` (your Vercel production + preview URLs).
3. Run `make deploy-space` to push the first version; confirm the Space builds and `/healthz` responds.

## Out of scope (this plan)

- The Vercel frontend (own plan — depends on this API contract).
- Cloudflare R2 + raw-trajectory (706 MB) drill-down.
- Any change to `make analyze` or the analysis pipeline.
