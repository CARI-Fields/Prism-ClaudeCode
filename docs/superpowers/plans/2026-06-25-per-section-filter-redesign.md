# Per-section filter redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement this plan. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replace the report's single global sidebar filter with per-section filter strips (global Task; per-section Feature/Rollout/Agent), so each filter dimension visibly scopes only the section it affects.

**Architecture:** All changes are in `analysis/echarts_report.py` (the SPA emitted as one HTML string). The global `sel` object becomes a scoped `SEL = {task, s1, s2, s3}`; `active()` gains a scope arg; each render function reads its section's scope; §3 stacks the runs its own strip selects.

**Tech Stack:** Python (string template) + embedded vanilla JS + ECharts. Verification: `node --check`, Python re-render off `data/processed/*.parquet`, stubbed `node` logic sims.

## Global Constraints

- Single file: `analysis/echarts_report.py`. No parquet/pipeline changes.
- Retain "empty set = show all" fallback for every dimension.
- Agent rows keep dynamic present-type scoping; Agent default = all present selected.
- §3 default = first feature × all rollouts.
- URL persists only `report` + global `task`.
- Internal data keys unchanged (`condition`/`rep`/`request_type`); only UI labels are Feature/Rollout.

---

### Task 1: Spec the new behavior as a runnable sim (the "failing test")

**Files:** Create `scratchpad/sel-sim.js` (throwaway, outside repo) — the executable spec for the SEL logic.

