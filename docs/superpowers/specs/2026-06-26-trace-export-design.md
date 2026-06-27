# Experiment trace export — download selected runs as a zip (design)

Date: 2026-06-26
Status: approved (pending spec review)
Scope: `web/api` (new export endpoint) + `web/app` (export UI)

## 1. Context

The report app serves processed experiment data via a **token-gated**, read-only
FastAPI + DuckDB API (`web/api`): `runs` (per-run metrics), `turns` (per-request
rows), `components` (per-request context-source breakdown), `component_texts`
(the raw captured context/prompt text), `token_rates`. The data is private — it
lives in a private HF Dataset pulled in at startup, and the bearer-token gate
(`require_token`) is the only access path (committing data to the public Space
would bypass the gate). The frontend (`web/app`) is the **redesigned** Blueprint
app (PR #8, now merged into `master`): an app-shell with a TopBar, a global
filter rail, and views; data is loaded once into `DataContext`; auth is a bearer
token in `localStorage` (`cc_report_token`) sent via `apiGet`.

Users want to **download experiment traces** — pick which runs, get each run's
trace, bundled into one zip.

## 2. Goals

A token-gated **export** that lets a user select specific runs and download a zip
containing each selected run's request-level trace (and, optionally, the raw
captured context text), with a self-describing manifest + README.

## 3. Decisions (locked)

| Decision point | Choice |
| --- | --- |
| Where the zip is built | **Server-side** — a new gated `/api/export` endpoint streams the zip |
| Selection | **Per-run checklist** (explicit checkboxes + select-all) |
| Per-run format | **JSONL, one line per request** (turn row + nested components); raw text in a separate per-run file |
| Raw captured text | **Opt-in**, default **off** (sensitivity); server includes it only when requested |
| App base | the **merged redesigned app** (master `5d48fa2`) — the pre-redesign concern is moot |

## 4. Export format

A zip named `cc-traces-<UTC-timestamp>.zip` containing:

- `manifest.json` — `{ generated_at (UTC ISO-8601), run_ids: [...], include_texts: bool, files: {<run_id>: [...]}, schema: { turns: [cols], components: [cols], texts: [cols] }, source: "cc-orchestration-report" }`.
- `README.md` — what each file is + load one-liners (pandas `read_json(..., lines=True)`, `jq`).
- per selected run, `runs/<run_id>.jsonl` — **one line per request**: the run's
  `turns` row (ordered by `request_index`) with that request's `components`
  (context-source breakdown) nested under a `components` key.
- per selected run, **only when `include_texts` is on**, `runs/<run_id>.texts.jsonl`
  — one line per `component_texts` row for the run (kept separate so the
  structured trace stays lean and the heavy/sensitive text is isolated).

Per-request line shape (illustrative):
```json
{"run_id":"...","task":"...","condition":"...","rep":1,"request_index":0,
 "request_type":"main-agent","input_tokens":..., "output_tokens":..., "cache_read":...,
 "cache_creation_5m":..., "cache_creation_1h":..., "ttft_s":..., "total_s":...,
 "components":[{"component":"base system prompt","est_tokens":...,"bytes":...}, ...]}
```

## 5. Backend (`web/api`)

- **`web/api/export.py`** — the export logic, isolated and unit-testable:
  - `known_run_ids() -> set[str]` — distinct `run_id`s from `runs.parquet`.
  - `run_jsonl(run_id) -> str` — builds the per-request JSONL (turns + nested
    components) for one run via DuckDB, ordered by `request_index`.
  - `texts_jsonl(run_id) -> str` — the `component_texts` JSONL for one run.
  - `build_zip(run_ids: list[str], include_texts: bool) -> bytes` — assembles
    `manifest.json` + `README.md` + per-run files into an in-memory zip
    (`zipfile.ZipFile` over `io.BytesIO`); returns the bytes. (~30 runs → small;
    in-memory is fine, no streaming complexity.)
