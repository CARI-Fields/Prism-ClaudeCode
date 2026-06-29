# Full request text in trace export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the "Export experiment traces" download include the *full, untruncated* request/context text (not just an 800‑char preview) when the "Include raw context text" toggle is on.

**Architecture:** `make analyze` produces a second text parquet, `component_texts_full.parquet` (un‑truncated), next to the existing 800‑char `component_texts.parquet`. `push_data.py` uploads both to the private HF dataset. The Space keeps pulling only the 5 small files at startup; the ~523 MB full‑text file is fetched lazily on the first text‑export (`ensure_full_texts`) and cached. The export's `runs/<id>.texts.jsonl` reads from the full file.

**Tech Stack:** Python (DuckDB, pandas, FastAPI, huggingface_hub), pytest; React + Blueprint + Vitest for the picker UI.

## Global Constraints

- Branch: `feat/export-full-request-text` (already created off `origin/master`; the spec commit is on it).
- Run Python tests with `.venv/bin/python -m pytest`. Run frontend tests with `cd web/app && npx vitest run <file>`.
- The full‑text parquet (`component_texts_full.parquet`) is large and lives under the gitignored `/analysis/data/`; never commit data files.
- Full text keeps the existing "stable boilerplate emitted once per run" dedup — it is lossless for components whose text is identical across every turn in a run. Do not change the dedup.
- Commit message trailer on every commit: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: `tap_component_texts` supports untruncated output

**Files:**
- Modify: `analysis/parse/parse_tap.py:264-294`
- Test: `tests/test_parse_tap.py`

