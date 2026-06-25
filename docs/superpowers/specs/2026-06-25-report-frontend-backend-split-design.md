# Report Frontend/Backend Split — Design

**Date:** 2026-06-25
**Status:** Draft for review
**Builds on:** Plan B analysis pipeline (`make analyze`) + the ECharts SPA report
(`analysis/echarts_report.py::render_combined_report`). Consumes `data/processed/*.parquet`.

## 1. Problem

The report is a single self-contained file: `analysis/echarts_report.py` inlines the
ECharts library **plus all data plus full component texts** into `reports/report.html`.
That file is now **18 MB** and growing with every run. Two consequences:

- **It chokes the browser** — an 18 MB single-page app is slow to load and render.
- **Sharing is clumsy** — you hand someone an 18 MB file instead of a URL.

The underlying data is tiny and static: `data/processed/` is **~468 KB** of Parquet
(`turns` 188 KB, `components` 102 KB, `component_texts` 136 KB, `runs` 37 KB,
`token_rates.json` 0.5 KB), regenerated offline by `make analyze`. The 18 MB is almost
entirely **inlining bloat**, not real data. So the fix is to stop shipping one fat file
and instead serve a small static frontend that fetches the data on demand.

## 2. Goals / Non-goals

**Goals**
- Replace the 18 MB single file with a **deployed web app**: static frontend + thin data API.
- Frontend on **Vercel** (shareable URL, push-to-deploy, CDN).
- Keep the existing `make analyze` pipeline and its Parquet output **unchanged**.
- Private access for **you + a few teammates**.
- Stay at **~$0/mo**.

**Non-goals (YAGNI)**
- No database. Parquet + DuckDB is the store; see §4.
- No user writes, no accounts/identity provider — a single shared token gates access (§7).
- No raw-trajectory (706 MB) drill-down in this build — explicit future phase (§9).
- No Cloudflare R2 yet — only needed once the big raw blobs get served (§9).

## 3. Architecture

```
  make analyze ──> data/processed/*.parquet        (existing pipeline, unchanged)
                          │
                          ▼  make deploy-data  (copy + git push into the Space repo)
   ┌─────────────────────────────────────────────┐
   │  Hugging Face Space (Docker, port 7860)       │
   │  FastAPI + DuckDB  ──reads──> *.parquet         │  raw data never leaves the server
   │  shared-token gate + CORS(locked to Vercel)     │
   │  GET /api/... ──> JSON (raw rows)               │
   └─────────────────────────────────────────────┘
                          │  JSON over HTTPS  (token header)
                          ▼
   ┌─────────────────────────────────────────────┐
   │  Vercel static SPA  (Vite + React + ECharts)   │  owns ALL presentation + interactivity
   └─────────────────────────────────────────────┘
```

- **Frontend (Vercel):** Vite + React + Apache ECharts. Owns 100% of presentation —
  every chart config ported from `echarts_report.py` into JS — and all interactivity.
- **Backend (private HF Space):** FastAPI + DuckDB. Thin: parameterized DuckDB reads
  over Parquet, returns raw rows as JSON. No presentation logic (P2 split — §5).
- **Storage:** `data/processed/*.parquet` committed into the Space repo (<500 KB).

### Decision log (how we got here)
- **Backend role = lightweight read API** (not pure-static, not full dynamic).
- **Store = Parquet + DuckDB**, *not* a database. Data is sub-1 MB, read-only,
  already columnar; DuckDB reads Parquet natively. JSON is the wire format + tiny config
  only. A DB would add ETL, ops, and cost for data smaller than a photo.
- **DuckDB runs server-side** (researched client-side DuckDB-WASM too) — chosen because
  access must be **private**, so raw Parquet must not be publicly downloadable.
- **Host = HF Space** (Docker) over Firebase/Cloud Run — audience is "me + a few
  teammates," so Firebase Auth's many-user login earns nothing here; HF Space is $0 with
  zero infra wiring. Private *access* is achieved via an app-level token gate, not a
  private Space (§7). Cloud Run is the documented fallback if HF's 48 h idle-sleep or the
  token-gate model becomes a pain.
- **Split = P2 (cleanest):** backend serves raw rows; frontend rebuilds all chart logic
  in JS — keeps the interactive toggles instant (client-side) and the backend decoupled
  from ECharts.

## 4. Data / query layer

The five processed artifacts are the contract (already produced by Plan B):
`runs.parquet`, `turns.parquet`, `components.parquet`, `component_texts.parquet`,
`token_rates.json`. DuckDB queries them in place — no schema, no migrations. The
`component_texts` table is the heavy one (full context text) and is fetched **lazily**,
only on drill-down (§6), never in the bulk load.

## 5. Frontend/backend split (P2)

