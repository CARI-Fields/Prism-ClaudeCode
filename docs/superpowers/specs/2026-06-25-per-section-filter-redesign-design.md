# Per-section filter redesign — `report.html`

**Date:** 2026-06-25
**Scope:** `analysis/echarts_report.py` (the single-page report's filter UI + selection logic). No data-pipeline or parquet changes.

## Problem (first principles)

The report has one **global** filter (`sel = {task, condition, rep, agent}`, sidebar chips) but its four dimensions apply to *different* sections at different altitudes:

| dimension | §1 averages | §2 across-run | §3 drilldown |
|---|---|---|---|
| Task | yes | yes | yes |
| Feature (condition) | yes | yes | yes |
| Rollout (rep) | no (rep-averaged) | yes | yes |
| Agent type | no | yes | yes |

A single global bar whose dimensions have inconsistent scope is the root cause of the recent friction (rollout/agent meaning different things per section; "§3 shows all selected runs = too many"; agent default-all vs click-to-scope tension). The chosen fix is **per-section filter strips**: each section carries only the dimensions it actually uses, so scope is transparent by construction.

## Approved decisions

1. **Layout:** per-section strips (no global sidebar). Full-width content.
2. **Task is global/linked** (one selector shared by all sections); **Feature, Rollout, Agent are per-section independent**.
3. **§3 default** stacks **one feature × all its rollouts** (e.g. 3 runs), not all runs.
4. **Agent default** = all present selected/highlighted, retaining the dynamic "only show agent types present in the current selection" behavior.
5. **"Empty set = show all"** fallback is retained for every dimension.

## Target structure

```
[ masthead + report (variant) switcher ]
[ GLOBAL strip:  Task[coding▾ research]  ]        ← shared by all sections
  §0 task brief
  KPIs (aggregate of Task × §1.Feature)
  §1 Averages   [strip: Feature]
  §2 Across-run [strip: Feature · Rollout · Agent]
  §3 Drilldown  [strip: Feature · Rollout · Agent · compose · group · density]
                one stacked block per run in (Task ∩ §3.Feature ∩ §3.Rollout)
```

- The **global Task strip** sits just below the masthead. Multi-select chips, default = first (coding-type) task.
- **§1 strip:** Feature only. The Experiment matrix becomes a coverage map — it shows **all rollouts** for the selected Task/Feature (no rollout filter in §1). Condition-comparison / Overhead / Quality-cost map stay rep-averaged.
- **§2 strip:** Feature, Rollout, Agent.
- **§3 strip:** Feature, Rollout, Agent + the existing compose-by / group / bar-density / cache-hit controls (moved from the §3 panel heads into the §3 strip). The selected (Feature × Rollout) resolves to the runs that stack.

## Logic model

Replace the single `sel` with a scoped structure:

```js
const SEL = {
  task: new Set(),                                   // global
  s1: { condition: new Set() },
  s2: { condition: new Set(), rep: new Set(), agent: new Set() },
  s3: { condition: new Set(), rep: new Set(), agent: new Set() },
};
const taskActive = t => SEL.task.size === 0 || SEL.task.has(String(t));
const active = (scope, dim, val) => SEL[scope][dim].size === 0 || SEL[scope][dim].has(String(val));
```

- **Section data selectors:** `runsFor(scope)` / `turnsFor(scope)` filter by `taskActive` + that scope's dims.
  - §1 renders (matrix, condition, overhead, efficiency, KPIs) → `taskActive` + `active('s1','condition')` (matrix ignores rollout; the rest are rep-averaged).
  - §2 renders (cache panels, latency) → `taskActive` + `active('s2', …)` over condition/rep/agent.
  - §3 drilldown → runs = `runsFor('s3')` (task ∩ s3.condition ∩ s3.rep); each stacked block scoped by `active('s3','agent', …)`.
- **Chips:** one chip container per (scope, dim): `chips-task`, `chips-s1-condition`, `chips-s2-condition`, `chips-s2-rep`, `chips-s2-agent`, `chips-s3-condition`, `chips-s3-rep`, `chips-s3-agent`. A chip carries `data-scope`, `data-dim`, `data-val`. Click toggles `SEL[scope][dim]`; each strip has its own "all" reset toggle.
- **Dynamic agent chips:** `presentAgentTypes(scope)` filters turns by `taskActive` + that scope's condition/rep, returning only agent types that actually appear. The §2 and §3 agent rows rebuild + reseed (to all-present) when that scope's task/feature/rollout changes (same mechanism as today, now per scope).
- **Default seeds** (`seedDefaults`, run on report activate / variant switch):
  - `task` ← first task.
  - `s1.condition` ← all conditions.
  - `s2.condition` ← all; `s2.rep` ← all; `s2.agent` ← all present (for s2 scope).
  - `s3.condition` ← **first condition only**; `s3.rep` ← all; `s3.agent` ← all present (for s3 scope).
- **`active` size-0 fallback** is unchanged, so clearing any strip's dimension shows all of it.

## Rendering / wiring changes

- `renderMatrix` ignores rollout (shows all reps); all §1 renders read `s1`.
- `renderCacheChartFor` / `renderLatencyChart` read `s2`.
- `refreshDrilldown` uses `runsFor('s3')`; per-run blocks already exist (built this session) — they now follow the §3 strip instead of the global filter. The §3 controls (`compose-filter`, `group-filter`, `run-scale`, `hitrate-toggle`) move into the §3 strip and re-render the drilldown.
- `renderKpis` reads `taskActive` + `s1`.
- Remove the sidebar DOM, the global `sel`, `buildSidebar`/`refreshAgentChips` (replaced by per-strip equivalents), and the single global reset. URL state persists `report` + global `task` only; per-section strips reset to defaults on load (deep-linking per-section is out of scope).

## Out of scope / non-goals

- No change to the analysis pipeline, parquet, or chart *content* (only which data each chart receives).
- No per-section URL deep-linking (only report + global task persisted).
- No new chart types.

## Verification plan

- `node --check` on the extracted app `<script>` (syntax).
- Python re-render off existing parquet (build succeeds).
- Stubbed node simulations for the new logic: (a) `active(scope,…)` size-0 fallback per scope; (b) `presentAgentTypes(scope)` dynamic scoping for s2 vs s3; (c) `runsFor('s3')` default = first-feature × all-rollouts; (d) Task global propagation to all sections.
- Browser eyeball: strips sit above their sections, drive only their own charts, §3 stacks the §3-selected runs, Task switch updates everything.
