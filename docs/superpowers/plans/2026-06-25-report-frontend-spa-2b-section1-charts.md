# Report Frontend SPA — Plan 2b (§1 Charts) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the four §1 "Averages across conditions" charts in the SPA shell — Experiment matrix (heatmap), Condition comparison (bar + metric selector), Overhead vs single agent (bar + resource selector), Quality-vs-cost map (scatter) — by porting the data-shaping and ECharts options from `analysis/echarts_report.py` to TypeScript and mounting them into the existing `#matrix-chart` / `#condition-chart` / `#overhead-chart` / `#efficiency-chart` panels.

**Architecture:** Builds on Plan 2a (the shell). Data-shaping (per-`(task,condition)` metric means, overhead factors vs the `single_agent` baseline, matrix cells) is ported to **pure TS functions** (frontend owns aggregation — P2). Chart **option builders** are pure functions returning ECharts option objects, ported faithfully from the report's JS. A thin imperative **`EChart`** React wrapper mounts/updates/resizes/disposes an ECharts instance. `Section1` lifts its metric/overhead `<select>`s to controlled state, computes the shaped data from the section-scoped runs, and renders the four charts. All pure functions are TDD'd; the wrapper is tested with a mocked `echarts`; charts' canvas rendering is not unit-tested.

**Tech Stack:** echarts ^6 (installed in 2a), React 18, TS, Vitest + RTL. Node 18.

**Layout/behavior truth:** `reports/report.html` + `analysis/echarts_report.py` (cited line ranges below). **Backend contract:** unchanged — uses `/api/runs` already loaded by the shell's `DataProvider`.

## Global Constraints

- **Frontend owns aggregation (P2).** Port the Python/JS logic to TS; do NOT add backend endpoints. Cite the source (`echarts_report.py:<lines>`) in each port.
- **Reproduce the charts faithfully.** Option builders mirror the report's series types, axes, `visualMap`, colors, formatters, grouping, and labels. When in doubt, match `echarts_report.py`.
- **Means skip null/NaN** (not counted as 0); a metric with no finite values is `null` (rendered as a gap / "n/a"). `success` is averaged as 1/0.
- **Condition metrics keys** (exact): `success_rate` + `mean_{completion_time_s,num_requests,cache_hit_ratio,total_cache_read,peak_prompt_tokens,output_tokens_total,total_cost_usd,quality_score,cost_efficiency_score,speedup,research_rubric_score}`, each a mean of the same-named `runs` column.
- **Overhead factor** = condition_mean(field) / `single_agent`_mean(field); `null` if either side null/non-finite or baseline == 0. The overhead panel is **hidden** when `single_agent` is not among the selected conditions.
- **Quality-vs-cost y is task-specific:** coding → `mean_speedup`, research → `mean_research_rubric_score`, else `mean_quality_score`; only the **first selected task** is plotted; dots sized by mean request count.
- **Both-tasks grouping** (condition + overhead bars only): one bar-series per task, colored by `PALETTE` (not condition), no value labels, task legend at bottom; single task → bars colored by condition with value labels.
- **Colors:** `CONDITION_COLORS` (from 2a `theme.ts`); status colors `["#eef1f5","#e03131","#2f9e44","#adb5bd"]` (codes 0–3 = missing/failed/success/skipped); glyphs `["","✗","✓","–"]`; `PALETTE = ["#3b5bdb","#0c8599","#e8590c","#7048e8","#c2255c","#1098ad","#f59f00"]`.
- Tests via `npm test`; every task ends green, output pristine.

## File Structure

| File | Responsibility |
|---|---|
| `web/src/charts/format.ts` | `fmt`, `fmtUsd`, `fmtMetric`, `fmtAxis`, `pct` number formatters |
| `web/src/charts/echartsTheme.ts` | Shared option fragments: `baseTextStyle`, `axisLabelStyle`, `valueAxis`, `catAxis`, `xName`, `yName`, `rightLegend`, `bottomLegend`, `TOOLTIP`; `STATUS_COLORS`, `STATUS_GLYPHS`, `PALETTE` |
| `web/src/charts/conditionMetrics.ts` | `conditionMetrics(runs, tasks, conditions)`, `conditionOverheads(metrics, tasks, conditions)` + their row types |
| `web/src/charts/matrix.ts` | `matrixData(runs, tasks, reps, conditions)` → `{ rows, cols, cells }` |
| `web/src/charts/section1Options.ts` | `matrixOption`, `conditionOption`, `overheadOption`, `efficiencyOption` (pure → ECharts option) |
| `web/src/components/EChart.tsx` | Imperative React wrapper around `echarts.init`/`setOption`/`resize`/`dispose` |
| `web/src/components/Section1.tsx` | (modify) controlled selects + mount the 4 charts + matrix status key |
| `web/src/types.ts` | (modify) add the optional numeric run columns used here (typed, not `unknown`) |

---

### Task 1: Number formatters

**Files:** Create `web/src/charts/format.ts`, `web/src/charts/format.test.ts`.

