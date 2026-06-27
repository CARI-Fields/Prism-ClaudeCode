# Trace Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users select specific experiment runs and download their traces as a single zip (one JSONL per run; raw context text opt-in), served by a new token-gated `/api/export` endpoint.

**Architecture:** A new backend module `web/api/export.py` builds an in-memory zip (`manifest.json` + `README.md` + `runs/<id>.jsonl` [+ `runs/<id>.texts.jsonl`]) from the existing parquet via DuckDB; `app.py` exposes it at `GET /api/export` behind the existing token gate. The frontend (redesigned Blueprint shell) adds a TopBar **Export** button → a `Dialog` with a per-run checklist that fetches the zip with the bearer token and triggers a blob download.

**Tech Stack:** Python 3.12 · FastAPI · DuckDB · pandas (tests) · React 18.3 · TypeScript 5.5 · `@blueprintjs/core` v5 · Vitest.

## Global Constraints

- Backend: do NOT change `web/api/config.py`, `web/api/data_source.py`, or the auth model. Reuse `web/api/queries._clean` (NaN/Inf → None) for JSON safety.
- The export endpoint is `GET /api/export` (matches the existing `allow_methods=["GET"]` CORS — no CORS change) and is gated by `dependencies=_GATE` (`require_token`).
- Query params: `runs` = comma-separated run_ids; `texts` = `0|1` (default `0`). Raw text (`component_texts`) is exported ONLY when `texts=1`.
- Unknown run_ids are dropped; if no valid run_ids remain → HTTP **400**.
- Zip filename: `cc-traces-<UTC timestamp>.zip` (`Content-Disposition: attachment`). Entries: `manifest.json`, `README.md`, `runs/<run_id>.jsonl`, and `runs/<run_id>.texts.jsonl` (only when `texts=1`).
- Per-run `runs/<id>.jsonl`: ONE line per request — the `turns` row (ordered by `request_index`) with that request's `components` nested under a `"components"` key (each `{component, est_tokens, bytes}`).
- Frontend: reuse `apiBase()` + `getToken()` for auth (bearer). A plain `<a href>` cannot send the token, so download = fetch→Blob→object-URL→`<a download>`.
- Run backend tests from the worktree root with:
  `PYTHONPATH=$(pwd) /home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest <args>`
  (the editable install points at the original repo; `PYTHONPATH` makes `web.api` resolve to the worktree).
- Run frontend tests from `web/app/`: `npx vitest run <path>` (single) / `npm test` (full). Commit after every green task.

---

## File Structure

**Backend (created):** `web/api/export.py` (export logic), `tests/test_export.py` (tests).
**Backend (modified):** `web/api/app.py` (the route).
**Frontend (created):** `web/app/src/export/useExportDownload.ts`, `web/app/src/export/RunPicker.tsx`, `web/app/src/export/ExportControl.tsx`, and co-located tests.
**Frontend (modified):** `web/app/src/api/client.ts` (add `fetchExport`), `web/app/src/components/shell/TopBar.tsx` (render `<ExportControl/>`), `web/app/src/theme/tokens.css` (run-picker styles).

---

## Task 1: Backend export module (`build_zip` + helpers)

**Files:**
- Create: `web/api/export.py`
- Create: `tests/test_export.py`

**Interfaces:**
- Produces: `known_run_ids() -> set[str]`; `run_jsonl(run_id: str) -> str`; `texts_jsonl(run_id: str) -> str`; `build_zip(run_ids: list[str], include_texts: bool, now: datetime | None = None) -> bytes`. `build_zip` drops unknown ids (preserving order, de-duped) and raises `ValueError` if none remain.
- Consumes: `web.api.config.get_settings().data_dir`; `web.api.queries._clean`.

- [ ] **Step 1: Write the failing test**

