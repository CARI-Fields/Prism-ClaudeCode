# Filterable Export Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local filter bar (Task / Feature / Rollout chips + text search) to the export dialog so users can quickly narrow and pick the runs they want to export, with selection that persists across filter changes.

**Architecture:** A pure `filterRuns` helper (reuses `scopeRuns`) computes the visible runs; a presentational `RunFilterBar` (reuses `RailFilterGroup` + a Blueprint `InputGroup`) renders the controls; `RunPicker` owns the filter state, shows only visible runs, makes select-all act on visible runs, and keeps the selection `Set` independent of filtering. Frontend only.

**Tech Stack:** React 18.3 · TypeScript 5.5 · `@blueprintjs/core` v5 · Vitest.

## Global Constraints

- React 18.3, Blueprint v5, TS 5.5. No new dependencies. Backend untouched.
- Reuse `components/shell/RailFilterGroup.tsx`, `data/filters.ts` `scopeRuns`, and `theme.conditionColor` — do not reimplement them.
- The selection is a `Set<run_id>` that PERSISTS across filter changes (filtering never clears selection). **Select-all acts on the currently visible (filtered) runs.** Download sends **all selected** run_ids in run order (the existing `orderedSelected = runs.map(r=>r.run_id).filter(id=>selected.has(id))` logic).
- Search match: case-insensitive substring over `` `${r.task} ${r.condition} r${r.rep} ${r.run_id}` ``.
- Filter dimensions are Task / Feature(condition) / Rollout(rep) only — **no Agent** (per-request, not per-run).
- Run frontend tests from `web/app/`: single `npx vitest run <path>`; full `npm test`. Commit after every green task.

---

## File Structure

**Created:** `web/app/src/export/filterRuns.ts` (+ `.test.ts`), `web/app/src/export/RunFilterBar.tsx` (+ `.test.tsx`).
**Modified:** `web/app/src/export/RunPicker.tsx` (+ its existing `RunPicker.test.tsx`), `web/app/src/theme/tokens.css` (filter-bar layout).

---

## Task 1: `filterRuns` helper

**Files:**
- Create: `web/app/src/export/filterRuns.ts`
- Create: `web/app/src/export/filterRuns.test.ts`

**Interfaces:**
- Consumes: `scopeRuns(runs, task: string[], sel: { condition; rep; agent })` from `data/filters`; `Run` from `types`.
- Produces: `interface RunFilter { task: string[]; condition: string[]; rep: string[]; query: string }`; `filterRuns(runs: Run[], f: RunFilter): Run[]`.

- [ ] **Step 1: Write the failing test**

`web/app/src/export/filterRuns.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { filterRuns } from './filterRuns';
import type { Run } from '../types';

const runs = [
  { run_id: 'a1', task: 'coding', condition: 'goal', rep: 1 },
  { run_id: 'b2', task: 'research', condition: 'subagents', rep: 2 },
  { run_id: 'c3', task: 'coding', condition: 'subagents', rep: 1 },
] as unknown as Run[];
const EMPTY = { task: [], condition: [], rep: [], query: '' };
const ids = (rs: Run[]) => rs.map((r) => r.run_id);

describe('filterRuns', () => {
  it('returns all runs when the filter is empty', () => {
    expect(ids(filterRuns(runs, EMPTY))).toEqual(['a1', 'b2', 'c3']);
  });
  it('narrows by task / condition / rep chips', () => {
    expect(ids(filterRuns(runs, { ...EMPTY, task: ['coding'] }))).toEqual(['a1', 'c3']);
    expect(ids(filterRuns(runs, { ...EMPTY, condition: ['subagents'] }))).toEqual(['b2', 'c3']);
    expect(ids(filterRuns(runs, { ...EMPTY, rep: ['r2'] }))).toEqual(['b2']);
  });
  it('narrows by case-insensitive search over run_id/task/condition/rep', () => {
    expect(ids(filterRuns(runs, { ...EMPTY, query: 'goal' }))).toEqual(['a1']);
    expect(ids(filterRuns(runs, { ...EMPTY, query: 'A1' }))).toEqual(['a1']);
    expect(ids(filterRuns(runs, { ...EMPTY, query: 'research' }))).toEqual(['b2']);
  });
  it('combines chips and search', () => {
    expect(ids(filterRuns(runs, { ...EMPTY, task: ['coding'], query: 'subagents' }))).toEqual(['c3']);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/app && npx vitest run src/export/filterRuns.test.ts`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

