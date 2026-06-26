# Report Frontend SPA — Plan 2d-i (§3 Cost Timeline) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the §3 "Single run drilldown" **per-run cost-timeline** chart — one block per run (in the §3 Feature×Rollout), each a stacked token bar (input / cache read / cache write 5m / cache write 1h / output) with TTFT + total latency line overlays on a second y-axis — plus the request-ordering/grouping helper (`orderedRequests`) both §3 charts share. (The context-source breakdown + text panel are Plan 2d-ii.)

**Architecture:** Builds on 2c. Frontend owns aggregation (P2): `orderedRequests` (request reordering + agent-type bands/labels) is ported pure from `echarts_report.py:1107-1144`; `costTimelineOption` is ported from `:1732-1795`. `Section3` renders one block (`.drilldown-run`) per filtered run, each mounting the cost-timeline `EChart`; the group/density controls (already in the 2a Section3) drive the options. Pure functions TDD'd; canvas not.

**Tech Stack:** echarts ^6 (tree-shaken; bar+line+graphic registered), React 18, TS, Vitest. Node 18.

**Truth:** `analysis/echarts_report.py` (cited lines). **Data:** `/api/turns` + `/api/runs` (already loaded).

## Global Constraints

- Frontend owns aggregation (P2); cite `echarts_report.py:<lines>`.
- **Per-run blocks:** one `<article class="panel drilldown-run">` per run in `runsFor("s3")` = runs filtered by global `task` + §3 `condition` + §3 `rep`. Block head `${task} / ${condition} / r${rep}` + `.run-tag` = run_id; then an `<h3 class="drill-sub">Per-Run Request Cost Timeline</h3>` + the chart. (`echarts_report.py:1918-1928`.)
- **Cost timeline:** 5 stacked bars `stack:'tokens'` — input `#3b5bdb`, cache read `#0c8599`, cache write 5m `#e8590c`, cache write 1h `#f59f00`, output `#7048e8` (fields `input_tokens/cache_read/cache_creation_5m/cache_creation_1h/output_tokens`); 2 line series on `yAxisIndex:1` — TTFT `#1098ad`, total `#c2255c` (fields `ttft_s/total_s`), symbol per agent type; dual y-axis (left "tokens" min 0, right "seconds" no splitLine); `bottomLegend(['input','cache read','cache write 5m','cache write 1h','output','TTFT','total'])`; x via grouped axis from `orderedRequests`. (`echarts_report.py:1732-1795`.)
- **`orderedRequests(typeByIndex, rawIndexes, at, groupMode, typeOrder)`** (`echarts_report.py:1107-1144`): `grouped = groupMode==='agent' && at==='all'`; when grouped, sort indexes by agent-type rank (`typeOrder.indexOf(type)`, missing→999) then by index; compute contiguous `bands` `{type,startPos,endPos}`, per-band `ordinal` (1..n), `annotate = grouped || at!=='all'`; `xLabels` (band-count at midpoint when annotate, else `#${i+1}\n${type}` with first/last shown) + `showLabel`; `groupAxisLabels` (agent type at band midpoints when annotate).
- **`at` (singleAgent):** `state.s3.agent.length===1 ? state.s3.agent[0] : 'all'`. **groupMode** from the §3 group `<select>` ('agent'|'none').
- **Simplifications (noted, not silent):** the pixel-positioned agent-type **bracket graphics** (`drawGroupBrackets`) are replaced by the x-axis `groupAxisLabels` (agent-type labels at band midpoints) — conveys grouping without per-render pixel math; **bar-density** uses a controlled slider value to set `barMaxWidth` (no chart-width measurement). These are the only intentional deviations.
- Colors/helpers reuse `echartsTheme` + `agentSymbols` + `format`. TS strict; ASCII-only source; tests via `npm test`.

## File Structure

| File | Responsibility |
|---|---|
| `web/src/charts/agentSymbols.ts` | (modify) add `AGENT_TYPE_ORDER` |
| `web/src/charts/ordered.ts` | `orderedRequests(...)` + `Ordered` type + `groupedXAxis(ordered, position)` |
| `web/src/charts/costTimeline.ts` | `costTimelineOption(rows: Turn[], ordered, barMaxWidth)` |
| `web/src/components/Section3.tsx` | (modify) per-run blocks + cost timeline; group/density wired |
| `web/src/App.tsx` | (modify) pass scoped `runs`+`turns` to Section3 |

