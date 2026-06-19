# Claude Code Context-Window & Prefix-Cache Experiment — Design

**Date:** 2026-06-18
**Status:** Draft for review
**Root:** `~/experiments/projects/claude-code/`

## 1. Goal & research questions

Measure how the **context window** and the **prefix cache** behave when Claude Code
runs under different **multi-agent orchestration patterns**, using two representative
workloads. Capture the finest-grained tracing data available, then plot and report.

- **RQ1 — Prefix cache:** How does cache-hit accumulate over a session for each
  orchestration pattern? Where does the cached prefix break?
- **RQ2 — Context window:** How does the context window grow, decomposed by
  component (system prompt, tool definitions, message history, file contents,
  tool results), for each pattern?
- **RQ3 — Consequence:** How do the patterns differ in token cost / efficiency as a
  result of RQ1 and RQ2?

## 2. Experimental design

Full factorial, two factors:

- **Factor A — orchestration pattern (5 levels / conditions):**
  1. `single_agent` — one continuous session, no delegation. Baseline: a single
     growing context with one cache lineage.
  2. `subagents` — task that delegates via the Task tool. A main context plus
     isolated subagent contexts, each with its own cache.
  3. `ralph_loop` — external `while` loop invoking `claude -p "<prompt>"`
     repeatedly with a **fresh context each iteration**; progress persisted to disk
     between iterations (the "Ralph" technique).
  4. `dynamic_workflow` — deterministic multi-agent orchestration (Workflow-style):
     many short-lived subagents driven by a script.
  5. `loop_dynamic` — Claude Code's `/loop` in self-paced (no-interval) mode: a
     single session that repeats the task across self-scheduled turns with
     **retained context**. Direct contrast to `ralph_loop` — internal loop + retained
     context vs. external loop + reset context — the sharpest cache contrast in the set.

- **Factor B — task (2 levels):**
  1. `coding` — a bounded coding task over a seed workspace.
  2. `research` — a bounded multi-source research task.

**Design:** 5 × 2 = **10 cells**, **3 repetitions/cell** → **30 runs** (default; revisit
after pilot). Repetitions capture the inherent stochasticity of agent runs.

**Controls held fixed across all conditions:** model (fixed at `claude-sonnet-4-6`),
Claude Code version, machine, MCP/skill/plugin configuration,
task prompts and seed workspaces, network path (all traffic via the same proxy).

## 3. Data sources & capture

Three non-overlapping sources are combined; each contributes data the others lack.

| Source | Unique contribution | Setup |
|---|---|---|
| **claude-tap** (reverse proxy) | Raw request bodies → exact prefix composition (system / tools / messages) per request; lets us diff consecutive requests to locate cache breaks. Redacts auth headers. | Start proxy, route Claude Code through it. |
| **Session JSONL** (`~/.claude/projects/<cwd>/*.jsonl`) | Per-turn `cache_creation_input_tokens` / `cache_read_input_tokens` (+ 5m/1h split), subagent sidechains (`isSidechain`), CC-internal event structure. | Copy session file(s) after each run. |
| **OTEL** (optional) | Aggregated cost + independent cross-check on token totals. | Collector config; off by default. |

**Capture per run:**
1. Bring up `claude-tap` and point Claude Code at it (`harness/env.sh`).
2. Run the (task × condition) workload via its launcher.
3. Copy claude-tap traces, the new session JSONL(s) (incl. sidechains), and optional
   OTEL output into `data/raw/<run_id>/`.
4. Write `run_meta.json`: task, condition, rep, UTC timestamp, Claude Code version,
   model, claude-tap version, OS, harness git sha, env summary.

**Proxy fidelity:** a transparent reverse proxy forwards request bytes unchanged, so
caching is preserved. Validate on a pilot by cross-checking cache token counts from
claude-tap vs. the JSONL.

## 4. Directory structure (Approach A — stage pipeline)