- [ ] **Step 1:** Write `sel-sim.js` defining `SEL`, `taskActive`, `active(scope,dim,val)`, `presentAgentTypes(scope)`, `runsFor(scope)`, `seedDefaults()` against a fake `EXPERIMENT_DATA` (real shapes), asserting:
  - default: `SEL.task={coding}`, `s1.condition`=all, `s2`=all+present-agents, `s3.condition`={firstFeature}, `s3.rep`=all, `s3.agent`=present.
  - `runsFor('s3')` default = first feature × all rollouts (count = #rollouts).
  - `active('s2','condition',x)` size-0 → all; deselect-all fallback holds per scope.
  - `presentAgentTypes('s3')` reflects only the s3 condition/rep scope.
  - changing `SEL.task` propagates to every `*For` selector.
- [ ] **Step 2:** `node scratchpad/sel-sim.js` → all assertions print PASS. This is the contract Task 3 must satisfy.

---

### Task 2: DOM — remove sidebar, add global Task strip + per-section strips

**Files:** Modify `analysis/echarts_report.py` (the HTML template region + CSS).

- [ ] **Step 1:** Delete the `<aside class="sidebar">…</aside>` block. Remove `.sidebar`/`.app` two-column layout CSS; make `<main>` full width.
- [ ] **Step 2:** Add a global Task strip just below the masthead: `<div class="fstrip" id="strip-task"><span class="fstrip-label">Task</span><div class="chips" id="chips-task"></div></div>`.
- [ ] **Step 3:** Add per-section strips at the top of each band:
  - §1: `chips-s1-condition` (label "Feature").
  - §2: `chips-s2-condition`, `chips-s2-rep` (label "Rollout"), `chips-s2-agent`.
  - §3: `chips-s3-condition`, `chips-s3-rep`, `chips-s3-agent` + move the existing `run-scale`/`compose-filter`/`group-filter`/`hitrate-toggle` controls into the §3 strip (remove them from the panel/band heads where they now sit).
  - Each strip gets a per-dim "all" reset (`ftoggle` with `data-scope`+`data-toggle`).
- [ ] **Step 4:** Add `.fstrip` CSS (horizontal flex chip bar, sticky optional) consistent with existing `.chip`/`.control inline`.
- [ ] **Step 5:** Verify: `grep` confirms `chips-task`, `chips-s{1,2,3}-*` present and `class="sidebar"` gone.

---

### Task 3: State model + chips — scoped SEL, active(scope,…), per-strip build/sync/seed

**Files:** Modify `analysis/echarts_report.py` (JS region).

- [ ] **Step 1:** Replace `const sel = {...}` with `const SEL = {task:new Set(), s1:{condition:new Set()}, s2:{condition:new Set(),rep:new Set(),agent:new Set()}, s3:{condition:new Set(),rep:new Set(),agent:new Set()}}`.
- [ ] **Step 2:** Add `taskActive(t)` and change `active(scope,dim,val)`; update `selectedTasks`→`taskActive`, add `conditionsFor(scope)`.
- [ ] **Step 3:** `presentAgentTypes(scope)` filters turns by `taskActive` + `SEL[scope].condition/rep`. Add `runsFor(scope)` / `turnsFor(scope)`.
- [ ] **Step 4:** Per-strip chip build (`renderChipGroup(scope,dim,values)`), `syncChips()` (reads `data-scope`+`data-dim`), and `seedDefaults()` per the spec. Agent rows rebuild+reseed when their scope's task/feature/rollout changes.
- [ ] **Step 5:** Chip/`ftoggle` click handlers read `data-scope`; mutate `SEL[scope][dim]`; if changed dim ≠ agent for that scope, rebuild that scope's agent chips; then re-render only the affected section(s).
- [ ] **Step 6:** Port the Task 1 sim functions verbatim-equivalent into the file; re-run `node scratchpad/sel-sim.js` against the in-file logic copy → PASS.

---

### Task 4: Wire each render function to its scope; remove dead global code

**Files:** Modify `analysis/echarts_report.py` (JS region).

- [ ] **Step 1:** §1 renders (`renderKpis`,`renderMatrix`,`renderConditionChart`,`renderOverheadChart`,`renderEfficiencyChart`) read `taskActive`+`active('s1','condition',…)`. `renderMatrix` no longer filters by rep (coverage map: all rollouts).
- [ ] **Step 2:** §2 renders (`renderCacheChart`/`renderCacheChartFor`,`renderLatencyChart`) read `taskActive`+`active('s2',…)`.
- [ ] **Step 3:** §3: `refreshDrilldown` uses `runsFor('s3')`; per-run agent scope uses `active('s3','agent',…)`/`singleAgent('s3')`.
- [ ] **Step 4:** `renderAll` calls each section's renders; per-strip change handlers call only that section's render subset. `activateReport`/`initCharts` reset `SEL` via `seedDefaults`, build all strips. Remove `buildSidebar`/`refreshAgentChips`/global reset/`sel`.
- [ ] **Step 5:** `writeURL`/`readURL` persist `report` + `task` only.

---

### Task 5: Verify end-to-end

- [ ] **Step 1:** Python re-render off `data/processed/*.parquet` → "RENDER OK".
- [ ] **Step 2:** Extract the app `<script>` (the one containing `seedDefaults`) → `node --check` → "JS SYNTAX OK".
- [ ] **Step 3:** Stubbed node sim of orchestration: Task switch updates all sections; §1 ignores rollout; §2 honors all four; `runsFor('s3')` default = first-feature × all-rollouts; per-scope size-0 fallback.
- [ ] **Step 4:** `grep` shows no residual `\bsel\b`/`buildSidebar`/`refreshAgentChips`/`class="sidebar"`/`getElementById("run-filter")`.
- [ ] **Step 5:** Report the browser-eyeball checklist to the user (strips above sections, each drives only its own charts, §3 stacks first-feature×rollouts, Task switch global).

---

## Self-Review

- **Spec coverage:** Task→spec mapping — DOM/layout (T2), SEL+active+seeds+dynamic-agent (T3), per-section render wiring + matrix-all-reps + §3 runsFor + URL (T4), verification plan (T1,T5). All spec sections covered.
- **Placeholder scan:** none (verification is concrete commands; code model lives in the spec + ported sim).
- **Type consistency:** `active(scope,dim,val)`, `taskActive(t)`, `runsFor(scope)`, `presentAgentTypes(scope)`, `singleAgent(scope)`, `SEL[scope][dim]` used consistently across tasks.