`web/app/src/export/filterRuns.ts`:
```ts
import { scopeRuns } from '../data/filters';
import type { Run } from '../types';

export interface RunFilter {
  task: string[];
  condition: string[];
  rep: string[];
  query: string;
}

export function filterRuns(runs: Run[], f: RunFilter): Run[] {
  const scoped = scopeRuns(runs, f.task, { condition: f.condition, rep: f.rep, agent: [] });
  const q = f.query.trim().toLowerCase();
  if (!q) return scoped;
  return scoped.filter((r) =>
    `${r.task} ${r.condition} r${r.rep} ${r.run_id}`.toLowerCase().includes(q),
  );
}
```

- [ ] **Step 4: Run tests**

Run: `cd web/app && npx vitest run src/export/filterRuns.test.ts` → PASS. Then `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/export/filterRuns.ts web/app/src/export/filterRuns.test.ts
git commit -m "feat(web): filterRuns helper (chips + search)"
```

---

## Task 2: `RunFilterBar` component

**Files:**
- Create: `web/app/src/export/RunFilterBar.tsx`
- Create: `web/app/src/export/RunFilterBar.test.tsx`

**Interfaces:**
- Consumes: `RailFilterGroup` from `components/shell/RailFilterGroup`; `conditionColor` from `theme`; Blueprint `InputGroup`; `RunFilter` from `./filterRuns` (Task 1).
- Produces: `<RunFilterBar domains={{task,condition,rep}} filter={RunFilter} onToggle={(dim,token)=>...} onClear={(dim)=>...} onQuery={(q)=>...} />` where `dim` is `'task'|'condition'|'rep'`.

- [ ] **Step 1: Write the failing test**

`web/app/src/export/RunFilterBar.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RunFilterBar } from './RunFilterBar';

const domains = { task: ['coding', 'research'], condition: ['goal', 'subagents'], rep: ['r1', 'r2'] };
const filter = { task: [], condition: [], rep: [], query: '' };

describe('RunFilterBar', () => {
  it('renders chip groups + search and reports changes', async () => {
    const onToggle = vi.fn(); const onClear = vi.fn(); const onQuery = vi.fn();
    render(<RunFilterBar domains={domains} filter={filter} onToggle={onToggle} onClear={onClear} onQuery={onQuery} />);
    await userEvent.click(screen.getByRole('button', { name: 'coding' }));
    expect(onToggle).toHaveBeenCalledWith('task', 'coding');
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    expect(onToggle).toHaveBeenCalledWith('condition', 'goal');
    await userEvent.click(screen.getByRole('button', { name: 'r2' }));
    expect(onToggle).toHaveBeenCalledWith('rep', 'r2');
    await userEvent.type(screen.getByRole('searchbox', { name: /search runs/i }), 'x');
    expect(onQuery).toHaveBeenCalledWith('x');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/app && npx vitest run src/export/RunFilterBar.test.tsx`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

