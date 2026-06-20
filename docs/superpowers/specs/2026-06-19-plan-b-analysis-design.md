# Plan B — Analysis Pipeline — Design

**Date:** 2026-06-19
**Status:** Draft for review
**Builds on:** Plan A (capture) + Plan A2 (instrumentation), both merged. Consumes `data/raw/<run_id>/`.

## 1. Goal

Turn captured run data into tidy tables, figures, and a report comparing the 5
orchestration conditions. **Headline metric: prefix-cache-hit accumulation.**
Built and tested against the real data we have (2 complete coding cells + the pilot
fixtures + a partial research session), structured to run unchanged on the full 30.

## 2. Headline metric — prefix-cache-hit accumulation (figure 1)

Per request the API `usage` gives `input_tokens` (uncached/computed),
`cache_read_input_tokens` (served from cache = **hit**), `cache_creation_input_tokens`
(written to cache this turn). Over `request_index` within a run:

- **Main curve:** `cumsum(cache_read_input_tokens)` — total tokens served from the
  prefix cache as the session progresses. One line per condition.
- **Companions:** `cumsum(cache_creation_input_tokens)` (writes) and
  `cumsum(input_tokens)` (never-cached), so the figure shows hits vs writes vs cold.
- **Accumulated hit ratio:** `cumsum(cache_read) / cumsum(cache_read + cache_creation
  + input_tokens)`.

This contrast is the core story: single_agent's one growing context keeps hitting a
warm prefix; subagents reset the prefix per child; ralph resets each loop iteration.

## 3. Data sources (grounded in the REAL captured formats)

| Source | Real shape (verified) | Yields |
|---|---|---|
| `tap/<session>.json` | **a LIST of turn objects**, each `{turn, timestamp, duration_ms, model, system, tools, messages, response}`. `usage` is at `turn["response"]["usage"]`. **No `request_id`.** | per-request tokens/cache/duration; component sizes |
| `transcripts/**.jsonl` | nested: parent `<uuid>.jsonl` + `<uuid>/subagents/agent-*.jsonl` (`isSidechain:true`) | agent-role attribution, CC-internal events |
| `ttft/ttft.jsonl` | rows `{request_id, t_send_epoch, prefill_s, ttft_s, total_s, status}` | latency split |
| `run_meta.json` | `{run_id, task, condition, rep, model, started_utc, ended_utc, completion_time_s, success, score, ttft, services, transcripts, tap}` | run-level success/speedup |

**ttft↔tap join (no request_id):** `tap.timestamp` is the request **completion**
time; `ttft.t_send_epoch` is the **start**. So `tap_start = parse(tap.timestamp) −
duration_ms/1000` matches `ttft.t_send_epoch` (nearest within ~0.5s tolerance).
Verified on cell 1.

**Component sizes:** from each tap turn's `system` (text blocks), `tools`, `messages`
— byte sizes directly (blob refs carry `bytes` in some captures; inline text measured
by length), plus token estimates anchored so component tokens sum to the reported
prompt tokens (`input + cache_read + cache_creation`).

**Stale-fixture note:** the pilot fixtures (`tests/fixtures/sample_plain`,
`sample_subagents`) are the OLD `{session, records}` shape. The tap parser targets the
REAL list shape; tests use the captured cells under `data/raw/` (a small committed
sample is copied into `tests/fixtures/real_cell/`).

## 4. Tidy tables (the contract)

- **`turns.parquet`** — one row per API request: `run_id, task, condition, rep,
  request_index, ts_start_epoch, input_tokens, output_tokens, cache_read,
  cache_creation_5m, cache_creation_1h, duration_ms, model` + joined
  `ttft_s, prefill_s, total_s`.
- **`components.parquet`** — one row per (run, request_index, component):
  `component ∈ {system_prompt, tools, messages, other}, bytes, est_tokens`.
- **`runs.parquet`** — one row per run: `task, condition, rep, success, correctness,
  speedup, completion_time_s, num_requests, total_input, total_cache_read,
  total_cache_creation, cache_hit_ratio, peak_prompt_tokens, output_tokens_total`.

## 5. Figures

1. **Prefix-cache-hit accumulation** (§2) — primary; built and verified first.
2. **Context-window growth by component** — stacked area of component tokens over
   `request_index`; small-multiples grid (task × condition).
3. **TTFT / latency** — prefill vs ttft vs total: distributions + per-turn lines
   (real spread already seen: ~3s TTFT, one 128s total).
4. **Success rate** — bar across conditions (coding=kernel correctness;
   research=sections+citations).
5. **Speedup** — bar across conditions (coding; `runs.speedup`).
6. **Cost / efficiency** — derived per-run summary (tokens × price; tokens per success).

Figures → `figures/` (png+pdf). `reports/report.md` stitches figures + a `runs` table.

## 6. Module layout

```
analysis/
  parse/{parse_tap.py, parse_transcript.py, parse_ttft.py, parse_meta.py, tokenizer.py}
  build_tables.py            # walk data/raw → turns/components/runs parquet
  metrics.py                 # cache accumulation, hit ratio, context growth, summaries
  plots/{cache_accumulation.py, context_growth.py, latency.py, success_speedup.py, style.py}
  report.py                  # render reports/report.md from the tables + figures
tests/                       # parser + metric unit tests (against real_cell fixture)
Makefile targets: parse · analyze · report
```

## 7. Build/validation strategy

- Unit-test parsers + metrics against a committed `real_cell` fixture (one captured
  cell) + synthetic tidy tables for the cross-condition metrics.
- `make analyze` builds tables from whatever is in `data/raw/` and renders figures —
  runs on the 2 complete cells now, on all 30 later.
- First deliverable verified end-to-end: the figure-1 cache-accumulation curve on real
  cell data.

## 8. Out of scope (YAGNI)

- Statistical significance beyond mean±std across reps.
- Interactive dashboards.
- Re-deriving server-side exact token counts (component tokens are estimates anchored
  to reported usage).
- Writing real findings/conclusions (needs the full 30-run + research cells; the report
  template + auto-tables are built now, narrative filled after the full run).

## 9. Risks

- **Partial data now:** only 2 coding cells + 1 partial research are real; cross-condition
  and research figures will be sparse until the rate-limit resets and the research cells
  run. The pipeline renders whatever exists.
- **Component token estimate** won't exactly match server counts; used for relative
  composition, anchored to totals.
- **ttft↔tap timestamp join** assumes ≤~0.5s alignment; rows that don't match within
  tolerance are kept with null latency rather than dropped.