---

### Task 1: orderedRequests + grouped x-axis

**Files:** Modify `web/src/charts/agentSymbols.ts`; create `web/src/charts/ordered.ts`, `web/src/charts/ordered.test.ts`.

**Interfaces (port of `echarts_report.py:1107-1144`):**
- In `agentSymbols.ts` add `export const AGENT_TYPE_ORDER = Object.keys(REQUEST_TYPE_SYMBOLS);` (the 8 agent types in canonical order).
- `Ordered = { indexes: number[]; bands: { type: string; startPos: number; endPos: number }[]; ordinal: number[]; annotate: boolean; grouped: boolean; xLabels: string[]; showLabel: boolean[]; groupAxisLabels: string[] }`.
- `orderedRequests(typeByIndex: Map<number,string>, rawIndexes: number[], at: string, groupMode: string, typeOrder: string[]): Ordered`.
- `groupedXAxis(o: Ordered, position?: 'bottom'): Record<string, unknown>` — a category axis whose `data` = `o.xLabels`, with `axisLabel` showing only where `o.showLabel`, mono style; reuse `catAxis`.

- [ ] **Step 1: Write the failing test** — `web/src/charts/ordered.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import { orderedRequests } from './ordered';
import { AGENT_TYPE_ORDER } from './agentSymbols';

describe('orderedRequests', () => {
  const typeByIndex = new Map<number, string>([[0, 'main-agent'], [1, 'task-subagent'], [2, 'main-agent']]);

  it('keeps raw order when groupMode=none', () => {
    const o = orderedRequests(typeByIndex, [0, 1, 2], 'all', 'none', AGENT_TYPE_ORDER);
    expect(o.indexes).toEqual([0, 1, 2]);
    expect(o.grouped).toBe(false);
  });
  it('groups by agent type when groupMode=agent and at=all', () => {
    const o = orderedRequests(typeByIndex, [0, 1, 2], 'all', 'agent', AGENT_TYPE_ORDER);
    expect(o.grouped).toBe(true);
    // main-agent (rank 0) before task-subagent (rank 3): indices 0,2 then 1
    expect(o.indexes).toEqual([0, 2, 1]);
    expect(o.bands.map((b) => b.type)).toEqual(['main-agent', 'task-subagent']);
    expect(o.ordinal).toEqual([1, 2, 1]); // per-band ordinals
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/charts/ordered.test.ts`.

- [ ] **Step 3: Add `AGENT_TYPE_ORDER` to `agentSymbols.ts`** (after the maps):
```ts
export const AGENT_TYPE_ORDER = Object.keys(REQUEST_TYPE_SYMBOLS);
```

- [ ] **Step 4: Create `web/src/charts/ordered.ts`** porting `orderedRequests` + a `groupedXAxis` helper:

```ts
import { catAxis } from './echartsTheme';

export interface Ordered {
  indexes: number[];
  bands: { type: string; startPos: number; endPos: number }[];
  ordinal: number[];
  annotate: boolean;
  grouped: boolean;
  xLabels: string[];
  showLabel: boolean[];
  groupAxisLabels: string[];
}

export function orderedRequests(
  typeByIndex: Map<number, string>, rawIndexes: number[], at: string, groupMode: string, typeOrder: string[],
): Ordered {
  const indexes = rawIndexes.slice();
  const grouped = groupMode === 'agent' && at === 'all';
  const rank = (t: string | undefined) => { const k = typeOrder.indexOf(t ?? ''); return k < 0 ? 999 : k; };
  if (grouped) indexes.sort((a, b) => rank(typeByIndex.get(a)) - rank(typeByIndex.get(b)) || a - b);

  const bands: Ordered['bands'] = [];
  indexes.forEach((i, pos) => {
    const t = typeByIndex.get(i) ?? 'main-agent';
    const last = bands[bands.length - 1];
    if (last && last.type === t) last.endPos = pos;
    else bands.push({ type: t, startPos: pos, endPos: pos });
  });

  const ordinal = new Array<number>(indexes.length);
  for (const g of bands) { let n = 1; for (let p = g.startPos; p <= g.endPos; p++) ordinal[p] = n++; }

  const annotate = grouped || at !== 'all';
  const xLabels = new Array<string>(indexes.length).fill('');
  const showLabel = new Array<boolean>(indexes.length).fill(false);
  if (annotate) {
    for (const g of bands) {
      const mid = Math.floor((g.startPos + g.endPos) / 2);
      xLabels[mid] = `${g.endPos - g.startPos + 1}`;
      showLabel[mid] = true;
    }
  } else {
    indexes.forEach((i, pos) => { xLabels[pos] = `#${i + 1}\n${typeByIndex.get(i) ?? 'main-agent'}`; });
    if (indexes.length) { showLabel[0] = true; showLabel[indexes.length - 1] = true; }
  }
  const groupAxisLabels = new Array<string>(indexes.length).fill('');
  if (annotate) for (const g of bands) groupAxisLabels[Math.floor((g.startPos + g.endPos) / 2)] = g.type;

  return { indexes, bands, ordinal, annotate, grouped, xLabels, showLabel, groupAxisLabels };
}

export function groupedXAxis(o: Ordered): Record<string, unknown> {
  return catAxis({
    data: o.xLabels,
    axisLabel: {
      interval: (idx: number) => o.showLabel[idx],
      fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      fontSize: 10,
      color: '#5c6675',
      formatter: (v: string) => v,
    },
  });
}
```

- [ ] **Step 5: Run → pass + build.** `cd web && npx vitest run src/charts/ordered.test.ts && npm run build`.

- [ ] **Step 6: Commit.**
```bash
git add web/src/charts/agentSymbols.ts web/src/charts/ordered.ts web/src/charts/ordered.test.ts
git commit -m "feat(web): orderedRequests grouping + grouped x-axis (port of echarts_report)"
```

---

### Task 2: Cost-timeline option builder

**Files:** Create `web/src/charts/costTimeline.ts`, `web/src/charts/costTimeline.test.ts`.

**Interfaces (port of `echarts_report.py:1732-1795`):**
- `costTimelineOption(rows: Turn[], o: Ordered, barMaxWidth: number): EChartsOption` — `rows` are the run's turns; series data is read in `o.indexes` order (`o.indexes.map(i => rows[i])` — i.e. `rawIndexes` were positions into `rows`). 5 stacked bars + 2 lines as in Global Constraints; `xAxis = groupedXAxis(o)`; dual `yAxis` ([tokens min0, seconds noSplitLine]); `bottomLegend(...)`; bars carry `barMaxWidth`.

> Indexing note: build `rows`-position arrays. In Section3 we pass `rawIndexes = rows.map((_, i) => i)` and a `typeByIndex` keyed by those positions, so `o.indexes` are positions into `rows`. Each series' `data = o.indexes.map(i => field(rows[i]))`.

- [ ] **Step 1: Write the failing contract test** — `web/src/charts/costTimeline.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import type { Turn } from '../types';
import { orderedRequests } from './ordered';
import { AGENT_TYPE_ORDER } from './agentSymbols';
import { costTimelineOption } from './costTimeline';

const rows = [
  { request_index: 0, request_type: 'main-agent', input_tokens: 10, cache_read: 5, cache_creation_5m: 2, cache_creation_1h: 1, output_tokens: 3, ttft_s: 0.5, total_s: 1 },
  { request_index: 1, request_type: 'main-agent', input_tokens: 0, cache_read: 20, cache_creation_5m: 0, cache_creation_1h: 0, output_tokens: 4, ttft_s: 0.4, total_s: 2 },
] as unknown as Turn[];
const o = orderedRequests(new Map(rows.map((_, i) => [i, rows[i].request_type as string])), rows.map((_, i) => i), 'all', 'none', AGENT_TYPE_ORDER);