**Interfaces (port of `echarts_report.py:1064-1081`):**
- `fmt(value: number | null | undefined, digits?: number): string` — `null/NaN → "n/a"`; `|v|≥1e6 → "<v/1e6>M"`; `|v|≥1e3 → "<v/1e3>k"`; else `v.toFixed(digits)` (default digits 1).
- `fmtUsd(value: number | null | undefined): string` — `null → "n/a"`; `<0.01 → $x.xxxx`; `<1 → $x.xxx`; else `$x.xx`.
- `fmtAxis(v: number): string` — `|v|≥1e6 → "<v/1e6>M"` (1 digit); `≥1e3 → "<v/1e3>k"` (0 digits); else `String(v)`.
- `pct(value: number | null | undefined, digits?: number): string` — `null → "n/a"`; else `(v*100).toFixed(digits ?? 0)+"%"`.
- `fmtMetric(value: number | null | undefined, metric: string): string` — if `metric` includes `"cost_usd"` → `fmtUsd`; if includes `"ratio"` or `"rate"` → `pct`; else `fmt`.

- [ ] **Step 1: Write the failing test** — `web/src/charts/format.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import { fmt, fmtAxis, fmtMetric, fmtUsd, pct } from './format';

describe('format', () => {
  it('fmt: n/a, k, M, and digits', () => {
    expect(fmt(null)).toBe('n/a');
    expect(fmt(NaN)).toBe('n/a');
    expect(fmt(1500)).toBe('1.5k');
    expect(fmt(2_300_000)).toBe('2.3M');
    expect(fmt(3.14159, 2)).toBe('3.14');
  });
  it('fmtUsd: variable precision', () => {
    expect(fmtUsd(0.005)).toBe('$0.0050');
    expect(fmtUsd(0.5)).toBe('$0.500');
    expect(fmtUsd(12.3)).toBe('$12.30');
    expect(fmtUsd(null)).toBe('n/a');
  });
  it('pct and fmtAxis', () => {
    expect(pct(0.873)).toBe('87%');
    expect(pct(0.873, 1)).toBe('87.3%');
    expect(fmtAxis(2500)).toBe('2k');
    expect(fmtAxis(42)).toBe('42');
  });
  it('fmtMetric routes by metric name', () => {
    expect(fmtMetric(0.5, 'mean_total_cost_usd')).toBe('$0.500');
    expect(fmtMetric(0.81, 'mean_cache_hit_ratio')).toBe('81%');
    expect(fmtMetric(0.81, 'success_rate')).toBe('81%');
    expect(fmtMetric(5.2, 'mean_num_requests')).toBe('5.2');
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/charts/format.test.ts` → cannot resolve `./format`.

- [ ] **Step 3: Implement** — `web/src/charts/format.ts`

```ts
function finite(v: number | null | undefined): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}
export function fmt(value: number | null | undefined, digits = 1): string {
  if (!finite(value)) return 'n/a';
  const a = Math.abs(value);
  if (a >= 1e6) return `${(value / 1e6).toFixed(digits)}M`;
  if (a >= 1e3) return `${(value / 1e3).toFixed(digits)}k`;
  return value.toFixed(digits);
}
export function fmtUsd(value: number | null | undefined): string {
  if (!finite(value)) return 'n/a';
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}
export function fmtAxis(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(0)}k`;
  return String(v);
}
export function pct(value: number | null | undefined, digits = 0): string {
  if (!finite(value)) return 'n/a';
  return `${(value * 100).toFixed(digits)}%`;
}
export function fmtMetric(value: number | null | undefined, metric: string): string {
  if (metric.includes('cost_usd')) return fmtUsd(value);
  if (metric.includes('ratio') || metric.includes('rate')) return pct(value);
  return fmt(value);
}
```

- [ ] **Step 4: Run → pass.** `cd web && npx vitest run src/charts/format.test.ts` → 4 pass.

- [ ] **Step 5: Commit.**
```bash
git add web/src/charts/format.ts web/src/charts/format.test.ts
git commit -m "feat(web): chart number formatters (port of echarts_report fmt helpers)"
```

---

### Task 2: ECharts theme fragments

**Files:** Create `web/src/charts/echartsTheme.ts` (no test — it's static option fragments + constants exercised by the option-builder tests in Task 5).

**Interfaces (port of `echarts_report.py:999-1009,1054-1062` + the `TT` tooltip base):**
- Constants: `STATUS_COLORS = ['#eef1f5','#e03131','#2f9e44','#adb5bd']`, `STATUS_GLYPHS = ['','✗','✓','–']`, `PALETTE = ['#3b5bdb','#0c8599','#e8590c','#7048e8','#c2255c','#1098ad','#f59f00']`. (`CONDITION_COLORS`/`conditionColor` already live in `web/src/theme.ts` — import from there.)
- CSS color constants mirrored from `:root`: `INK='#10151d'`, `MUTED='#5c6675'`, `LINE='#dde2e9'`, `SANS`/`MONO` font stacks.
- Fragment factories returning plain objects: `baseTextStyle()`, `axisLabelStyle()`, `valueAxis(extra?)`, `catAxis(extra?)`, `xName(name, gap)`, `yName(name, gap)`, `rightLegend(items)`, `bottomLegend(items)`, and a `TOOLTIP` base object (confine + white bg + border + mono text). Use `import type { EChartsOption } from 'echarts'` only where helpful; these factories may return `Record<string, unknown>` to stay flexible.

- [ ] **Step 1: Implement** — `web/src/charts/echartsTheme.ts`

Port the helper factories from `analysis/echarts_report.py:1054-1062` and the `TT` tooltip object (search `const TT =` in that file) faithfully. Use these exact constants:
```ts
export const INK = '#10151d';
export const MUTED = '#5c6675';
export const LINE = '#dde2e9';
export const SANS = "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif";
export const MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";
export const STATUS_COLORS = ['#eef1f5', '#e03131', '#2f9e44', '#adb5bd'];
export const STATUS_GLYPHS = ['', '✗', '✓', '–'];
export const PALETTE = ['#3b5bdb', '#0c8599', '#e8590c', '#7048e8', '#c2255c', '#1098ad', '#f59f00'];