```
claude-code/
├── README.md
├── Makefile                     # setup ▸ run ▸ parse ▸ analyze ▸ report
├── pyproject.toml               # pandas, matplotlib, tokenizer
├── .gitignore                   # ignore data/raw (large); keep figures/ + reports/
├── config/
│   ├── experiment.yaml          # reps, fixed model, seeds, paths (global controls)
│   ├── conditions/{single_agent,subagents,ralph_loop,dynamic_workflow,loop_dynamic}.yaml
│   └── tasks/{coding,research}.yaml
├── tasks/
│   ├── coding/{prompt.md, workspace/}     # workspace git/tar-restored per run
│   └── research/{prompt.md, resources/}
├── harness/
│   ├── runner.py                # drives one (task × condition × rep) run
│   ├── conditions/*.sh          # launch logic per pattern (ralph = while-loop, …)
│   ├── capture/
│   │   ├── start_tap.sh
│   │   ├── collect_transcripts.py
│   │   └── otel/collector.yaml  # optional
│   └── env.sh                   # routes Claude Code through the proxy
├── data/
│   ├── raw/<run_id>/            # tap/  transcripts/  otel/  run_meta.json
│   └── processed/               # turns.parquet  components.parquet  runs.parquet
├── analysis/
│   ├── parse/{parse_tap.py, parse_transcript.py, tokenizer.py}
│   ├── metrics.py               # cache-hit accumulation, context growth, cost
│   └── plots/{cache_accumulation.py, context_growth.py, style.py}
├── figures/                     # committed output plots
├── reports/report.md            # the written analysis
├── docs/superpowers/specs/      # this design doc
└── tests/                       # parser + metric unit tests
```

**Stage boundaries (each independently testable):**
`config` (what to run) → `harness` (capture + launch) → `data/raw` (immutable
captures) → `analysis/parse` (raw → `data/processed` tidy tables) →
`analysis/metrics` + `analysis/plots` → `figures` + `reports`.

## 5. Data model (processed tidy tables)

- **`turns.parquet`** — one row per API request: `run_id, task, condition, rep,
  request_index, ts, model, input_tokens, output_tokens,
  cache_creation_input_tokens, cache_read_input_tokens, cache_creation_5m,
  cache_creation_1h, agent_role (main/subagent id), is_sidechain`.
- **`components.parquet`** — one row per (request × component):
  `run_id, request_index, component, token_count`, where component ∈
  {`system_prompt`, `tool_defs`, `message_history`, `file_contents`,
  `tool_results`, `other`}. Derived by tokenizing the parsed request body.
- **`runs.parquet`** — one row per run: `total_input, total_cache_read,
  total_cache_creation, cache_hit_ratio, peak_context_tokens, total_cost,
  num_requests, num_subagents, wall_time`.

## 6. Metrics & figures

- **Cache-hit accumulation (RQ1):** cumulative `cache_read_input_tokens` (and
  cumulative `cache_creation_input_tokens`) over `request_index`; one panel per task,
  lines colored by condition. Companion: cache-hit ratio per turn.
- **Context-window growth by component (RQ2):** stacked-area of component token
  counts over `request_index`; small-multiples grid (task × condition).
- **Cost / efficiency (RQ3):** per-run cost and tokens-per-unit-progress, mean ± std
  across reps, as a derived summary.

Outputs land in `figures/` (png + pdf) and are referenced from `reports/report.md`.

## 7. Reproducibility

- `run_id = <task>__<condition>__<rep>__<UTC-timestamp>` makes every raw artifact
  traceable to its cell.
- Seed workspace restored to a pristine state before each run.
- Versions pinned: Claude Code, claude-tap, Python deps.
- `Makefile` targets: `setup`, `tap-up`, `run-all`, `run` (single cell), `parse`,
  `analyze`, `report`, `clean`.

## 8. Out of scope (YAGNI)

- Comparing multiple models (model held fixed).
- More than one coding / one research task.
- Real-time dashboards (claude-tap's live viewer suffices for ad hoc inspection).
- Formal significance testing beyond mean ± std across reps.
- CI / automation beyond the Makefile.

## 9. Risks & open questions (resolve in a pilot spike — first implementation step)

1. **Triggering patterns deterministically in headless mode** — confirm the exact
   invocation that reliably induces `subagents`, `ralph_loop`, `dynamic_workflow`,
   and `loop_dynamic` under `claude -p`. `loop_dynamic` and `dynamic_workflow` are
   the least certain to drive headlessly and may need an interactive or scripted
   harness. Highest-uncertainty item.
2. **Proxy fidelity** — confirm claude-tap does not alter requests or caching
   (cross-check tap vs JSONL usage on a pilot run).
3. **Component token counting** — a local tokenizer won't exactly match server-side
   counts; use it for *relative* composition and anchor totals to reported usage.
4. **Repetition count** — 3 reps may be low given stochasticity; revisit after pilot.
5. **Subagent attribution** — verify how subagent usage surfaces in both tap and
   JSONL (sidechain linkage) so `agent_role` can be populated reliably.
```
