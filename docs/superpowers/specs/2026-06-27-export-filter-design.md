# Filterable export picker (design)

Date: 2026-06-27
Status: approved (pending spec review)
Scope: `web/app` frontend only (export dialog UX)

## 1. Context

The trace-export feature (merged) puts a per-run checklist in a TopBar Export
dialog (`web/app/src/export/RunPicker.tsx`): a flat list of every run with a
checkbox, a select-all, an "include raw context text" switch, and a Download
button (calls `useExportDownload`). With ~30 runs the flat list is workable but
slow to scan. The app already has the building blocks to filter:
`components/shell/RailFilterGroup.tsx` (a reusable label + interactive `Tag`
chip-group with per-group "clear" and an optional color dot), `data/filters.ts`
`scopeRuns(runs, task[], {condition, rep, agent})`, and `theme.conditionColor`.

## 2. Goal

Let users quickly find the runs they want to export by **filtering the run list
inside the dialog** — modeled on the existing rail filter UI — with selection
that persists as they change filters.

## 3. Decisions (locked)

- **Local filters in the dialog** (not the global rail; not seeded from it).
- Filter controls: **Task**, **Feature** (condition), **Rollout** (rep) chip
  groups (reusing `RailFilterGroup`) + a **text search** box.
- **Agent excluded** (it's a per-request dimension, not per-run).
- Selection is a `Set<run_id>` that **persists across filter changes**
  (filter → select → re-filter → select more, accumulating).
- **Select-all acts on the currently visible (filtered) runs.**
- Frontend only; the export endpoint/format is unchanged.

## 4. Behavior

- A **filter bar** sits above the run list: the three chip groups + a search
  `InputGroup`. Chip groups are multi-select with a per-group clear; the search
  narrows by case-insensitive substring across `run_id`, `task`, `condition`,
  and `r<rep>`.
- The list shows only **visible** runs = `filterRuns(runs, filter)`.
- **Select-all** (a checkbox labeled `Select all shown (M)`, M = visible count)
  selects every visible run; clicking again when all visible are selected
  deselects the visible ones. `indeterminate` when some-but-not-all visible are
  selected. Hidden/disabled when nothing is visible.
- The header shows **`N selected`** (N = total selected across all filters).
- Footer unchanged: "Include raw context text" switch + Download. Download sends
  **all selected** run_ids in run order (unchanged `orderedSelected` logic), so
  selections made under earlier filters are still exported.
- Empty filter result → a `No runs match` note; Download stays disabled at 0
  selected.

## 5. Components (small, testable units)

- **`export/filterRuns.ts`** — pure helper:
  `interface RunFilter { task: string[]; condition: string[]; rep: string[]; query: string }`
  and `filterRuns(runs: Run[], f: RunFilter): Run[]` =
  `scopeRuns(runs, f.task, { condition: f.condition, rep: f.rep, agent: [] })`
  then a substring filter on `query` (empty query → no-op). Reuses `scopeRuns`.
- **`export/RunFilterBar.tsx`** — presentational: three `RailFilterGroup`s
  (Task / Feature[dotFor=conditionColor] / Rollout) + a Blueprint `InputGroup`
  search. Props: domain arrays + active arrays + `onToggle(dim, token)` /
  `onClear(dim)` + `query` / `onQuery`. Derives nothing; `RunPicker` owns state.
- **`export/RunPicker.tsx`** (modified) — owns the `RunFilter` state, derives the
  domains (distinct sorted `task` / `condition` / `r<rep>` from `data.runs`),
  computes `visible = filterRuns(runs, filter)`, renders `RunFilterBar` + the
  visible list + select-all-of-visible + the `N selected` count + the existing
  footer. `selected: Set<run_id>` persists (keyed by id, unaffected by filtering).
- **`theme/tokens.css`** — a small `.run-filter-bar` layout (the chips reuse the
  existing `.rail-*` classes via `RailFilterGroup`).

## 6. Reuse / no new deps

`RailFilterGroup`, `scopeRuns`, `conditionColor`, Blueprint `InputGroup` — all
already present. No new dependency. Backend untouched.

## 7. Testing

- **`filterRuns.test.ts`** — chip narrowing (task / condition / rep each);
  search substring (matches run_id and task; case-insensitive); combined chips +
  search; empty filter → all runs.
- **`RunFilterBar.test.tsx`** — renders the three groups + search; toggling a
  chip calls `onToggle` with the dim+token; typing calls `onQuery`.
- **`RunPicker.test.tsx`** (extended) — applying a filter hides non-matching
  runs; select-all selects only visible; **selection survives a filter change**
  (select under filter A, switch to filter B, both stay selected and Download
  gets both); search narrows the list; Download still sends all selected in run
  order. Keep the existing two assertions working (download contracts).

## 8. Non-goals

- No change to the global rail, the export endpoint, the zip format, or auth.
- No saved/named filter presets, no URL-encoding of the dialog filter (it's
  ephemeral dialog state). YAGNI.

## 9. Success criteria

- In the Export dialog, a user filters by Task/Feature/Rollout chips and/or text
  search to shrink the list, ticks runs (selection persisting across filter
  changes), and Downloads exactly the accumulated selection. Full frontend suite
  green; build clean.