export function baseTextStyle() { return { fontFamily: SANS, color: INK }; }
export function axisLabelStyle() { return { fontFamily: MONO, fontSize: 11, color: MUTED }; }
export const TOOLTIP = {
  confine: true,
  backgroundColor: '#ffffff',
  borderColor: LINE,
  borderWidth: 1,
  padding: [8, 11] as [number, number],
  textStyle: { fontFamily: MONO, fontSize: 12, color: INK },
};
export function valueAxis(extra: Record<string, unknown> = {}) {
  return {
    type: 'value',
    axisLabel: axisLabelStyle(),
    splitLine: { lineStyle: { color: LINE, type: 'dashed' } },
    ...extra,
  };
}
export function catAxis(extra: Record<string, unknown> = {}) {
  return {
    type: 'category',
    axisLabel: axisLabelStyle(),
    axisTick: { show: false },
    axisLine: { lineStyle: { color: LINE } },
    ...extra,
  };
}
export function xName(name: string, gap: number) {
  return { name, nameLocation: 'middle', nameGap: gap, nameTextStyle: { fontFamily: MONO, fontSize: 11, color: MUTED } };
}
export function yName(name: string, gap: number) {
  return { name, nameLocation: 'middle', nameGap: gap, nameRotate: 90, nameTextStyle: { fontFamily: MONO, fontSize: 11, color: MUTED } };
}
export function rightLegend(items: string[]) {
  return { type: 'scroll', orient: 'vertical', right: 6, top: 'middle', data: items, textStyle: { fontFamily: MONO, fontSize: 11, color: MUTED }, icon: 'roundRect' };
}
export function bottomLegend(items: string[]) {
  return { type: 'scroll', bottom: 0, data: items, textStyle: { fontFamily: MONO, fontSize: 11, color: MUTED }, icon: 'roundRect' };
}
```
Cross-check the `TOOLTIP`/legend/axis shapes against `echarts_report.py` and adjust any field you find differs (note differences in the report). These fragments don't need their own test; Task 5 asserts the composed options.

- [ ] **Step 2: Build check.** `cd web && npm run build` → clean (the module type-checks even though nothing imports it yet — acceptable for a constants/fragment module; Task 5 will consume it).

- [ ] **Step 3: Commit.**
```bash
git add web/src/charts/echartsTheme.ts
git commit -m "feat(web): shared ECharts theme fragments + status/palette constants"
```

---

### Task 3: Condition metrics + overheads (data-shaping)

**Files:** Modify `web/src/types.ts` (add optional numeric run columns); create `web/src/charts/conditionMetrics.ts`, `web/src/charts/conditionMetrics.test.ts`.

**Interfaces (port of `echarts_report.py:234-286`):**
- `MetricRow` — `{ task: string; condition: string; runs: number; success_rate: number|null; mean_completion_time_s: number|null; mean_num_requests: number|null; mean_cache_hit_ratio: number|null; mean_total_cache_read: number|null; mean_peak_prompt_tokens: number|null; mean_output_tokens_total: number|null; mean_total_cost_usd: number|null; mean_quality_score: number|null; mean_cost_efficiency_score: number|null; mean_speedup: number|null; mean_research_rubric_score: number|null }`.
- `conditionMetrics(runs: Run[], tasks: string[], conditions: string[]): MetricRow[]` — one row per `(scope, condition)` for `scope ∈ ['all', ...tasks]`.
- `OverheadRow` — `{ task; condition; num_requests_factor; completion_time_factor; total_cost_factor; peak_prompt_tokens_factor; total_cache_read_factor; output_tokens_factor }` (each `number|null`).
- `conditionOverheads(metrics: MetricRow[], tasks: string[], conditions: string[]): OverheadRow[]`.

- [ ] **Step 1: Extend `web/src/types.ts`** — add the optional numeric columns to `Run` (they exist in the parquet; type them instead of relying on the index signature):

Add these fields to the `Run` interface (keep the existing `[key: string]: unknown`):
```ts
  completion_time_s?: number | null;
  cost_efficiency_score?: number | null;
  total_cache_read?: number | null;
  peak_prompt_tokens?: number | null;
  output_tokens_total?: number | null;