Today `analysis/echarts_report.py` (114 KB) builds ECharts `option` objects in Python
and inlines them. Under **P2**, that presentation logic is **re-expressed in JS** on the
frontend; the backend returns only raw query rows. Trade-off accepted: more rewrite than
a thin "backend emits ECharts JSON" port, in exchange for a clean separation and
instant, client-side interactivity (no server round-trip per toggle).

**Frontend owns** (ported from the current SPA):
- The masthead switcher between the two condition-scoped reads (`multi_agent` ↔
  `long_horizon`) — driven by `VARIANTS` / the `/api/manifest` response.
- The §0 task-prompt band per read.
- The context-breakdown roll-up mirroring Claude Code's `/context` category buckets:
  System prompt · System tools · MCP tools · Custom agents · Memory files · Skills ·
  Messages.
- The token/source and agent-grouping toggles on the context breakdown.
- All charts: cache accumulation, context growth, latency, success/speedup, cost/efficiency.

## 6. API surface

All JSON, all DuckDB-over-Parquet, all gated by the shared token (§7):

| Endpoint | Returns |
|---|---|
| `GET /api/manifest` | conditions / tasks / runs available + variant defs (drives the switcher) |
| `GET /api/runs` | whole `runs` table (37 KB) |
| `GET /api/turns` | whole `turns` table (188 KB) |
| `GET /api/components` | whole `components` table (102 KB) |
| `GET /api/component-texts?run_id=…[&request_index=…]` | heavy full texts, **lazy / drill-down only** |
| `GET /api/token-rates` | `token_rates.json` |
| `GET /healthz` | liveness / wake ping |

Tables are tiny, so the frontend loads runs/turns/components once, caches in memory, and
does all slicing + aggregation + charting client-side. Only `component-texts` is fetched
on demand.

## 7. Privacy & access

A *private* HF Space gates its HTTP API behind an HF token, which a public Vercel SPA
cannot safely hold. So:

- **Space is public; FastAPI enforces a shared bearer token** on every `/api/*` request.
  The SPA prompts for the token once, stores it in `localStorage`, and sends it as an
  `Authorization` header. Only people with the token get in; raw Parquet stays
  server-side (only computed JSON crosses the wire).
- **CORS** is locked to the Vercel production + preview domains.
- The token lives as an HF Space **secret** (env var), never in the repo or the frontend bundle.

*Fallback for stronger gating:* serve the SPA from the Space itself and make the Space
HF-account-private — simplest privacy, but drops the separate Vercel frontend.

## 8. Data sync & deploy

- New Make target **`make deploy-data`**: copy fresh `data/processed/*.parquet` into the
  Space repo working tree and `git push` it. The Docker Space rebuilds/restarts and
  serves the new data. `make analyze` is untouched.
- **Frontend** deploys via Vercel's Git integration (push to `master` → production;
  PRs → preview URLs).
- The Space repo holds: `Dockerfile`, the FastAPI app, and `data/processed/*.parquet`.

## 9. Rollout phases

1. **Backend up:** FastAPI + DuckDB Space serving §6 endpoints over the committed Parquet,
   with token gate + CORS. Verify each endpoint returns correct rows.
2. **Frontend shell:** scaffold Vite + React on Vercel; data-fetch layer + token prompt +
   in-memory cache; render the manifest/switcher with no charts yet.
3. **Port charts** one-by-one to JS, parity-checked against the current `report.html`.
4. **Wire interactivity:** masthead switcher, §0 band, context-breakdown toggles.
5. **Lock down:** CORS to the Vercel domain, token secret, `make deploy-data`.
6. **Cut over:** share the Vercel URL; keep `echarts_report.py` as a fallback exporter
   until parity is confirmed, then retire it from the default `make analyze` path.

## 10. Risks

- **Chart-parity drift:** re-expressing `echarts_report.py` configs in JS risks subtle
  visual/numeric differences. Mitigation: port one chart at a time, diff against the
  current report on the same data before moving on.
- **HF Space idle-sleep (48 h):** first hit after a long idle is slow (container wake).
  Acceptable for an internal dashboard; Cloud Run fallback removes it if needed.
- **Token-in-localStorage** is coarse access control (anyone with the token + URL gets
  in). Fine for a few trusted teammates; revisit if the audience widens.
- **CORS/preview domains:** Vercel preview URLs are dynamic; either allow the
  `*.vercel.app` preview pattern or restrict to production only.

## 11. Out of scope (future phases)

- Serving the 706 MB raw trajectories for drill-down → Cloudflare R2 (10 GB + zero-egress
  free tier) + DuckDB range reads or per-run blobs. Not in this build.
- Real auth provider / per-user accounts (Firebase Auth or Cloud Run + IAP) — only if the
  audience grows beyond a few teammates.
- Statistical/analytical changes — this is a delivery/hosting refactor, not a metrics change.