**Interfaces:**
- Produces: `tap_component_texts(tap: list, max_chars: int | None = 800) -> list[dict]`. When `max_chars is None`, `text` is the full joined component text and `truncated` is always `False`. Integer `max_chars` behaves exactly as before.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_parse_tap.py`. First extend the import on line 3:

```python
from analysis.parse.parse_tap import parse_iso, tap_turns, tap_components, tap_component_texts
```

Then append:

```python
def test_tap_component_texts_full_is_untruncated():
    long = "x" * 1000
    tap = [{
        "timestamp": "2026-06-19T21:02:44.554578+00:00",
        "duration_ms": 1000,
        "model": "claude-sonnet-4-6",
        "system": [{"type": "text", "text": "You are a Claude agent."}],
        "messages": [{"role": "user", "content": [{"type": "text", "text": long}]}],
        "response": {"usage": {
            "input_tokens": 10, "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0, "output_tokens": 5,
        }},
    }]
    preview = {r["component"]: r for r in tap_component_texts(tap)}
    full = {r["component"]: r for r in tap_component_texts(tap, max_chars=None)}
    assert preview["user input"]["text"] == long[:800]
    assert preview["user input"]["truncated"] is True
    assert full["user input"]["text"] == long
    assert full["user input"]["truncated"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_parse_tap.py::test_tap_component_texts_full_is_untruncated -v`
Expected: FAIL — with the current code `max_chars=None` causes `text[:None]` (which actually returns the whole string) but `truncated` would be `len(text) > None` → `TypeError`.

- [ ] **Step 3: Write minimal implementation**

In `analysis/parse/parse_tap.py`, change the signature and the per-row build. Replace:

```python
def tap_component_texts(tap: list, max_chars: int = 800) -> list[dict]:
```
with:
```python
def tap_component_texts(tap: list, max_chars: int | None = 800) -> list[dict]:
```

Then replace the emit block (currently lines ~283-293):

```python
        for i, request_type, text in emit:
            preview = text[:max_chars]
            rows.append({
                "request_index": i,
                "component": comp,
                "request_type": request_type,
                "text": preview,
                "truncated": len(text) > max_chars,
                "bytes": len(text.encode("utf-8")),
                "stable": stable,
            })
```
with:
```python
        for i, request_type, text in emit:
            preview = text if max_chars is None else text[:max_chars]
            rows.append({
                "request_index": i,
                "component": comp,
                "request_type": request_type,
                "text": preview,
                "truncated": False if max_chars is None else len(text) > max_chars,
                "bytes": len(text.encode("utf-8")),
                "stable": stable,
            })
```

Also update the docstring's first line so it no longer implies truncation is unconditional:

```python
    """Per-(request_index, component) real text. Truncated to a ``max_chars``
    preview by default; pass ``max_chars=None`` for the full untruncated text.
```
(keep the rest of the existing docstring about `stable` unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_parse_tap.py -v`
Expected: PASS (new test plus all existing parse_tap tests).

- [ ] **Step 5: Commit**

```bash
git add analysis/parse/parse_tap.py tests/test_parse_tap.py
git commit -m "feat(parse): tap_component_texts max_chars=None yields full untruncated text

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `build_tables` writes `component_texts_full.parquet`

**Files:**
- Modify: `analysis/build_tables.py:34-74` (`build_run`), `analysis/build_tables.py:121-143` (`build_all`)
- Test: `tests/test_build_tables.py`

**Interfaces:**
- Consumes: `tap_component_texts(tap, max_chars=None)` from Task 1.
- Produces: `build_run(run_dir)` now returns a 5‑tuple `(turns, comps, summary, comp_texts, comp_texts_full)`. `build_all(raw_dir, out_dir)` writes `component_texts_full.parquet` and its return dict gains `"component_texts_full": <int>`.

- [ ] **Step 1: Update existing tests to the new arity and assert the full file (these are the failing tests)**

In `tests/test_build_tables.py`, update `test_build_run` (line ~32) unpacking and add a full-text assertion:

```python
def test_build_run(tmp_path):
    d = _make_run(tmp_path)
    turns, comps, run, comp_texts, comp_texts_full = build_run(d)
    assert turns and all(t["condition"] == "single_agent" for t in turns)
    assert run["num_requests"] == len(turns)
    assert run["total_cache_read"] == sum(t["cache_read"] for t in turns)
    assert 0.0 <= run["cache_hit_ratio"] <= 1.0
    assert "total_cost_usd" in run
    assert all("total_cost_usd" in turn for turn in turns)
    assert run["quality_score"] == 0.0
    assert comp_texts and all({"component", "text", "stable"} <= set(x) for x in comp_texts)
    assert comp_texts_full and all(x["truncated"] is False for x in comp_texts_full)
```

Update `test_build_run_adds_research_rubric_fields` (line ~118) unpacking:

```python
    _, _, run, _, _ = build_run(d)
```

Extend `test_build_all_writes_parquet` (line ~78) to assert the new file:

```python
def test_build_all_writes_parquet(tmp_path):
    _make_run(tmp_path)
    out = tmp_path / "processed"
    counts = build_all(tmp_path / "data/raw", out)
    assert counts["runs"] == 1 and counts["turns"] > 0
    assert counts["component_texts_full"] > 0
    df = pd.read_parquet(out / "turns.parquet")
    assert {"run_id", "condition", "cache_read", "ttft_s"}.issubset(df.columns)
    full = pd.read_parquet(out / "component_texts_full.parquet")
    assert not full.empty and not full["truncated"].any()
    assert {"run_id", "component", "text", "stable", "truncated"}.issubset(full.columns)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_build_tables.py -v`
Expected: FAIL — `build_run` returns 4 values (ValueError: not enough values to unpack), and `component_texts_full.parquet` / `counts["component_texts_full"]` do not exist yet.

- [ ] **Step 3: Implement in `build_tables.py`**

In `build_run`, after `comp_texts = tap_component_texts(tap)` (line ~48) add:

```python
    comp_texts_full = tap_component_texts(tap, max_chars=None)
```

In the same function, after the existing `for x in comp_texts: x.update(stamp)` loop (lines ~56-57) add:

```python
    for x in comp_texts_full:
        x.update(stamp)
```

Change the return statement (line ~74) from:

```python
    return turns, comps, summary, comp_texts
```
to:
```python
    return turns, comps, summary, comp_texts, comp_texts_full
```

In `build_all`, change the accumulator init (line ~126):

```python
    all_turns, all_comps, all_runs, all_texts, all_texts_full = [], [], [], [], []
```

Change the unpack + accumulation inside the loop (lines ~131 and ~135):

```python
            t, c, r, x, xf = build_run(d)
```
```python
        all_turns += t; all_comps += c; all_runs.append(r); all_texts += x; all_texts_full += xf
```

Add the write after the existing `component_texts.parquet` write (after line ~141):

```python
    pd.DataFrame(all_texts_full).to_parquet(out_dir / "component_texts_full.parquet")
```

Extend the success return dict (lines ~142-143):

```python
    return {"turns": len(all_turns), "components": len(all_comps),
            "runs": len(all_runs), "component_texts": len(all_texts),
            "component_texts_full": len(all_texts_full)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_build_tables.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/build_tables.py tests/test_build_tables.py
git commit -m "feat(analysis): write component_texts_full.parquet (untruncated text)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `data_source` — `FULL_TEXT_FILE` + lazy `ensure_full_texts`

**Files:**
- Modify: `web/api/data_source.py`
- Test: `tests/test_data_source.py`

**Interfaces:**
- Produces: `FULL_TEXT_FILE = "component_texts_full.parquet"` (a module constant, NOT in `DATA_FILES`); `ensure_full_texts(_download=None) -> Path` which reads settings and pulls only `FULL_TEXT_FILE` (no‑op when `HF_DATASET_REPO` is unset).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_data_source.py`:

```python
def test_full_text_file_is_separate_from_startup_files():
    from web.api.data_source import DATA_FILES, FULL_TEXT_FILE
    assert FULL_TEXT_FILE == "component_texts_full.parquet"
    assert FULL_TEXT_FILE not in DATA_FILES


def test_ensure_full_texts_pulls_only_the_full_file(monkeypatch, tmp_path):
    import web.api.data_source as ds
    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    seen = []

    def fake_download(repo, filename, token, dest):
        seen.append((repo, filename, token))
        Path(dest).write_text("payload")

    ds.ensure_full_texts(_download=fake_download)
    assert [f for _, f, _ in seen] == [ds.FULL_TEXT_FILE]
    assert all(repo == "acme/ds" and token == "tok" for repo, _, token in seen)


def test_ensure_full_texts_noop_without_repo(monkeypatch, tmp_path):
    import web.api.data_source as ds
    monkeypatch.delenv("HF_DATASET_REPO", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    calls = []
    ds.ensure_full_texts(_download=lambda **k: calls.append(k))
    assert calls == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_data_source.py -k full -v`
Expected: FAIL — `ImportError: cannot import name 'FULL_TEXT_FILE'` / `AttributeError: ensure_full_texts`.

- [ ] **Step 3: Implement in `data_source.py`**

Add the settings import near the top (after the existing `from huggingface_hub import hf_hub_download`):

```python
from web.api.config import get_settings
```

After the `DATA_FILES = (...)` tuple, add:

```python
# Large, export-only. Deliberately NOT in DATA_FILES: it is pulled lazily on the
# first text-export (see ensure_full_texts), not at startup.
FULL_TEXT_FILE = "component_texts_full.parquet"
```

At the end of the file, add:

```python
def ensure_full_texts(_download=None) -> Path:
    """Pull the large full-text parquet on demand (export path only).

    No-op when no dataset repo is configured (local dev relies on the file
    already being present from `make analyze`). `_download` is injectable for
    tests."""
    s = get_settings()
    return ensure_data(
        s.data_dir, s.hf_dataset_repo, s.hf_token,
        files=(FULL_TEXT_FILE,), _download=_download,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_data_source.py -v`
Expected: PASS (new tests plus all existing data_source tests).

- [ ] **Step 5: Commit**

```bash
git add web/api/data_source.py tests/test_data_source.py
git commit -m "feat(api): FULL_TEXT_FILE + lazy ensure_full_texts (export-only fetch)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `push_data` uploads the full-text file to the private dataset

**Files:**
- Modify: `scripts/push_data.py`
- Test: `tests/test_push_data.py` (create)

**Interfaces:**
- Consumes: `DATA_FILES`, `FULL_TEXT_FILE` from `web.api.data_source` (Task 3).
- Produces: `scripts/push_data.py` uploads `DATA_FILES + (FULL_TEXT_FILE,)` and checks all of them for presence.

- [ ] **Step 1: Write the failing test**

Create `tests/test_push_data.py`:

```python
import importlib.util
from pathlib import Path


def _load_push_data():
    spec = importlib.util.spec_from_file_location("push_data", "scripts/push_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_push_uploads_data_files_plus_full_text(monkeypatch, tmp_path):
    from web.api.data_source import DATA_FILES, FULL_TEXT_FILE
    pd_mod = _load_push_data()
    for f in DATA_FILES + (FULL_TEXT_FILE,):
        (tmp_path / f).write_text("payload")

    uploaded = []

    class FakeApi:
        def __init__(self, token=None):
            pass

        def create_repo(self, **kwargs):
            pass

        def upload_file(self, path_or_fileobj, path_in_repo, repo_id, repo_type):
            uploaded.append(path_in_repo)

    monkeypatch.setattr(pd_mod, "HfApi", FakeApi)
    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")

    pd_mod.main([str(tmp_path)])

    assert FULL_TEXT_FILE in uploaded
    assert set(uploaded) == set(DATA_FILES) | {FULL_TEXT_FILE}


def test_push_errors_when_full_text_missing(monkeypatch, tmp_path):
    import pytest
    from web.api.data_source import DATA_FILES
    pd_mod = _load_push_data()
    for f in DATA_FILES:  # full-text file deliberately absent
        (tmp_path / f).write_text("payload")
    monkeypatch.setattr(pd_mod, "HfApi", lambda token=None: None)
    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")
    with pytest.raises(SystemExit):
        pd_mod.main([str(tmp_path)])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_push_data.py -v`
Expected: FAIL — `test_push_uploads...` fails because `FULL_TEXT_FILE` is not uploaded; `test_push_errors_when_full_text_missing` fails because the current code does not require the full file.

- [ ] **Step 3: Implement in `push_data.py`**

Change the import (line ~25):

```python
from web.api.data_source import DATA_FILES, FULL_TEXT_FILE  # noqa: E402
```

Immediately after that import (module level), add:

```python
UPLOAD_FILES = DATA_FILES + (FULL_TEXT_FILE,)
```

In `main`, change the presence check (line ~36):

```python
    missing = [f for f in UPLOAD_FILES if not (data_dir / f).exists()]
```

Change the upload loop (line ~42) and the final print (line ~49):

```python
    for name in UPLOAD_FILES:
        api.upload_file(
            path_or_fileobj=str(data_dir / name),
            path_in_repo=name,
            repo_id=repo,
            repo_type="dataset",
        )
    print(f"uploaded {len(UPLOAD_FILES)} files to private dataset {repo}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_push_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/push_data.py tests/test_push_data.py
git commit -m "feat(deploy): push component_texts_full.parquet to the private dataset

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `export` reads full text + clear error when absent

**Files:**
- Modify: `web/api/export.py` (`texts_jsonl`, `_README`)
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: `FULL_TEXT_FILE` from `web.api.data_source` (Task 3).
- Produces: `texts_jsonl(run_id)` reads `component_texts_full.parquet`; raises `FileNotFoundError` (readable message) when that file is absent.

- [ ] **Step 1: Update the fixture + add the failing tests**

In `tests/test_export.py`, in the `data_dir` fixture, add a `component_texts_full.parquet` right after the existing `component_texts.parquet` block (after line ~26):

```python
    pd.DataFrame({"run_id": ["r1", "r2"], "request_index": [0, 0],
                  "component": ["base system prompt", "base system prompt"],
                  "text": ["hi", "yo"], "truncated": [False, False],
                  "bytes": [2, 2], "stable": [True, True]}
                 ).to_parquet(tmp_path / "component_texts_full.parquet")
```

Append a new test:

```python
def test_texts_jsonl_reads_full_file_and_errors_when_missing(data_dir):
    from web.api import export
    rows = [json.loads(l) for l in export.texts_jsonl("r1").splitlines()]
    assert rows[0]["text"] == "hi"
    (data_dir / "component_texts_full.parquet").unlink()
    with pytest.raises(FileNotFoundError):
        export.texts_jsonl("r1")
```

(`test_build_zip_with_texts` already asserts `texts[0]["text"] == "hi"`; it now exercises the full file via the fixture above.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_export.py::test_texts_jsonl_reads_full_file_and_errors_when_missing -v`
Expected: FAIL — `texts_jsonl` still reads `component_texts.parquet` and never raises `FileNotFoundError`.

- [ ] **Step 3: Implement in `export.py`**

Add the import near the top (after `from web.api.queries import _clean`):

```python
from web.api.data_source import FULL_TEXT_FILE
```

Replace `texts_jsonl` (lines ~86-92):

```python
def texts_jsonl(run_id: str) -> str:
    path = _parquet(FULL_TEXT_FILE)
    if not Path(path).exists():
        raise FileNotFoundError(
            "component_texts_full.parquet not present — run `make analyze` "
            "locally or configure HF_DATASET_REPO so the Space can fetch it"
        )
    rows = _rows(
        f"SELECT * FROM read_parquet('{path}') "
        f"WHERE run_id = ? ORDER BY request_index",
        [run_id],
    )
    return ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n") if rows else ""
```

Update the `runs/<run_id>.texts.jsonl` bullet in `_README` (lines ~21-22):

```python
- `runs/<run_id>.texts.jsonl` — present only when raw text was requested; one
  JSON object per captured context part with the FULL, untruncated `text`
  (`component_texts_full`). Static parts (system prompt, tool definitions) appear
  once per run (`stable: true`); volatile parts (messages, tool results) per request.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_export.py -v`
Expected: PASS (new test plus all existing export tests, including `test_build_zip_with_texts` and `test_export_texts_flag`).

- [ ] **Step 5: Commit**

```bash
git add web/api/export.py tests/test_export.py
git commit -m "feat(api): export bundles full untruncated text; clear error when absent

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: export route fetches full text lazily

**Files:**
- Modify: `web/api/app.py:10-13` (imports), `web/api/app.py:73-85` (`export_zip`)
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: `ensure_full_texts` from `web.api.data_source` (Task 3); `texts_jsonl`'s `FileNotFoundError` (Task 5).
- Produces: `GET /api/export?texts=1` calls `ensure_full_texts()` before building the zip; a fetch/read failure surfaces as HTTP 503.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_export.py`:

```python
def test_export_texts_triggers_lazy_full_fetch(client, monkeypatch):
    import web.api.app as appmod
    called = []
    monkeypatch.setattr(appmod, "ensure_full_texts", lambda: called.append(True))
    r = client.get("/api/export", params={"runs": "r1", "texts": 1}, headers=AUTH)
    assert r.status_code == 200
    assert called == [True]


def test_export_without_texts_skips_full_fetch(client, monkeypatch):
    import web.api.app as appmod
    called = []
    monkeypatch.setattr(appmod, "ensure_full_texts", lambda: called.append(True))
    client.get("/api/export", params={"runs": "r1", "texts": 0}, headers=AUTH)
    assert called == []


def test_export_texts_missing_full_file_returns_503(client, data_dir):
    (data_dir / "component_texts_full.parquet").unlink()
    r = client.get("/api/export", params={"runs": "r1", "texts": 1}, headers=AUTH)
    assert r.status_code == 503
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_export.py -k "lazy or skips or 503" -v`
Expected: FAIL — `ensure_full_texts` is not referenced by `app` (AttributeError on monkeypatch / not called), and a missing full file currently 500s rather than 503.

- [ ] **Step 3: Implement in `app.py`**

Change the data_source import (line ~13):

```python
from web.api.data_source import ensure_data, ensure_full_texts
```

Replace `export_zip` (lines ~73-85):

```python
@app.get("/api/export", dependencies=_GATE)
def export_zip(runs: str = Query(...), texts: int = Query(default=0)) -> Response:
    run_ids = [r for r in runs.split(",") if r]
    if texts:
        try:
            ensure_full_texts()
        except Exception as exc:  # noqa: BLE001 — readable error, not a raw HF stack
            raise HTTPException(
                status_code=503, detail="raw context text is temporarily unavailable"
            ) from exc
    try:
        data = export.build_zip(run_ids, include_texts=bool(texts))
    except ValueError:
        raise HTTPException(status_code=400, detail="no valid run_ids")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="cc-traces-{ts}.zip"'},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_export.py tests/test_serve_api.py -v`
Expected: PASS (new route tests plus all existing export/serve tests).

- [ ] **Step 5: Commit**

```bash
git add web/api/app.py tests/test_export.py
git commit -m "feat(api): /api/export fetches full text lazily on texts=1; 503 on failure

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: RunPicker toggle copy reflects full text

**Files:**
- Modify: `web/app/src/export/RunPicker.tsx:65-70`
- Test: `web/app/src/export/RunPicker.test.tsx` (verify, no change expected)

**Interfaces:**
- No API change. The accessible name must keep the substring "Include raw context text" so the existing `getByRole('checkbox', { name: /include raw context text/i })` query still matches.

- [ ] **Step 1: Confirm the current test passes (baseline)**

Run: `cd web/app && npx vitest run src/export/RunPicker.test.tsx`
Expected: PASS — establishes the toggle is matched by `/include raw context text/i`.

- [ ] **Step 2: Update the Switch copy**

In `web/app/src/export/RunPicker.tsx`, replace the `Switch` (lines ~65-70):

```tsx
        <Switch
          checked={includeTexts}
          onChange={(e) => setIncludeTexts(e.currentTarget.checked)}
          label="Include raw context text (full)"
          aria-label="Include raw context text (full)"
          title="Full, untruncated request text for the selected runs — can be a large download"
        />
```

- [ ] **Step 3: Run the test to verify it still passes**

Run: `cd web/app && npx vitest run src/export/RunPicker.test.tsx`
Expected: PASS — `/include raw context text/i` still matches "Include raw context text (full)".

- [ ] **Step 4: Commit**

```bash
git add web/app/src/export/RunPicker.tsx
git commit -m "feat(web): label the export raw-text toggle as full + size hint

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Full suite green + regenerate data locally

**Files:** none (verification only)

- [ ] **Step 1: Run the whole Python test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (no regressions across analysis/web tests).

- [ ] **Step 2: Run the export frontend tests**

Run: `cd web/app && npx vitest run src/export`
Expected: PASS.

- [ ] **Step 3: Regenerate processed data so the full-text file exists locally**

Run: `make analyze`
Expected: prints counts including a non-zero `component_texts_full`; `analysis/data/processed/component_texts_full.parquet` now exists.

Verify it is untruncated and NOT staged for commit:

Run: `.venv/bin/python -c "import pandas as pd; d=pd.read_parquet('analysis/data/processed/component_texts_full.parquet'); print(len(d), bool(d['truncated'].any()))"`
Expected: a row count and `False`.

Run: `git status --porcelain analysis/data`
Expected: empty (the directory is gitignored).

- [ ] **Step 4: No commit** (verification task; data is gitignored).

---

## Notes for the executor

- After Task 8, the deploy path is: `make analyze` → `bash scripts/deploy_space.sh` (which runs `scripts/push_data.py`, now uploading the full file too). Deploy is a separate, user-initiated step — do not run it as part of implementation.
- `texts_jsonl` scans the full parquet once per selected run (mirrors `run_jsonl`); acceptable for an export action and intentionally left un-optimized.