```

- [ ] **Step 2: Write the failing test** — `web/src/charts/conditionMetrics.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import type { Run } from '../types';
import { conditionMetrics, conditionOverheads } from './conditionMetrics';

const runs = [
  { task: 'coding', condition: 'single_agent', rep: 1, success: true, num_requests: 4, total_cost_usd: 0.1, quality_score: 2 },
  { task: 'coding', condition: 'single_agent', rep: 2, success: false, num_requests: 6, total_cost_usd: 0.3, quality_score: null },
  { task: 'coding', condition: 'subagents', rep: 1, success: true, num_requests: 8, total_cost_usd: 0.5, quality_score: 3 },
] as unknown as Run[];

describe('conditionMetrics', () => {
  it('means skip nulls; success averaged as 1/0; runs counted', () => {
    const m = conditionMetrics(runs, ['coding'], ['single_agent', 'subagents']);
    const sa = m.find((r) => r.task === 'coding' && r.condition === 'single_agent')!;
    expect(sa.runs).toBe(2);
    expect(sa.mean_num_requests).toBeCloseTo(5);
    expect(sa.success_rate).toBeCloseTo(0.5);
    expect(sa.mean_quality_score).toBeCloseTo(2); // one null skipped
  });
  it('emits an "all" scope aggregating across tasks', () => {
    const m = conditionMetrics(runs, ['coding'], ['single_agent']);
    expect(m.some((r) => r.task === 'all' && r.condition === 'single_agent')).toBe(true);
  });
});

describe('conditionOverheads', () => {
  it('factor = condition mean / single_agent mean; null when no baseline', () => {
    const m = conditionMetrics(runs, ['coding'], ['single_agent', 'subagents']);
    const o = conditionOverheads(m, ['coding'], ['single_agent', 'subagents']);
    const sub = o.find((r) => r.task === 'coding' && r.condition === 'subagents')!;
    expect(sub.num_requests_factor).toBeCloseTo(8 / 5); // 1.6
    const sa = o.find((r) => r.task === 'coding' && r.condition === 'single_agent')!;
    expect(sa.num_requests_factor).toBeCloseTo(1);
    const noBase = conditionOverheads(conditionMetrics(runs, ['coding'], ['subagents']), ['coding'], ['subagents']);
    expect(noBase[0].num_requests_factor).toBeNull();
  });
});
```

- [ ] **Step 3: Run → fail.** `cd web && npx vitest run src/charts/conditionMetrics.test.ts` → cannot resolve.

- [ ] **Step 4: Implement** — `web/src/charts/conditionMetrics.ts`

```ts
import type { Run } from '../types';

export interface MetricRow {
  task: string; condition: string; runs: number;
  success_rate: number | null;
  mean_completion_time_s: number | null; mean_num_requests: number | null;
  mean_cache_hit_ratio: number | null; mean_total_cache_read: number | null;
  mean_peak_prompt_tokens: number | null; mean_output_tokens_total: number | null;
  mean_total_cost_usd: number | null; mean_quality_score: number | null;
  mean_cost_efficiency_score: number | null; mean_speedup: number | null;
  mean_research_rubric_score: number | null;
}
type MeanKey = Exclude<keyof MetricRow, 'task' | 'condition' | 'runs' | 'success_rate'>;

const COLUMN_OF: Record<MeanKey, string> = {
  mean_completion_time_s: 'completion_time_s', mean_num_requests: 'num_requests',
  mean_cache_hit_ratio: 'cache_hit_ratio', mean_total_cache_read: 'total_cache_read',
  mean_peak_prompt_tokens: 'peak_prompt_tokens', mean_output_tokens_total: 'output_tokens_total',
  mean_total_cost_usd: 'total_cost_usd', mean_quality_score: 'quality_score',
  mean_cost_efficiency_score: 'cost_efficiency_score', mean_speedup: 'speedup',
  mean_research_rubric_score: 'research_rubric_score',
};

function num(v: unknown): number | null {
  if (typeof v === 'boolean') return v ? 1 : 0;
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}
function mean(runs: Run[], column: string): number | null {
  const xs: number[] = [];
  for (const r of runs) { const n = num(r[column]); if (n !== null) xs.push(n); }
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
}
function metricRow(task: string, condition: string, runs: Run[]): MetricRow {
  const row = { task, condition, runs: runs.length, success_rate: mean(runs, 'success') } as MetricRow;
  for (const key of Object.keys(COLUMN_OF) as MeanKey[]) row[key] = mean(runs, COLUMN_OF[key]);
  return row;
}
export function conditionMetrics(runs: Run[], tasks: string[], conditions: string[]): MetricRow[] {
  const out: MetricRow[] = [];
  for (const task of ['all', ...tasks]) {
    const taskRuns = task === 'all' ? runs : runs.filter((r) => r.task === task);
    for (const condition of conditions) {
      out.push(metricRow(task, condition, taskRuns.filter((r) => r.condition === condition)));
    }
  }
  return out;
}