- **Route** in `app.py`: `GET /api/export` (matches the existing `GET`-only CORS),
  gated by `_GATE` (`require_token`), params `runs: str` (comma-separated ids) and
  `texts: int = 0`. It drops unknown ids; if the valid set is **empty → 400**.
  Returns a `Response(content=build_zip(...), media_type="application/zip",
  headers={"Content-Disposition": "attachment; filename=cc-traces-<ts>.zip"})`.
- Reuses `queries._rows`/DuckDB + `_clean` (NaN→None) so JSON serialization
  matches the rest of the API. No change to `data_source.py`/`config.py`.

## 6. Frontend (`web/app`)

Integrates into the redesigned shell; small, focused units:

- **`api/client.ts`**: add `fetchExport(runIds: string[], includeTexts: boolean): Promise<Blob>`
  — `fetch(\`${apiBase()}/api/export?runs=...&texts=0|1\`, { headers: { Authorization: \`Bearer ${getToken()}\` } })`,
  throws `ApiError` on non-OK, returns `res.blob()`. (Mirrors `apiGet`'s auth; a
  plain `<a href>` can't carry the bearer header, so blob-download is required.)
- **`export/useExportDownload.ts`** — hook: `download(runIds, includeTexts)` →
  calls `fetchExport`, makes an object URL, triggers an `<a download>` with the
  filename from `Content-Disposition` (fallback `cc-traces.zip`), revokes the URL;
  exposes `{ download, busy, error }`.
- **`export/RunPicker.tsx`** — the per-run checklist: rows from `useData().data.runs`
  (task / condition / r{rep} / run_id) with a checkbox each + a select-all; an
  **"include raw context text"** Blueprint `Switch` (default off, with a one-line
  sensitivity note); a **Download** `Button` (disabled when nothing selected,
  shows `busy`); selection state is a local `Set<run_id>`.
- **`export/ExportDialog.tsx`** — a Blueprint `Dialog` wrapping `RunPicker`.
- **`TopBar`**: add an **Export** `Button` (icon `download`) that opens
  `ExportDialog`. (Dialog over a new view: self-contained, doesn't entangle with
  the global filter rail — consistent with the per-run-checklist decision, which
  was chosen over reuse-the-filters.)

## 7. Security / auth

- The endpoint is behind `require_token` — same gate as every data endpoint; it
  only repackages already-gated data, no new exposure path.
- **Raw text is opt-in** (`texts=0` default); the sensitive `component_texts` is
  exported only on explicit request.
- `runs` ids are validated against `known_run_ids()`; unknown dropped; empty → 400.
- No CORS change (GET). No new secrets.

## 8. Testing

- **Backend** (`tests/test_export.py`, run via `PYTHONPATH=<worktree> <venv>/python -m pytest`):
  - `build_zip` produces a valid zip with `manifest.json` + `README.md` +
    `runs/<id>.jsonl` for each id; each jsonl line parses and carries nested
    `components`; ordered by `request_index`.
  - `include_texts=True` adds `runs/<id>.texts.jsonl`; `False` omits them.
  - unknown ids dropped; empty selection → 400; route requires the token (401
    without it) — using the existing `test_serve_api.py` fixtures/sample parquet.
- **Frontend**:
  - `RunPicker`: renders a row per run, toggles selection, select-all, the texts
    switch; Download disabled with empty selection; clicking Download calls the
    hook with the selected ids + texts flag (mock the hook / `fetchExport`).
  - `useExportDownload`/`fetchExport`: builds the right URL with auth + texts
    flag and resolves to a Blob (mock `fetch`); triggers an anchor download.

## 9. Non-goals

- No streaming/chunked transfer (dataset is ~30 runs; in-memory zip suffices).
- No CSV/parquet export variants, no server-side persistence of exports, no
  background jobs. (YAGNI — add only if a real need appears.)
- No change to the data pipeline, `data_source.py`, or auth model.

## 10. Success criteria

- A token-holder opens Export, checks specific runs, optionally enables raw text,
  clicks Download, and receives `cc-traces-<ts>.zip` with one JSONL trace per
  selected run (+ `.texts.jsonl` when requested), a `manifest.json`, and a README.
- Endpoint gated; empty/garbage selections handled; full backend + frontend test
  suites green; builds clean.