`tests/test_export.py`:
```python
import io
import json
import zipfile
from datetime import datetime, timezone

import pandas as pd
import pytest


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    pd.DataFrame({"run_id": ["r1", "r2"], "task": ["coding", "research"],
                  "condition": ["single_agent", "subagents"], "rep": [1, 1]}
                 ).to_parquet(tmp_path / "runs.parquet")
    pd.DataFrame({"run_id": ["r1", "r1"], "request_index": [1, 0],
                  "request_type": ["main-agent", "main-agent"],
                  "input_tokens": [20, 10]}).to_parquet(tmp_path / "turns.parquet")
    pd.DataFrame({"run_id": ["r1", "r1"], "request_index": [0, 0],
                  "component": ["base system prompt", "user input"],
                  "est_tokens": [25, 5], "bytes": [100, 20]}
                 ).to_parquet(tmp_path / "components.parquet")
    pd.DataFrame({"run_id": ["r1", "r2"], "request_index": [0, 0],
                  "component": ["base system prompt", "base system prompt"],
                  "text": ["hi", "yo"], "truncated": [False, False],
                  "bytes": [2, 2], "stable": [True, True]}
                 ).to_parquet(tmp_path / "component_texts.parquet")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return tmp_path


def _zip(data: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(data))


def test_known_run_ids(data_dir):
    from web.api import export
    assert export.known_run_ids() == {"r1", "r2"}


def test_run_jsonl_one_line_per_request_ordered_with_components(data_dir):
    from web.api import export
    lines = [json.loads(l) for l in export.run_jsonl("r1").splitlines()]
    assert [l["request_index"] for l in lines] == [0, 1]  # ordered by request_index
    first = lines[0]
    assert first["input_tokens"] == 10
    assert {c["component"] for c in first["components"]} == {"base system prompt", "user input"}
    assert first["components"][0].keys() >= {"component", "est_tokens", "bytes"}
    assert lines[1]["components"] == []  # request 1 has no components


def test_build_zip_structure_without_texts(data_dir):
    from web.api import export
    z = _zip(export.build_zip(["r1"], include_texts=False,
                              now=datetime(2026, 1, 2, tzinfo=timezone.utc)))
    names = set(z.namelist())
    assert "manifest.json" in names and "README.md" in names
    assert "runs/r1.jsonl" in names
    assert "runs/r1.texts.jsonl" not in names
    m = json.loads(z.read("manifest.json"))
    assert m["run_ids"] == ["r1"] and m["include_texts"] is False
    assert m["generated_at"] == "2026-01-02T00:00:00+00:00"


def test_build_zip_with_texts(data_dir):
    from web.api import export
    z = _zip(export.build_zip(["r1"], include_texts=True))
    assert "runs/r1.texts.jsonl" in set(z.namelist())
    texts = [json.loads(l) for l in z.read("runs/r1.texts.jsonl").decode().splitlines()]
    assert texts[0]["text"] == "hi"


def test_build_zip_drops_unknown_and_dedupes(data_dir):
    from web.api import export
    z = _zip(export.build_zip(["r1", "bogus", "r1"], include_texts=False))
    assert "runs/r1.jsonl" in set(z.namelist())
    assert "runs/bogus.jsonl" not in set(z.namelist())
    assert json.loads(z.read("manifest.json"))["run_ids"] == ["r1"]


def test_build_zip_empty_raises(data_dir):
    from web.api import export
    with pytest.raises(ValueError):
        export.build_zip(["bogus"], include_texts=False)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=$(pwd) /home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_export.py -q`
Expected: FAIL (`No module named 'web.api.export'`).

- [ ] **Step 3: Implement `web/api/export.py`**