export interface OverheadRow {
  task: string; condition: string;
  num_requests_factor: number | null; completion_time_factor: number | null;
  total_cost_factor: number | null; peak_prompt_tokens_factor: number | null;
  total_cache_read_factor: number | null; output_tokens_factor: number | null;
}
function safeFactor(v: number | null, b: number | null): number | null {
  if (v == null || b == null || !Number.isFinite(v) || !Number.isFinite(b) || b === 0) return null;
  return v / b;
}
export function conditionOverheads(metrics: MetricRow[], tasks: string[], conditions: string[]): OverheadRow[] {
  const out: OverheadRow[] = [];
  for (const task of ['all', ...tasks]) {
    const rows = metrics.filter((m) => m.task === task);
    const base = rows.find((m) => m.condition === 'single_agent');
    for (const condition of conditions) {
      const row = rows.find((m) => m.condition === condition);
      const f = (k: MeanKey) => safeFactor(row ? row[k] : null, base ? base[k] : null);
      out.push({
        task, condition,
        completion_time_factor: f('mean_completion_time_s'),
        num_requests_factor: f('mean_num_requests'),
        total_cost_factor: f('mean_total_cost_usd'),
        peak_prompt_tokens_factor: f('mean_peak_prompt_tokens'),
        total_cache_read_factor: f('mean_total_cache_read'),
        output_tokens_factor: f('mean_output_tokens_total'),
      });
    }
  }
  return out;
}
```

- [ ] **Step 5: Run → pass.** `cd web && npx vitest run src/charts/conditionMetrics.test.ts` then `npm run build` → pass + clean.

- [ ] **Step 6: Commit.**
```bash
git add web/src/types.ts web/src/charts/conditionMetrics.ts web/src/charts/conditionMetrics.test.ts
git commit -m "feat(web): condition metrics + overhead factors (port of echarts_report)"
```

---

### Task 4: Matrix data + the EChart wrapper

**Files:** Create `web/src/charts/matrix.ts`, `web/src/charts/matrix.test.ts`, `web/src/components/EChart.tsx`, `web/src/components/EChart.test.tsx`.

**Interfaces:**
- `matrix.ts` (port of `echarts_report.py:175-216`):
  - `MatrixCell = { task: string; condition: string; rep: number; row: string; status: 'missing'|'failed'|'success'|'skipped'; status_code: 0|1|2|3; run_id?: string; num_requests?: number|null; total_cost_usd?: number|null; quality_score?: number|null; completion_time_s?: number|null }`
  - `matrixData(runs, tasks, reps, conditions): { rows: string[]; cols: string[]; cells: MatrixCell[] }` — `rows = tasks×reps` labelled `` `${task} r${rep}` ``; `cols = conditions`; one cell per `(task, rep, condition)`. Status: no run → `missing`; latest run (max `run_id`) `status==='skipped'` → `skipped`; else `success` if `success` truthy else `failed`. Codes `{missing:0,failed:1,success:2,skipped:3}`.
- `EChart.tsx`: `EChart({ option, className }: { option: unknown; className?: string })` — a `<div>` that on mount `echarts.init`s, calls `setOption(option, true)`, re-`setOption` on `option` change, `resize` on window resize, `dispose` on unmount.

- [ ] **Step 1: Write the failing matrix test** — `web/src/charts/matrix.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import type { Run } from '../types';
import { matrixData } from './matrix';

const runs = [
  { run_id: 'a1', task: 'coding', condition: 'single_agent', rep: 1, success: true },
  { run_id: 'a2', task: 'coding', condition: 'single_agent', rep: 1, success: false }, // later run_id wins
  { run_id: 'b1', task: 'coding', condition: 'subagents', rep: 1, success: true },
] as unknown as Run[];