describe('costTimelineOption', () => {
  it('has 5 stacked bars + 2 latency lines, dual y-axis', () => {
    const opt = costTimelineOption(rows, o, 30) as any;
    const bars = opt.series.filter((s: any) => s.type === 'bar');
    const lines = opt.series.filter((s: any) => s.type === 'line');
    expect(bars).toHaveLength(5);
    expect(lines).toHaveLength(2);
    expect(Array.isArray(opt.yAxis) && opt.yAxis).toHaveLength(2);
    expect(lines.every((l: any) => l.yAxisIndex === 1)).toBe(true);
    const input = bars.find((b: any) => b.name === 'input');
    expect(input.data).toEqual([10, 0]); // in o.indexes (raw) order
    expect(input.itemStyle.color).toBe('#3b5bdb');
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/charts/costTimeline.test.ts`.

- [ ] **Step 3: Implement `web/src/charts/costTimeline.ts`** by porting `renderRunChart()` (`echarts_report.py:1732-1795`) — the 5 stacked bars (names/colors/fields per Global Constraints), the 2 line series (`yAxisIndex:1`, symbol from `REQUEST_TYPE_SYMBOLS[type]`), dual `yAxis` (`valueAxis({...yName('tokens',58), min:0})` and `valueAxis({...yName('seconds',46), splitLine:{show:false}})`), `xAxis: groupedXAxis(o)`, `bottomLegend([...7 names])`, `grid:{left:66,right:24,top:16,bottom:120}`, `tooltip:{...TOOLTIP, trigger:'axis'}`. Series data uses `o.indexes.map(i => rows[i])`. Pass `barMaxWidth` to each bar. Pure function; import helpers from `./echartsTheme`, `REQUEST_TYPE_SYMBOLS` from `./agentSymbols`, `groupedXAxis` from `./ordered`, types from `../types`/`./ordered`, `import type { EChartsOption } from 'echarts'`.

- [ ] **Step 4: Run → pass + build.** `cd web && npx vitest run src/charts/costTimeline.test.ts && npm run build`.

- [ ] **Step 5: Commit.**
```bash
git add web/src/charts/costTimeline.ts web/src/charts/costTimeline.test.ts
git commit -m "feat(web): per-run cost-timeline option builder (port of echarts_report)"
```

---

### Task 3: Per-run blocks in Section3 (cost timeline)

**Files:** Modify `web/src/components/Section3.tsx`, `web/src/App.tsx`; create `web/src/components/Section3.charts.test.tsx`. Also update the existing `Section3`'s local `group`/`density` state to drive the chart.

**Interfaces:**
- `Section3` gains `runs: Run[]` (blocks, scoped) + `turns: Turn[]` (per-block data, scoped). For each run in `runs`, render a `.drilldown-run` block: head (`${task} / ${condition} / r${rep}` + `.run-tag` run_id), `<h3 class="drill-sub">Per-Run Request Cost Timeline</h3>`, and `<EChart className="chart" option={costTimelineOption(rowsForRun, ordered, barMaxWidth)} />`. Build `rowsForRun = turns.filter(t => t.run_id === run.run_id).sort((a,b) => a.request_index - b.request_index)`; `typeByIndex = new Map(rowsForRun.map((t,i) => [i, t.request_type ?? 'main-agent']))`; `ordered = orderedRequests(typeByIndex, rowsForRun.map((_,i)=>i), singleAgent, group, AGENT_TYPE_ORDER)`. `singleAgent = state.s3.agent.length===1 ? state.s3.agent[0] : 'all'`; `barMaxWidth = Math.max(6, Math.round(6 + 40 * density/100))` (density is the existing slider state 0–100).
- `App.tsx` passes `runs={scopeRuns(runs, state.task, state.s3)}` and `turns={scopeTurns(turns, state.task, state.s3)}` to Section3.

- [ ] **Step 1: Write the failing test (mock EChart)** — `web/src/components/Section3.charts.test.tsx`

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { toggleSection } from '../state/appState';
import { initState } from '../state/appState';
import type { Run, Turn } from '../types';

vi.mock('./EChart', () => ({ EChart: ({ className }: { className?: string }) => <div data-testid="echart" className={className} /> }));
import { Section3 } from './Section3';

const variant = { key: 'multi_agent', eyebrow: '', title: '', lede: '', conditions: ['single_agent', 'subagents'], tasks: ['coding'] };
const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1 },
  { run_id: 'b', task: 'coding', condition: 'single_agent', rep: 2 },
] as unknown as Run[];
const turns = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent', request_index: 0, input_tokens: 1, cache_read: 0, cache_creation_5m: 0, cache_creation_1h: 0, output_tokens: 0, ttft_s: 0.1, total_s: 0.2 },
] as unknown as Turn[];

describe('Section3 cost timeline', () => {
  it('renders one block (with a cost-timeline chart) per scoped run', () => {
    render(<Section3 variant={variant} state={initState('multi_agent', ['coding'])} runs={runs} turns={turns} reps={['r1', 'r2']} agentTypes={['main-agent']} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getAllByTestId('echart')).toHaveLength(2); // 2 runs → 2 cost-timeline charts
    expect(screen.getByText('a')).toBeInTheDocument(); // run-tag run_id
    expect(screen.getAllByText('Per-Run Request Cost Timeline')).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/components/Section3.charts.test.tsx`.

- [ ] **Step 3: Modify `web/src/components/Section3.tsx`.** Keep the 2a band/filter-strip/selectors markup (the Feature/Rollout/Agent chips + bar-density slider + compose/group selects + cache-hit checkbox + their local state). Add `runs: Run[]` + `turns: Turn[]` to `Props`. Replace the empty `<div id="drilldown-runs" className="drilldown-runs" />` with a map over `runs`:
```tsx
        <div id="drilldown-runs" className="drilldown-runs">
          {runs.map((run) => {
            const rowsForRun = turns.filter((t) => t.run_id === run.run_id)
              .sort((a, b) => a.request_index - b.request_index);
            const typeByIndex = new Map<number, string>(rowsForRun.map((t, i) => [i, t.request_type ?? 'main-agent']));
            const ordered = orderedRequests(typeByIndex, rowsForRun.map((_, i) => i), singleAgent, group, AGENT_TYPE_ORDER);
            const barMaxWidth = Math.max(6, Math.round(6 + 40 * (density / 100)));
            return (
              <article className="panel drilldown-run" key={run.run_id}>
                <div className="panel-head"><h2>{run.task} / {run.condition} / r{run.rep}</h2><span className="run-tag">{run.run_id}</span></div>
                <h3 className="drill-sub">Per-Run Request Cost Timeline</h3>
                <EChart className="chart" option={costTimelineOption(rowsForRun, ordered, barMaxWidth)} />
              </article>
            );
          })}
        </div>
```
Add `const singleAgent = state.s3.agent.length === 1 ? state.s3.agent[0] : 'all';` near the other derived values. Wire imports: `EChart` from `./EChart`, `orderedRequests` from `../charts/ordered`, `AGENT_TYPE_ORDER` from `../charts/agentSymbols`, `costTimelineOption` from `../charts/costTimeline`, `Run`/`Turn` from `../types`. (`group` and `density` are the existing `useState` from 2a — ensure the group `<select>` value is `group` and the density slider value is `density`, already wired in 2a.)

- [ ] **Step 4: Modify `web/src/App.tsx`** — pass to Section3: `runs={scopeRuns(runs, state.task, state.s3)}` and `turns={scopeTurns(turns, state.task, state.s3)}` (keep the existing reps/agentTypes/onToggle/onClear). `scopeRuns`/`scopeTurns` are already imported.

- [ ] **Step 5: Run → pass + full suite + build.** `cd web && npx vitest run src/components/Section3.charts.test.tsx && npm test && npm run build`.

- [ ] **Step 6: Commit.**
```bash
git add web/src/components/Section3.tsx web/src/components/Section3.charts.test.tsx web/src/App.tsx
git commit -m "feat(web): §3 per-run blocks with cost-timeline chart"
```

---

## Out of scope (Plan 2d-ii)
- The **context-source breakdown** chart per block (3 compose modes /context·source·token + bucket maps, the cache-hit inverted overlay line, group modes) and the **clickable context-text panel** (lazy `/api/component-texts` fetch).
- The pixel-positioned agent-type **bracket graphics** (replaced here by x-axis group labels) and chart-width-measured **bar-density** (replaced by `barMaxWidth` from the slider) — faithful-enough simplifications; revisit only if visual parity demands it.