```python
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from web.api.config import get_settings
from web.api.queries import _clean

_README = """# CC experiment trace export

Each selected run has one file under `runs/`:

- `runs/<run_id>.jsonl` — one JSON object per request (a "turn"), ordered by
  `request_index`, with that request's context-source breakdown nested under
  `components` (`{component, est_tokens, bytes}`).
- `runs/<run_id>.texts.jsonl` — present only when raw text was requested; one
  JSON object per captured context part (`component_texts`).

`manifest.json` lists the included runs and the export options.

Load (Python):

    import pandas as pd
    df = pd.read_json("runs/<run_id>.jsonl", lines=True)

Inspect (shell):

    jq . runs/<run_id>.jsonl
"""


def _data_dir() -> Path:
    return Path(get_settings().data_dir)


def _parquet(name: str) -> str:
    # Trusted config path (DATA_DIR + fixed filename), safe to format into SQL.
    return str(_data_dir() / name)


def _rows(sql: str, params: list) -> list[dict]:
    con = duckdb.connect()
    try:
        cur = con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [{c: _clean(v) for c, v in zip(cols, row)} for row in cur.fetchall()]
    finally:
        con.close()


def known_run_ids() -> set[str]:
    rows = _rows(
        f"SELECT DISTINCT run_id FROM read_parquet('{_parquet('runs.parquet')}')", []
    )
    return {r["run_id"] for r in rows}


def run_jsonl(run_id: str) -> str:
    turns = _rows(
        f"SELECT * FROM read_parquet('{_parquet('turns.parquet')}') "
        f"WHERE run_id = ? ORDER BY request_index",
        [run_id],
    )
    comps = _rows(
        f"SELECT * FROM read_parquet('{_parquet('components.parquet')}') WHERE run_id = ?",
        [run_id],
    )
    by_req: dict = {}
    for c in comps:
        by_req.setdefault(c.get("request_index"), []).append(
            {k: c.get(k) for k in ("component", "est_tokens", "bytes")}
        )
    out = []
    for t in turns:
        row = dict(t)
        row["components"] = by_req.get(row.get("request_index"), [])
        out.append(json.dumps(row, ensure_ascii=False))
    return ("\n".join(out) + "\n") if out else ""


def texts_jsonl(run_id: str) -> str:
    rows = _rows(
        f"SELECT * FROM read_parquet('{_parquet('component_texts.parquet')}') "
        f"WHERE run_id = ? ORDER BY request_index",
        [run_id],
    )
    return ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n") if rows else ""


def build_zip(run_ids, include_texts: bool, now: datetime | None = None) -> bytes:
    known = known_run_ids()
    valid: list[str] = []
    for rid in run_ids:
        if rid in known and rid not in valid:
            valid.append(rid)
    if not valid:
        raise ValueError("no valid run_ids")
    manifest = {
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "run_ids": valid,
        "include_texts": include_texts,
        "source": "cc-orchestration-report",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("README.md", _README)
        for rid in valid:
            z.writestr(f"runs/{rid}.jsonl", run_jsonl(rid))
            if include_texts:
                z.writestr(f"runs/{rid}.texts.jsonl", texts_jsonl(rid))
    return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=$(pwd) /home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_export.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add web/api/export.py tests/test_export.py
git commit -m "feat(api): export module — build per-run trace zip"
```

---

## Task 2: Backend route `GET /api/export`

**Files:**
- Modify: `web/api/app.py`
- Modify: `tests/test_export.py` (add route tests)

**Interfaces:**
- Consumes: `web.api.export.build_zip` (Task 1); existing `_GATE`, `app`.
- Produces: `GET /api/export?runs=<csv>&texts=<0|1>` → `application/zip` (200) gated by the token; empty/garbage selection → 400.

- [ ] **Step 1: Write the failing test** (append to `tests/test_export.py`)