describe('matrixData', () => {
  it('builds rows/cols and resolves status from the latest run', () => {
    const { rows, cols, cells } = matrixData(runs, ['coding'], [1], ['single_agent', 'subagents']);
    expect(rows).toEqual(['coding r1']);
    expect(cols).toEqual(['single_agent', 'subagents']);
    const sa = cells.find((c) => c.condition === 'single_agent' && c.rep === 1)!;
    expect(sa.status).toBe('failed'); // a2 (later) has success=false
    expect(sa.status_code).toBe(1);
  });
  it('marks absent cells missing (code 0)', () => {
    const { cells } = matrixData(runs, ['coding'], [2], ['single_agent']);
    expect(cells[0].status).toBe('missing');
    expect(cells[0].status_code).toBe(0);
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/charts/matrix.test.ts`.

- [ ] **Step 3: Implement** — `web/src/charts/matrix.ts`

```ts
import type { Run } from '../types';

const CODE = { missing: 0, failed: 1, success: 2, skipped: 3 } as const;
type Status = keyof typeof CODE;

export interface MatrixCell {
  task: string; condition: string; rep: number; row: string;
  status: Status; status_code: (typeof CODE)[Status];
  run_id?: string; num_requests?: number | null; total_cost_usd?: number | null;
  quality_score?: number | null; completion_time_s?: number | null;
}

export function matrixData(runs: Run[], tasks: string[], reps: number[], conditions: string[]) {
  const rows: string[] = [];
  for (const task of tasks) for (const rep of reps) rows.push(`${task} r${rep}`);
  const cols = [...conditions];
  const cells: MatrixCell[] = [];
  for (const task of tasks) for (const rep of reps) for (const condition of conditions) {
    const match = runs.filter((r) => r.task === task && r.condition === condition && r.rep === rep);
    const row = `${task} r${rep}`;
    if (match.length === 0) {
      cells.push({ task, condition, rep, row, status: 'missing', status_code: CODE.missing });
      continue;
    }
    const latest = match.slice().sort((a, b) => String(a.run_id).localeCompare(String(b.run_id))).at(-1)!;
    const skipped = String((latest as { status?: unknown }).status ?? '').toLowerCase() === 'skipped';
    const status: Status = skipped ? 'skipped' : latest.success ? 'success' : 'failed';
    cells.push({
      task, condition, rep, row, status, status_code: CODE[status],
      run_id: latest.run_id,
      num_requests: (latest.num_requests as number | null) ?? null,
      total_cost_usd: (latest.total_cost_usd as number | null) ?? null,
      quality_score: (latest.quality_score as number | null) ?? null,
      completion_time_s: (latest.completion_time_s as number | null) ?? null,
    });
  }
  return { rows, cols, cells };
}
```

- [ ] **Step 4: Run → pass.** `cd web && npx vitest run src/charts/matrix.test.ts`.

- [ ] **Step 5: Write the EChart wrapper test (mock echarts)** — `web/src/components/EChart.test.tsx`

```tsx
import { render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const inst = { setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() };
vi.mock('echarts', () => ({ init: vi.fn(() => inst) }));

import * as echarts from 'echarts';
import { EChart } from './EChart';

afterEach(() => { vi.clearAllMocks(); });

describe('EChart', () => {
  it('inits on mount and applies the option', () => {
    render(<EChart option={{ series: [] }} className="chart" />);
    expect(echarts.init).toHaveBeenCalledTimes(1);
    expect(inst.setOption).toHaveBeenCalledWith({ series: [] }, true);
  });
  it('re-applies the option when it changes', () => {
    const { rerender } = render(<EChart option={{ a: 1 }} />);
    rerender(<EChart option={{ a: 2 }} />);
    expect(inst.setOption).toHaveBeenLastCalledWith({ a: 2 }, true);
  });
});
```

- [ ] **Step 6: Run → fail.** `cd web && npx vitest run src/components/EChart.test.tsx`.

- [ ] **Step 7: Implement** — `web/src/components/EChart.tsx`

```tsx
import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export function EChart({ option, className }: { option: unknown; className?: string }) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!elRef.current) return;
    const chart = echarts.init(elRef.current);
    chartRef.current = chart;
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); chart.dispose(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option as echarts.EChartsOption, true);
  }, [option]);

  return <div ref={elRef} className={className ?? 'chart'} />;
}
```

- [ ] **Step 8: Run → pass + build.** `cd web && npx vitest run src/components/EChart.test.tsx && npm run build`.

- [ ] **Step 9: Commit.**
```bash
git add web/src/charts/matrix.ts web/src/charts/matrix.test.ts web/src/components/EChart.tsx web/src/components/EChart.test.tsx
git commit -m "feat(web): matrix data-shaping + imperative EChart wrapper"
```

---

### Task 5: §1 chart option builders

**Files:** Create `web/src/charts/section1Options.ts`, `web/src/charts/section1Options.test.ts`.

**Interfaces — pure functions returning ECharts option objects, ported faithfully from the cited JS. Reproduce the series/axes/visualMap/formatters/colors; consult the report for exact option fields.**
- `matrixOption(m: { rows; cols; cells }): EChartsOption` — port `renderMatrix()` `echarts_report.py:1411-1451` (heatmap; `visualMap.inRange.color = STATUS_COLORS`; `series[0].data = cells.map(c => [colIndex(c.condition), rowIndex(c.row), c.status_code])`; label formatter `STATUS_GLYPHS[code]`; white cell borders).
- `conditionOption(metrics: MetricRow[], conditions: string[], tasks: string[], metric: string, metricLabel: string): EChartsOption` — port `renderConditionChart()` `1453-1481` (bar; grouped when `tasks.length>1` → one series/task, `PALETTE` colors, no labels, bottom legend; else single series colored by `conditionColor`, value labels via `fmtMetric(v, metric)`; yAxis name = `metricLabel`).
- `overheadOption(overheads: OverheadRow[], conditions: string[], tasks: string[], factor: string, factorLabel: string): EChartsOption` — port `renderOverheadChart()` `1488-1518` (bar; same grouping; labels `${fmt(v,2)}×`; first series `markLine` dashed at `yAxis:1` labelled "1.0× baseline"; yAxis `min:0`, name "× vs single_agent").
- `efficiencyOption(metrics: MetricRow[], conditions: string[], task: string): EChartsOption` — port `renderEfficiencyChart()` `1520-1562` (scatter; one series/condition; `[cost, quality, requests, success_rate, cache_hit, cost_eff]`; quality field = `mean_speedup` (coding) / `mean_research_rubric_score` (research) / `mean_quality_score`; `symbolSize = clamp(12, 46, 12 + 34*(requests/maxRequests))`; condition colors `opacity .82`; right legend; only rows with `runs>0 && cost!=null && quality!=null`).

Import helpers from `./echartsTheme` + `./format` + `../theme` (`conditionColor`). Use `import type { EChartsOption } from 'echarts'`.

- [ ] **Step 1: Write the failing test** — assert the structural contract (not pixel output) — `web/src/charts/section1Options.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import { conditionMetrics, conditionOverheads } from './conditionMetrics';
import { matrixData } from './matrix';
import { conditionOption, efficiencyOption, matrixOption, overheadOption } from './section1Options';
import type { Run } from '../types';

