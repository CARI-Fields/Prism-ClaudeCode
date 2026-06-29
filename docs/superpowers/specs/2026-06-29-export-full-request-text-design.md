# Export full request text content — design

## Problem

The web "Export experiment traces" feature lets the user download a zip of
selected runs. The zip always contains the **aggregated** per-request data
(`runs/<id>.jsonl`: tokens, costs, timing, plus the context-source byte/token
breakdown under `components`). When the "Include raw context text" toggle is on,
it additionally bundles `runs/<id>.texts.jsonl` — but that text is only an
**800-char preview** per context component (`tap_component_texts(..., max_chars=800)`).
Of ~523 MB of real request/context text, only ~7 MB (≈1.3%) survives.

So a user who wants the actual request text content gets snippets, not the full
prompts, model responses, or tool results. This design adds full, untruncated
request text to the export.

## Decisions (from brainstorming)

- **Scope: Option 2 — full text, everything.** Un-truncate *all* components,
  including the base system prompt and builtin tool-definition JSON. The
  existing "stable boilerplate emitted once per run" dedup is kept — it is
  lossless for components whose text is identical across every turn in a run.
- **Gated by the toggle.** Full text appears in the export **only when
  "Include raw context text" is on**. The default (toggle off) export is
  unchanged and stays lean.
- **Lazy fetch on the Space.** The ~523 MB full-text file is fetched to the
  Space **on the first text-export**, then cached — not at startup. Cold starts
  keep pulling only the 5 small files.

## Architecture & data flow

```
make analyze (build_tables.py)
  ├─ component_texts.parquet        (preview, max_chars=800, ~7 MB)  → feeds UI panel + lightweight
  └─ component_texts_full.parquet   (full, max_chars=None, ~523 MB)  → export only
        │
push_data.py  → uploads DATA_FILES + FULL_TEXT_FILE to the PRIVATE HF dataset
        │
Space startup → ensure_data pulls the 5 small DATA_FILES only
        │
GET /api/export?texts=1 → ensure_full_texts() downloads+caches component_texts_full.parquet
        │                  (no-op locally / when HF_DATASET_REPO unset)
        └─ build_zip(include_texts=True) → runs/<id>.texts.jsonl carries FULL text
```

The raw `.tap` files are never deployed to the Space, so full text must be baked
into a parquet that reaches the Space — hence the new file rather than
re-deriving at request time.

## Components / units

### 1. Build side — `analysis/parse/parse_tap.py`, `analysis/build_tables.py`

- `tap_component_texts(tap, max_chars: int | None = 800)`: when `max_chars is
  None`, do not truncate — `text` is the full joined component text and
  `truncated` is `False`. Existing behavior for an integer `max_chars` is
  unchanged. Stable-once-per-run dedup is unchanged.
- `build_tables.py`: in addition to the existing
  `comp_texts = tap_component_texts(tap)`, build
  `comp_texts_full = tap_component_texts(tap, max_chars=None)`, accumulate it the
  same way as `all_texts`, and write `component_texts_full.parquet` with the
  same schema as `component_texts.parquet`.

### 2. Distribution — `web/api/data_source.py`, `scripts/push_data.py`

- `data_source.py`:
  - `FULL_TEXT_FILE = "component_texts_full.parquet"` — kept **out** of
    `DATA_FILES` so startup does not pull it.
  - `ensure_full_texts(_download=None)`: reads settings (`get_settings()`) and
    calls `ensure_data(data_dir, repo, token, files=(FULL_TEXT_FILE,),
    _download=_download)`. No-op when `repo` is empty (local dev relies on
    `make analyze` output). `_download` injectable for tests.
- `push_data.py`: upload `DATA_FILES + (FULL_TEXT_FILE,)` (and check all of them
  for presence) so the full file lands in the private dataset.

### 3. Export — `web/api/export.py`, `web/api/app.py`

- `export.texts_jsonl(run_id)`: read from `component_texts_full.parquet` instead
  of `component_texts.parquet`.
- `export._README`: update the description so `runs/<id>.texts.jsonl` is
  documented as **full, untruncated** captured text.
- `app.export_zip`: when `texts` is truthy, call
  `data_source.ensure_full_texts()` before `export.build_zip(...)`. `build_zip`
  stays pure (no I/O beyond reading the local parquet) so unit tests are
  unaffected.

### 4. Frontend — `web/app/src/export/RunPicker.tsx`

- Keep the existing "Include raw context text" `Switch` (already the gate).
  Update its label / add a short sub-note indicating it now bundles **full** raw
  text and can be large. No behavior change.

## Error handling

- If the full-text parquet cannot be fetched or read at export time (download
  failure on the Space, or local dev before `make analyze`), the
  `/api/export` route surfaces a clear error (HTTP 4xx/5xx with a readable
  message) rather than a raw duckdb/HF stack trace.
- `texts=0` exports never touch the full file, so they are unaffected by its
  absence.

## Testing

- `tests/test_parse_tap.py`: `tap_component_texts(tap, max_chars=None)` returns
  untruncated `text` and `truncated == False`; integer cap behavior unchanged.
- `tests/test_build_tables.py`: `make analyze` / `build_tables` writes
  `component_texts_full.parquet` with the expected schema and untruncated text.
- `tests/test_export.py`: `texts_jsonl` reads the full file; `build_zip(...,
  include_texts=True)` bundles full text; `include_texts=False` does not require
  the full file.
- `tests/test_data_source.py`: `ensure_full_texts` pulls only `FULL_TEXT_FILE`,
  is a no-op when repo unset, and `FULL_TEXT_FILE not in DATA_FILES`.
- `tests/test_serve_api.py`: `GET /api/export?texts=1` triggers the lazy fetch
  (injectable `_download`); `texts=0` does not.

## Out of scope / noted

- `texts_jsonl` scans the full parquet once per selected run (mirrors today's
  `run_jsonl`). Acceptable for an export action; optimizable later (single scan
  over all selected runs) if it becomes a problem.
- No change to the UI per-request context panel or `/api/component-texts`; they
  keep using the small preview parquet.
- The ~523 MB full file is gitignored (`/analysis/data/`) and never committed.