`web/app/src/export/RunFilterBar.tsx`:
```tsx
import { InputGroup } from '@blueprintjs/core';
import { RailFilterGroup } from '../components/shell/RailFilterGroup';
import { conditionColor } from '../theme';
import type { RunFilter } from './filterRuns';

type Dim = 'task' | 'condition' | 'rep';

interface Props {
  domains: { task: string[]; condition: string[]; rep: string[] };
  filter: RunFilter;
  onToggle: (dim: Dim, token: string) => void;
  onClear: (dim: Dim) => void;
  onQuery: (q: string) => void;
}

export function RunFilterBar({ domains, filter, onToggle, onClear, onQuery }: Props) {
  return (
    <div className="run-filter-bar">
      <RailFilterGroup
        label="Task" items={domains.task} active={filter.task}
        onToggle={(t) => onToggle('task', t)} onClear={() => onClear('task')}
      />
      <RailFilterGroup
        label="Feature" items={domains.condition} active={filter.condition} dotFor={conditionColor}
        onToggle={(t) => onToggle('condition', t)} onClear={() => onClear('condition')}
      />
      <RailFilterGroup
        label="Rollout" items={domains.rep} active={filter.rep}
        onToggle={(t) => onToggle('rep', t)} onClear={() => onClear('rep')}
      />
      <InputGroup
        type="search" leftIcon="search" placeholder="Search runs…" aria-label="Search runs"
        value={filter.query} onChange={(e) => onQuery(e.currentTarget.value)}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

Run: `cd web/app && npx vitest run src/export/RunFilterBar.test.tsx` → PASS. Then `npm test` → green.
> Note: Blueprint `<InputGroup type="search">` renders an `<input type="search">` → ARIA role `searchbox`; the test queries it by role + the `aria-label`. `RailFilterGroup` `Tag`s render `role="button"`; group item names don't collide (task: coding/research, condition: goal/subagents, rep: r1/r2).

- [ ] **Step 5: Commit**
```bash
git add web/app/src/export/RunFilterBar.tsx web/app/src/export/RunFilterBar.test.tsx
git commit -m "feat(web): RunFilterBar (Task/Feature/Rollout chips + search)"
```

---

## Task 3: integrate filtering into `RunPicker`

**Files:**
- Modify: `web/app/src/export/RunPicker.tsx`
- Modify: `web/app/src/export/RunPicker.test.tsx`
- Modify: `web/app/src/theme/tokens.css`

**Interfaces:**
- Consumes: `filterRuns`/`RunFilter` (Task 1); `RunFilterBar` (Task 2); existing `useData`, `useExportDownload`.
- Produces: the enhanced `<RunPicker />` — filter state + visible list + select-all-of-visible + `N selected` count + persistent selection.

- [ ] **Step 1: Update the test** (replace `web/app/src/export/RunPicker.test.tsx`)

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
    { run_id: 'c3', task: 'coding', condition: 'subagents', rep: 1 },
  ] } }),
}));

describe('RunPicker', () => {
  it('selects a run and downloads with the texts flag', async () => {
    render(<RunPicker />);
    const dl = screen.getByRole('button', { name: /download/i });
    expect(dl).toBeDisabled();
    await userEvent.click(screen.getByLabelText(/coding \/ goal \/ r1 · a1/));
    await userEvent.click(screen.getByRole('checkbox', { name: /include raw context text/i }));
    expect(dl).toBeEnabled();
    await userEvent.click(dl);
    expect(download).toHaveBeenCalledWith(['a1'], true);
  });

  it('select-all selects every visible run', async () => {
    render(<RunPicker />);
    await userEvent.click(screen.getByRole('checkbox', { name: /select all shown/i }));
    await userEvent.click(screen.getByRole('button', { name: /download/i }));
    expect(download).toHaveBeenLastCalledWith(['a1', 'b2', 'c3'], false);
  });

  it('a filter hides non-matching runs', async () => {
    render(<RunPicker />);
    await userEvent.click(screen.getByRole('button', { name: 'goal' })); // Feature chip → condition=goal
    expect(screen.getByLabelText(/· a1/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/· b2/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/· c3/)).not.toBeInTheDocument();
  });

  it('search narrows the list', async () => {
    render(<RunPicker />);
    await userEvent.type(screen.getByRole('searchbox', { name: /search runs/i }), 'c3');
    expect(screen.getByLabelText(/· c3/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/· a1/)).not.toBeInTheDocument();
  });

  it('select-all acts on visible runs and selection persists across filter changes', async () => {
    render(<RunPicker />);
    // Filter A: task=research → only b2 visible; select all shown
    await userEvent.click(screen.getByRole('button', { name: 'research' }));
    expect(screen.queryByLabelText(/· a1/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('checkbox', { name: /select all shown/i }));
    // Switch to filter B: clear research, set Feature=goal → only a1 visible; select it
    await userEvent.click(screen.getByRole('button', { name: 'research' })); // toggle off
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    await userEvent.click(screen.getByLabelText(/coding \/ goal \/ r1 · a1/));
    // Download has both (b2 from filter A persisted, a1 from filter B), in run order
    await userEvent.click(screen.getByRole('button', { name: /download/i }));
    expect(download).toHaveBeenLastCalledWith(['a1', 'b2'], false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/app && npx vitest run src/export/RunPicker.test.tsx`
Expected: FAIL (no `select all shown` / `searchbox` / filtering yet).

- [ ] **Step 3: Implement** — replace `web/app/src/export/RunPicker.tsx`:

```tsx
import { useMemo, useState } from 'react';
import { Button, Checkbox, Switch } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useExportDownload } from './useExportDownload';
import { RunFilterBar } from './RunFilterBar';
import { filterRuns } from './filterRuns';
import type { RunFilter } from './filterRuns';

type Dim = 'task' | 'condition' | 'rep';
const EMPTY: RunFilter = { task: [], condition: [], rep: [], query: '' };
const uniqSorted = (xs: string[]): string[] => Array.from(new Set(xs)).sort();

export function RunPicker() {
  const { data } = useData();
  const runs = data?.runs ?? [];
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [includeTexts, setIncludeTexts] = useState(false);
  const [filter, setFilter] = useState<RunFilter>(EMPTY);
  const { download, busy, error } = useExportDownload();

  const domains = useMemo(() => ({
    task: uniqSorted(runs.map((r) => r.task)),
    condition: uniqSorted(runs.map((r) => r.condition)),
    rep: uniqSorted(runs.map((r) => `r${r.rep}`)),
  }), [runs]);
  const visible = useMemo(() => filterRuns(runs, filter), [runs, filter]);

  const toggle = (id: string) =>
    setSelected((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const toggleDim = (dim: Dim, token: string) =>
    setFilter((f) => {
      const cur = f[dim];
      return { ...f, [dim]: cur.includes(token) ? cur.filter((x) => x !== token) : [...cur, token] };
    });
  const clearDim = (dim: Dim) => setFilter((f) => ({ ...f, [dim]: [] }));
  const setQuery = (query: string) => setFilter((f) => ({ ...f, query }));

  const visibleIds = visible.map((r) => r.run_id);
  const allVisibleSelected = visible.length > 0 && visibleIds.every((id) => selected.has(id));
  const someVisibleSelected = visibleIds.some((id) => selected.has(id));
  const toggleAllVisible = () =>
    setSelected((s) => {
      const n = new Set(s);
      if (allVisibleSelected) visibleIds.forEach((id) => n.delete(id));
      else visibleIds.forEach((id) => n.add(id));
      return n;
    });
  // Download all selected, in run order (across all filters).
  const orderedSelected = runs.map((r) => r.run_id).filter((id) => selected.has(id));

  return (
    <div className="run-picker">
      <RunFilterBar domains={domains} filter={filter} onToggle={toggleDim} onClear={clearDim} onQuery={setQuery} />
      <div className="run-picker-head">
        <div className="run-picker-selinfo">
          <Checkbox
            checked={allVisibleSelected}
            indeterminate={someVisibleSelected && !allVisibleSelected}
            disabled={visible.length === 0}
            onChange={toggleAllVisible}
            label={`Select all shown (${visible.length})`}
          />
          <span className="run-picker-count">{selected.size} selected</span>
        </div>
        <Switch
          checked={includeTexts}
          onChange={(e) => setIncludeTexts(e.currentTarget.checked)}
          label="Include raw context text"
          aria-label="Include raw context text"
        />
      </div>
      <div className="run-picker-list">
        {visible.length === 0 && <p className="run-picker-empty">No runs match</p>}
        {visible.map((r) => (
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
.run-filter-bar { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: flex-start; padding-bottom: 12px; margin-bottom: 4px; border-bottom: 1px solid var(--app-line); }
.run-filter-bar .bp5-input-group { min-width: 170px; }
.run-picker-selinfo { display: flex; align-items: center; gap: 12px; }
.run-picker-count { font-family: var(--app-mono); font-size: 11px; color: var(--app-muted); }
.run-picker-empty { margin: 10px 0; color: var(--app-muted); font-family: var(--app-mono); font-size: 12px; }
```

- [ ] **Step 4: Run tests**

Run: `cd web/app && npx vitest run src/export/RunPicker.test.tsx` → PASS (5 tests). Then `npm test` → full suite green. Then `npm run build` → exit 0.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/export/RunPicker.tsx web/app/src/export/RunPicker.test.tsx web/app/src/theme/tokens.css
git commit -m "feat(web): filterable run picker (chips + search, persistent selection)"
```

---

## Self-Review

**Spec coverage:**
- Local filter bar: Task/Feature/Rollout chips + search → Task 2 (`RunFilterBar`), Task 3 (wired). ✓
- Reuse RailFilterGroup/scopeRuns/conditionColor → Task 1 (`scopeRuns`), Task 2 (`RailFilterGroup`, `conditionColor`). ✓
- Filtering logic (chips + substring) → Task 1 (`filterRuns`). ✓
- Visible list; select-all acts on visible; selection persists; `N selected`; download all selected in run order → Task 3 (impl + the persistence test). ✓
- Empty result note; Download disabled at 0 → Task 3. ✓
- Agent excluded → no agent dimension anywhere. ✓
- Backend untouched; no new deps → only `web/app` files. ✓

**Placeholder scan:** No TBD/TODO; all code/test steps complete.

**Type consistency:** `RunFilter { task, condition, rep, query }` defined in Task 1, consumed identically in Tasks 2 & 3. `filterRuns(runs, f)` signature matches between Task 1 (def) and Task 3 (use). `RunFilterBar` props (`domains`, `filter`, `onToggle(dim,token)`, `onClear(dim)`, `onQuery`) match between Task 2 (def) and Task 3 (use). `Dim = 'task'|'condition'|'rep'` consistent across Tasks 2 & 3.