const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, success: true, num_requests: 4, total_cost_usd: 0.1, quality_score: 2, speedup: 1.5 },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 1, success: true, num_requests: 8, total_cost_usd: 0.5, quality_score: 3, speedup: 2.0 },
] as unknown as Run[];
const conds = ['single_agent', 'subagents'];

describe('section1 option builders', () => {
  it('matrixOption is a heatmap with status-coded cells + STATUS_COLORS visualMap', () => {
    const opt = matrixOption(matrixData(runs, ['coding'], [1], conds)) as any;
    expect(opt.series[0].type).toBe('heatmap');
    expect(opt.visualMap.inRange.color).toEqual(['#eef1f5', '#e03131', '#2f9e44', '#adb5bd']);
    expect(opt.series[0].data).toHaveLength(2); // 1 row × 2 conds
  });
  it('conditionOption single-task: one bar series, value per condition', () => {
    const m = conditionMetrics(runs, ['coding'], conds);
    const opt = conditionOption(m, conds, ['coding'], 'mean_num_requests', 'Mean requests') as any;
    expect(opt.series).toHaveLength(1);
    expect(opt.series[0].type).toBe('bar');
    expect(opt.series[0].data).toEqual([4, 8]);
  });
  it('overheadOption has a baseline markLine on the first series', () => {
    const m = conditionMetrics(runs, ['coding'], conds);
    const o = conditionOverheads(m, ['coding'], conds);
    const opt = overheadOption(o, conds, ['coding'], 'num_requests_factor', 'Requests') as any;
    expect(opt.series[0].markLine.data[0].yAxis).toBe(1);
  });
  it('efficiencyOption: scatter, coding quality = speedup', () => {
    const m = conditionMetrics(runs, ['coding'], conds);
    const opt = efficiencyOption(m, conds, 'coding') as any;
    expect(opt.series[0].type).toBe('scatter');
    const sub = opt.series.find((s: any) => s.name === 'subagents');
    expect(sub.data[0][1]).toBeCloseTo(2.0); // y = mean_speedup for coding
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/charts/section1Options.test.ts`.

- [ ] **Step 3: Implement `web/src/charts/section1Options.ts`** by porting the four `render*` functions from `analysis/echarts_report.py` (lines cited above) to TS, satisfying the test contract. Build the index maps for the heatmap (`colIndex`/`rowIndex`), the grouped-vs-single bar logic, the overhead `markLine`, and the scatter `symbolSize`/quality-field selection exactly as the report does. Use `baseTextStyle/TOOLTIP/valueAxis/catAxis/xName/yName/rightLegend/bottomLegend/STATUS_COLORS/STATUS_GLYPHS/PALETTE` from `./echartsTheme`, `fmt/fmtUsd/fmtMetric/pct` from `./format`, and `conditionColor` from `../theme`. Keep each builder a pure function of its arguments (read the metric/factor/task from params, never the DOM).

- [ ] **Step 4: Run → pass + build.** `cd web && npx vitest run src/charts/section1Options.test.ts && npm run build`.

- [ ] **Step 5: Commit.**
```bash
git add web/src/charts/section1Options.ts web/src/charts/section1Options.test.ts
git commit -m "feat(web): §1 ECharts option builders (matrix/condition/overhead/efficiency)"
```

---

### Task 6: Wire the charts into Section1

**Files:** Modify `web/src/components/Section1.tsx`; create `web/src/components/Section1.test.tsx`. (Section1 currently receives `{ variant, state, onToggle, onClear }`; this task adds `runs` and renders charts.)

**Interfaces:**
- `Section1` gains a `runs: Run[]` prop (the section-scoped runs). It lifts the metric + overhead `<select>`s to controlled `useState`, computes `conditionMetrics`/`conditionOverheads`/`matrixData` from the runs scoped by global task + `state.s1.condition`, and renders four `<EChart option={…} className="chart" />` plus the matrix status key.
- `App.tsx` passes the scoped runs: `<Section1 … runs={scopeRuns(runs, state.task, state.s1)} />`.

- [ ] **Step 1: Write the failing test (mock EChart to capture options)** — `web/src/components/Section1.test.tsx`

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { initState } from '../state/appState';
import type { Run } from '../types';

vi.mock('./EChart', () => ({ EChart: ({ className }: { className?: string }) => <div data-testid="echart" className={className} /> }));
import { Section1 } from './Section1';

const variant = { key: 'multi_agent', eyebrow: '', title: '', lede: '', conditions: ['single_agent', 'subagents'], tasks: ['coding'] };
const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, success: true, num_requests: 4 },
] as unknown as Run[];

describe('Section1', () => {
  it('renders four charts and the metric/overhead selects', () => {
    render(<Section1 variant={variant} state={initState('multi_agent', ['coding'])} runs={runs} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getAllByTestId('echart')).toHaveLength(4); // matrix/condition/overhead/efficiency
    expect(screen.getByDisplayValue('Mean completion time (s)')).toBeInTheDocument();
  });
  it('hides the overhead panel when single_agent is not selected', () => {
    const noBaseline = { ...variant, conditions: ['subagents', 'dynamic_workflow'] };
    render(<Section1 variant={noBaseline} state={initState('multi_agent', ['coding'])} runs={runs} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getAllByTestId('echart')).toHaveLength(3); // overhead panel gone
  });
  it('metric select is controlled (changing it keeps the new value)', async () => {
    render(<Section1 variant={variant} state={initState('multi_agent', ['coding'])} runs={runs} onToggle={() => {}} onClear={() => {}} />);
    const select = screen.getByDisplayValue('Mean completion time (s)') as HTMLSelectElement;
    await userEvent.selectOptions(select, 'mean_num_requests');
    expect(select.value).toBe('mean_num_requests');
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/components/Section1.test.tsx`.

- [ ] **Step 3: Rewrite `web/src/components/Section1.tsx`** keeping the existing band/filter-strip/panel markup (from 2a) and adding: a `runs: Run[]` prop; `const [metric, setMetric] = useState('mean_completion_time_s')` and `const [overhead, setOverhead] = useState('num_requests_factor')` driving the two `<select value=… onChange=…>` (controlled); `const conds = state.s1.condition.length ? state.s1.condition : variant.conditions` (empty = all); `const tasks = state.task.length ? state.task : variant.tasks`; compute `metrics = useMemo(() => conditionMetrics(runs, tasks, conds), [runs, tasks, conds])`, `overheads = useMemo(() => conditionOverheads(metrics, tasks, conds), …)`, and `reps` from runs; and replace each empty `<div id="…-chart" className="chart" />` with `<EChart className="chart" option={…Option(…)} />`. The matrix uses `matrixData(runs, tasks, reps, conds)`; the metric `<select>`'s label for the y-axis name comes from the selected option's text (keep the METRICS/OVERHEADS arrays). Render the matrix status key (`#matrix-key`) listing success/failed/skipped/missing swatches using `STATUS_COLORS`/`STATUS_GLYPHS` in order `[2,1,3,0]`. Keep the `hasBaseline` gate on the overhead panel.

Wire imports: `EChart`, the four option builders, `conditionMetrics`/`conditionOverheads`, `matrixData`, `STATUS_COLORS`/`STATUS_GLYPHS` from `../charts/echartsTheme`, and `Run` from `../types`.

- [ ] **Step 4: Update `App.tsx`** to pass `runs={scopeRuns(runs, state.task, state.s1)}` to `Section1`. (`scopeRuns` is already imported from 2a.)

- [ ] **Step 5: Run → pass + full suite + build.** `cd web && npx vitest run src/components/Section1.test.tsx && npm test && npm run build`.

- [ ] **Step 6: Visual check (manual, optional).** With the backend running (`make serve` + `make analyze` data), `cd web && npm run dev` and confirm the §1 charts render and the metric/overhead/condition selectors update them. Not required for the task gate.

- [ ] **Step 7: Commit.**
```bash
git add web/src/components/Section1.tsx web/src/components/Section1.test.tsx web/src/App.tsx
git commit -m "feat(web): render §1 charts (matrix/condition/overhead/efficiency) in Section1"
```

---

## Out of scope (later plans)

- **Plan 2c** — §2 charts (per-task cache-accumulation lines, hit-rate-vs-context scatter) + the cache-accumulation/per-agent-timeline data-shaping.
- **Plan 2d** — §3 per-run drilldown (cost timeline) + the context-source breakdown (3 compose modes + component→bucket maps, 2 group modes, bar-density rescale, cache-hit inverted overlay, clickable text panel via `/api/component-texts`).
- ECharts canvas rendering is not unit-tested (jsdom has no canvas); correctness is covered by the pure data-shaping + option-builder contract tests plus the optional manual visual check.