```python
from fastapi.testclient import TestClient


@pytest.fixture
def client(data_dir, monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret123")
    from web.api.app import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer secret123"}


def test_export_requires_token(client):
    assert client.get("/api/export", params={"runs": "r1"}).status_code == 401


def test_export_returns_zip(client):
    r = client.get("/api/export", params={"runs": "r1", "texts": 0}, headers=AUTH)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert "attachment" in r.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert "runs/r1.jsonl" in set(z.namelist())
    assert "runs/r1.texts.jsonl" not in set(z.namelist())


def test_export_texts_flag(client):
    r = client.get("/api/export", params={"runs": "r1", "texts": 1}, headers=AUTH)
    assert "runs/r1.texts.jsonl" in set(zipfile.ZipFile(io.BytesIO(r.content)).namelist())


def test_export_empty_selection_400(client):
    assert client.get("/api/export", params={"runs": "bogus"}, headers=AUTH).status_code == 400
    assert client.get("/api/export", params={"runs": ""}, headers=AUTH).status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=$(pwd) /home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_export.py -k export_ -q`
Expected: FAIL (route 404 / not found).

- [ ] **Step 3: Add the route to `web/api/app.py`**

Add `HTTPException` and `Response` to the FastAPI import, import `export`, and append the route. The import line becomes:
```python
from fastapi import Depends, FastAPI, HTTPException, Query, Response
```
Add near the other imports:
```python
from datetime import datetime, timezone

from web.api import export
```
Append after the last route:
```python
@app.get("/api/export", dependencies=_GATE)
def export_zip(runs: str = Query(...), texts: int = Query(default=0)) -> Response:
    run_ids = [r for r in runs.split(",") if r]
    try:
        data = export.build_zip(run_ids, include_texts=bool(texts))
    except ValueError:
        raise HTTPException(status_code=400, detail="no valid run_ids")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="cc-traces-{ts}.zip"'},
    )
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=$(pwd) /home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_export.py -q`
Expected: PASS (all). Then run the API suite to confirm no regression:
`PYTHONPATH=$(pwd) /home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_serve_api.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add web/api/app.py tests/test_export.py
git commit -m "feat(api): GET /api/export route (gated zip, empty->400)"
```

---

## Task 3: Frontend `fetchExport` + `useExportDownload`

**Files:**
- Modify: `web/app/src/api/client.ts`
- Create: `web/app/src/api/client.export.test.ts`
- Create: `web/app/src/export/useExportDownload.ts`
- Create: `web/app/src/export/useExportDownload.test.ts`

**Interfaces:**
- Consumes: existing `apiBase()`, `getToken()`, `ApiError` from `api/client.ts`.
- Produces: `fetchExport(runIds: string[], includeTexts: boolean): Promise<Blob>`; `useExportDownload(): { download(runIds: string[], includeTexts: boolean): Promise<void>; busy: boolean; error: string | null }`.

- [ ] **Step 1: Write the failing tests**

`web/app/src/api/client.export.test.ts`:
```ts
import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchExport } from './client';

afterEach(() => vi.restoreAllMocks());

describe('fetchExport', () => {
  it('requests the export URL with auth + texts flag and returns a Blob', async () => {
    localStorage.setItem('cc_report_token', 'tok');
    const blob = new Blob(['zip']);
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, blob: () => Promise.resolve(blob) });
    vi.stubGlobal('fetch', fetchMock);
    const out = await fetchExport(['r1', 'r2'], true);
    expect(out).toBe(blob);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/export?runs=r1,r2&texts=1');
    expect((opts.headers as Record<string, string>).Authorization).toBe('Bearer tok');
  });
  it('throws ApiError on non-ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(fetchExport(['r1'], false)).rejects.toMatchObject({ status: 500 });
  });
});
```

`web/app/src/export/useExportDownload.test.ts`:
```ts
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useExportDownload } from './useExportDownload';
import * as client from '../api/client';

afterEach(() => vi.restoreAllMocks());

describe('useExportDownload', () => {
  it('downloads a blob: fetch → object URL → anchor click, toggling busy', async () => {
    const blob = new Blob(['zip']);
    vi.spyOn(client, 'fetchExport').mockResolvedValue(blob);
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() });
    const click = vi.fn();
    vi.spyOn(document, 'createElement').mockReturnValue({ href: '', download: '', click, remove: vi.fn() } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, 'appendChild').mockImplementation((n) => n);

    const { result } = renderHook(() => useExportDownload());
    await act(async () => { await result.current.download(['r1'], false); });

    expect(client.fetchExport).toHaveBeenCalledWith(['r1'], false);
    expect(click).toHaveBeenCalled();
    expect(result.current.busy).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web/app && npx vitest run src/api/client.export.test.ts src/export/useExportDownload.test.ts`
Expected: FAIL (`fetchExport`/module not found).

- [ ] **Step 3: Implement**

Append to `web/app/src/api/client.ts`:
```ts
export async function fetchExport(runIds: string[], includeTexts: boolean): Promise<Blob> {
  const runs = runIds.map(encodeURIComponent).join(',');
  const res = await fetch(`${apiBase()}/api/export?runs=${runs}&texts=${includeTexts ? 1 : 0}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (res.status === 401) throw new ApiError(401, 'unauthorized');
  if (!res.ok) throw new ApiError(res.status, `export failed: ${res.status}`);
  return res.blob();
}
```

`web/app/src/export/useExportDownload.ts`:
```ts
import { useCallback, useState } from 'react';
import { fetchExport } from '../api/client';

export function useExportDownload() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const download = useCallback(async (runIds: string[], includeTexts: boolean) => {
    setBusy(true);
    setError(null);
    try {
      const blob = await fetchExport(runIds, includeTexts);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cc-traces.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);
  return { download, busy, error };
}
```

- [ ] **Step 4: Run tests**

Run: `cd web/app && npx vitest run src/api/client.export.test.ts src/export/useExportDownload.test.ts` → PASS. Then `npm test` → all green.

- [ ] **Step 5: Commit**

```bash
git add web/app/src/api/client.ts web/app/src/api/client.export.test.ts web/app/src/export/useExportDownload.ts web/app/src/export/useExportDownload.test.ts
git commit -m "feat(web): fetchExport + useExportDownload (auth blob download)"
```

---

## Task 4: Frontend `RunPicker` (per-run checklist)

**Files:**
- Create: `web/app/src/export/RunPicker.tsx`
- Create: `web/app/src/export/RunPicker.test.tsx`
- Modify: `web/app/src/theme/tokens.css` (run-picker layout)

**Interfaces:**
- Consumes: `useData()` (`data.runs`) from `data/DataContext`; `useExportDownload()` (Task 3); Blueprint `Checkbox`/`Switch`/`Button`; `Run` from `types`.
- Produces: `<RunPicker />` — per-run checkboxes + select-all + "Include raw context text" switch + Download button (disabled when nothing selected) that calls `download(selectedIds, includeTexts)`.

- [ ] **Step 1: Write the failing test**

`web/app/src/export/RunPicker.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RunPicker } from './RunPicker';

const download = vi.fn();
vi.mock('./useExportDownload', () => ({ useExportDownload: () => ({ download, busy: false, error: null }) }));
vi.mock('../data/DataContext', () => ({
  useData: () => ({ data: { runs: [
    { run_id: 'a1', task: 'coding', condition: 'goal', rep: 1 },
    { run_id: 'b2', task: 'research', condition: 'subagents', rep: 2 },
  ] } }),
}));

describe('RunPicker', () => {
  it('selects runs and downloads with the texts flag', async () => {
    render(<RunPicker />);
    const dl = screen.getByRole('button', { name: /download/i });
    expect(dl).toBeDisabled();                                   // nothing selected
    await userEvent.click(screen.getByLabelText(/coding \/ goal \/ r1 · a1/));
    await userEvent.click(screen.getByRole('checkbox', { name: /include raw context text/i }));
    expect(dl).toBeEnabled();
    await userEvent.click(dl);
    expect(download).toHaveBeenCalledWith(['a1'], true);
  });

  it('select-all toggles every run', async () => {
    render(<RunPicker />);
    await userEvent.click(screen.getByRole('checkbox', { name: /select all/i }));
    await userEvent.click(screen.getByRole('button', { name: /download/i }));
    expect(download).toHaveBeenLastCalledWith(['a1', 'b2'], false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/app && npx vitest run src/export/RunPicker.test.tsx`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

`web/app/src/export/RunPicker.tsx`:
```tsx
import { useState } from 'react';
import { Button, Checkbox, Switch } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useExportDownload } from './useExportDownload';

export function RunPicker() {
  const { data } = useData();
  const runs = data?.runs ?? [];
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [includeTexts, setIncludeTexts] = useState(false);
  const { download, busy, error } = useExportDownload();

  const allSelected = runs.length > 0 && selected.size === runs.length;
  const toggle = (id: string) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
  const toggleAll = () =>
    setSelected(allSelected ? new Set() : new Set(runs.map((r) => r.run_id)));
  // Download the runs in the order they appear in the list (stable, not Set order).
  const orderedSelected = runs.map((r) => r.run_id).filter((id) => selected.has(id));

  return (
    <div className="run-picker">
      <div className="run-picker-head">
        <Checkbox
          checked={allSelected}
          indeterminate={selected.size > 0 && !allSelected}
          onChange={toggleAll}
          label={`Select all (${runs.length})`}
        />
        <Switch
          checked={includeTexts}
          onChange={(e) => setIncludeTexts(e.currentTarget.checked)}
          label="Include raw context text"
          aria-label="Include raw context text"
        />
      </div>
      <div className="run-picker-list">
        {runs.map((r) => (
          <Checkbox
            key={r.run_id}
            checked={selected.has(r.run_id)}
            onChange={() => toggle(r.run_id)}
            label={`${r.task} / ${r.condition} / r${r.rep} · ${r.run_id}`}
          />
        ))}
      </div>
      {error && <p className="run-picker-error">{error}</p>}
      <Button
        intent="primary"
        icon="download"
        loading={busy}
        disabled={orderedSelected.length === 0}
        text={`Download ${orderedSelected.length || ''} ${orderedSelected.length === 1 ? 'trace' : 'traces'}`.replace('  ', ' ').trim()}
        onClick={() => download(orderedSelected, includeTexts)}
      />
    </div>
  );
}
```

Append to `web/app/src/theme/tokens.css`:
```css
.run-picker { display: flex; flex-direction: column; gap: 12px; min-width: 360px; }
.run-picker-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding-bottom: 8px; border-bottom: 1px solid var(--app-line); }
.run-picker-list { display: flex; flex-direction: column; gap: 2px; max-height: 360px; overflow: auto; font-family: var(--app-mono); font-size: 12px; }
.run-picker-error { color: #e03131; font-size: 12px; margin: 0; }
```

- [ ] **Step 4: Run tests**

Run: `cd web/app && npx vitest run src/export/RunPicker.test.tsx` → PASS. Then `npm test` → all green.

- [ ] **Step 5: Commit**

```bash
git add web/app/src/export/RunPicker.tsx web/app/src/export/RunPicker.test.tsx web/app/src/theme/tokens.css
git commit -m "feat(web): RunPicker per-run export checklist"
```

---

## Task 5: Frontend `ExportControl` + TopBar wiring

**Files:**
- Create: `web/app/src/export/ExportControl.tsx`
- Create: `web/app/src/export/ExportControl.test.tsx`
- Modify: `web/app/src/components/shell/TopBar.tsx`

**Interfaces:**
- Consumes: `RunPicker` (Task 4); Blueprint `Button`/`Dialog`/`DialogBody`.
- Produces: `<ExportControl />` — a TopBar Export button that opens a `Dialog` containing `RunPicker`. Rendered inside `TopBar`'s right `Navbar.Group`.

- [ ] **Step 1: Write the failing test**

`web/app/src/export/ExportControl.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExportControl } from './ExportControl';

vi.mock('./RunPicker', () => ({ RunPicker: () => <div>RUN PICKER</div> }));

describe('ExportControl', () => {
  it('opens a dialog with the run picker', async () => {
    render(<ExportControl />);
    expect(screen.queryByText('RUN PICKER')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /export traces/i }));
    expect(await screen.findByText('RUN PICKER')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/app && npx vitest run src/export/ExportControl.test.tsx`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

`web/app/src/export/ExportControl.tsx`:
```tsx
import { useState } from 'react';
import { Button, Dialog, DialogBody } from '@blueprintjs/core';
import { RunPicker } from './RunPicker';

export function ExportControl() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button minimal icon="download" aria-label="Export traces" onClick={() => setOpen(true)} />
      <Dialog
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Export experiment traces"
        icon="download"
      >
        <DialogBody>
          <RunPicker />
        </DialogBody>
      </Dialog>
    </>
  );
}
```

Modify `web/app/src/components/shell/TopBar.tsx` — import `ExportControl` and render it in the right group before the theme `Switch`. Add the import:
```tsx
import { ExportControl } from '../../export/ExportControl';
```
And change the right `Navbar.Group` to include it first:
```tsx
      <Navbar.Group align={Alignment.RIGHT}>
        <ExportControl />
        <Navbar.Divider />
        <Switch
          checked={mode === 'dark'}
          onChange={toggle}
          label={mode === 'dark' ? '☾ Dark' : '☀ Light'}
          aria-label="Toggle dark theme"
          style={{ margin: 0 }}
        />
        <Navbar.Divider />
        <Button minimal icon="refresh" aria-label="Reload data" onClick={reload} />
      </Navbar.Group>
```

- [ ] **Step 4: Run tests**

Run: `cd web/app && npx vitest run src/export/ExportControl.test.tsx` → PASS. Then `npm test` → all green (the existing `TopBar.test.tsx` still passes — `ExportControl`'s dialog is closed by default, so `RunPicker`/`useData` aren't invoked there). Then `npm run build` → exit 0.

- [ ] **Step 5: Commit**

```bash
git add web/app/src/export/ExportControl.tsx web/app/src/export/ExportControl.test.tsx web/app/src/components/shell/TopBar.tsx
git commit -m "feat(web): TopBar Export button + dialog"
```

---

## Self-Review

**Spec coverage:**
- Server-side gated `/api/export` streaming a zip → Task 2 (route, `_GATE`), Task 1 (`build_zip`). ✓
- Per-run JSONL (one line per request, components nested), ordered → Task 1 (`run_jsonl` + test). ✓
- Raw text opt-in, default off; separate `.texts.jsonl` → Task 1 (`include_texts`), Task 2 (`texts` param default 0). ✓
- `manifest.json` + `README.md` → Task 1. ✓
- Unknown ids dropped, empty → 400 → Task 1 (`ValueError`), Task 2 (→400). ✓
- Per-run checklist + select-all + texts toggle + Download → Task 4. ✓
- Auth blob download (bearer, no `<a href>`) → Task 3 (`fetchExport`/`useExportDownload`). ✓
- TopBar Export button → Dialog → Task 5. ✓
- No change to config/data_source/auth model → only `app.py` modified server-side. ✓
- Testing (backend build_zip/route/auth/texts/unknown; frontend picker/download) → Tasks 1–5. ✓

**Placeholder scan:** No TBD/TODO; every code/test step is complete. The README string is real content, not a placeholder.

**Type consistency:** `build_zip(run_ids, include_texts, now)` / `known_run_ids` / `run_jsonl` / `texts_jsonl` names match between Task 1 (def) and Task 2 (use). `fetchExport(runIds, includeTexts)` and `useExportDownload().download(runIds, includeTexts)` match between Task 3 (def) and Task 4 (use). `RunPicker` and `ExportControl` names match between Tasks 4/5. The `texts` query param (`0|1`) is consistent between `fetchExport` (Task 3) and the route (Task 2).
