# Report Frontend SPA — Plan 2d-ii (§3 Context Breakdown) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the §3 drilldown: add the **Context Source Breakdown** stacked-bar chart per run block — three compose modes (`/context` 7 buckets · `source` 14 categories · `token` 3 buckets), an optional inverted **cache-hit-rate overlay** line, request grouping via `orderedRequests`, and a **clickable** context-text panel (lazy `/api/component-texts`). This is the last piece; after it the SPA reproduces `report.html` end to end.

**Architecture:** Builds on 2d-i. Bucket maps + breakdown aggregation are ported pure from `echarts_report.py:1822-1896`; `contextOption` from `:2011-2045`. `EChart` gains an optional `onClick`. A `ContextTextPanel` lazily fetches `/api/component-texts?run_id=` once per run and resolves the clicked segment's text (key `run|reqIndex|component` or `run|*|component` for stable). `Section3` renders the breakdown chart + panel under each block; the existing compose/group/cache-hit controls drive it. Pure functions TDD'd.

**Tech Stack:** echarts ^6 (bar+line registered), React 18, TS, Vitest. Node 18.

**Truth:** `analysis/echarts_report.py`. **Data:** `/api/components` (loaded), `/api/turns` (loaded), `/api/component-texts` (lazy).

## Global Constraints

- Frontend owns aggregation (P2); cite `echarts_report.py:<lines>`.
- **Compose modes** (`echarts_report.py:1822-1896`):
  - `context`: from `components.est_tokens`; bucket map → System prompt/System tools/MCP tools/Custom agents/Memory files/Skills/Messages; order `['System prompt','System tools','MCP tools','Custom agents','Memory files','Skills','Messages']`; colors `{System prompt:#3b5bdb, System tools:#0c8599, MCP tools:#15aabf, Custom agents:#f76707, Memory files:#2f9e44, Skills:#7048e8, Messages:#495057}`; `clickable:false`.
  - `source`: from `components.est_tokens`; identity bucket; order = the 14 categories (verbatim list below); colors = `SOURCE_COLORS` (already in `web/src/theme.ts`); `clickable:true`.
  - `token`: from `turns`; per turn 4 contributions — `input_tokens`→'input', `cache_read`→'cache read', `cache_creation_5m`→'cache write', `cache_creation_1h`→'cache write'; order `['input','cache read','cache write']`; colors `{input:#3b5bdb,'cache read':#0c8599,'cache write':#e8590c}`; `clickable:false`.
  - The `/context` bucket map (verbatim): base system prompt→System prompt; builtin tool definitions→System tools; MCP / extension tool definitions→MCP tools; custom agent definitions→Custom agents; auto memory→Memory files; CLAUDE.md / project instructions→Memory files; skills listing→Skills; everything else→Messages.
- **Stacked bars** keyed by request position: `data = o.indexes.map(pos => byKey.get(`${pos}:${bucket}`) ?? 0)`; `stack:'context'`. Buckets rendered in `mode.order` filtered to those present.
- **Cache-hit overlay** (toggle = the existing `hitrate` checkbox): line on `yAxisIndex:1`, name "prefix cache hit rate", color `#f03e3e`, `connectNulls`, symbol circle size 4; right axis `valueAxis({min:0,max:100,inverse:true,splitLine:{show:false}})` (100% at bottom). Per position: `100*cache_read/promptTokens(turn)` or null when `promptTokens<=0`. (`echarts_report.py:1976-2010`.)
- **Click→text** (source mode only): clicking a bar segment fetches/uses `/api/component-texts?run_id=` for the run, keyed `run|reqIndex|component` (volatile) or `run|*|component` (stable row); panel shows component, request #, type, est tokens, bytes + truncated flag, and the text. (`echarts_report.py:1803-1817,2048-2055`.)
- The §3 controls (compose/group/cache-hit) are the existing 2a `useState` — drive `mode`/`group`/`showHit`. TS strict; ASCII-only; reuse `ordered`/`agentSymbols`/`format`/`echartsTheme`/`theme`.

## File Structure

| File | Responsibility |
|---|---|
| `web/src/charts/contextBreakdown.ts` | `COMPOSE_MODES`, `breakdownData(...)`, `hitRateData(...)` |
| `web/src/charts/contextOption.ts` | `contextOption(bd, o, showHit, hitData)` |
| `web/src/components/EChart.tsx` | (modify) optional `onClick` prop |
| `web/src/components/ContextTextPanel.tsx` | lazy `/api/component-texts` + render `.ctx-text-panel` |
| `web/src/components/Section3.tsx` | (modify) breakdown chart + panel per block |

---

### Task 1: Compose modes + breakdown aggregation

**Files:** Create `web/src/charts/contextBreakdown.ts`, `web/src/charts/contextBreakdown.test.ts`.

**Interfaces (port of `echarts_report.py:1822-1896`):**
- `ComposeMode = { key:'context'|'source'|'token'; bucketOf:(c:string)=>string|null; order:string[]; colors:Record<string,string>; clickable:boolean }`.
- `COMPOSE_MODES: Record<'context'|'source'|'token', ComposeMode>`.
- `Breakdown = { buckets:string[]; byKey:Map<string,number>; colors:Record<string,string>; clickable:boolean }`.
- `breakdownData(mode: ComposeMode, rowsForRun: Turn[], componentsForRun: Component[]): Breakdown` — positions are indices into `rowsForRun` (`pos` ↔ `rowsForRun[pos].request_index`); for `token` mode read `rowsForRun`, else read `componentsForRun` mapping `request_index`→pos; `byKey` keyed `${pos}:${bucket}`; `buckets = mode.order.filter(b => present)`.
- `hitRateData(rowsForRun: Turn[], o: Ordered): (number|null)[]` — `o.indexes.map(pos => { const t=rowsForRun[pos]; const ctx=promptTokens(t); return ctx>0 ? 100*n(cache_read)/ctx : null })`.

- [ ] **Step 1: Write the failing test** — `web/src/charts/contextBreakdown.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import type { Component, Turn } from '../types';
import { breakdownData, COMPOSE_MODES, hitRateData } from './contextBreakdown';
import { orderedRequests } from './ordered';
import { AGENT_TYPE_ORDER } from './agentSymbols';

const rows = [
  { request_index: 0, request_type: 'main-agent', input_tokens: 10, cache_read: 30, cache_creation_5m: 5, cache_creation_1h: 5 },
  { request_index: 1, request_type: 'main-agent', input_tokens: 0, cache_read: 50, cache_creation_5m: 0, cache_creation_1h: 0 },
] as unknown as Turn[];
const comps = [
  { run_id: 'a', request_index: 0, component: 'base system prompt', est_tokens: 100 },
  { run_id: 'a', request_index: 0, component: 'user input', est_tokens: 20 },
  { run_id: 'a', request_index: 1, component: 'builtin tool definitions', est_tokens: 40 },
] as unknown as Component[];

describe('breakdownData', () => {
  it('context mode buckets components by /context map, keyed by position', () => {
    const bd = breakdownData(COMPOSE_MODES.context, rows, comps);
    expect(bd.byKey.get('0:System prompt')).toBe(100); // base system prompt
    expect(bd.byKey.get('0:Messages')).toBe(20); // user input -> Messages
    expect(bd.byKey.get('1:System tools')).toBe(40); // builtin tool definitions
    expect(bd.buckets).toEqual(['System prompt', 'System tools', 'Messages']); // present, in order
  });
  it('token mode reads turns: input/cache read/cache write', () => {
    const bd = breakdownData(COMPOSE_MODES.token, rows, []);
    expect(bd.byKey.get('0:input')).toBe(10);
    expect(bd.byKey.get('0:cache read')).toBe(30);
    expect(bd.byKey.get('0:cache write')).toBe(10); // 5m + 1h
  });
});

describe('hitRateData', () => {
  it('computes 100*cache_read/promptTokens per position', () => {
    const o = orderedRequests(new Map(rows.map((_, i) => [i, 'main-agent'])), rows.map((_, i) => i), 'all', 'none', AGENT_TYPE_ORDER);
    const h = hitRateData(rows, o);
    expect(h[0]).toBeCloseTo(60); // 100*30/(10+30+5+5)=60
    expect(h[1]).toBeCloseTo(100); // 100*50/50
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/charts/contextBreakdown.test.ts`.

- [ ] **Step 3: Implement `web/src/charts/contextBreakdown.ts`**

```ts
import type { Component, Turn } from '../types';
import type { Ordered } from './ordered';
import { promptTokens } from './cacheTimeline';
import { SOURCE_COLORS } from '../theme';

export interface ComposeMode {
  key: 'context' | 'source' | 'token';
  bucketOf: (c: string) => string | null;
  order: string[];
  colors: Record<string, string>;
  clickable: boolean;
}
const n = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

const CONTEXT_BUCKET: Record<string, string> = {
  'base system prompt': 'System prompt',
  'builtin tool definitions': 'System tools',
  'MCP / extension tool definitions': 'MCP tools',
  'custom agent definitions': 'Custom agents',
  'auto memory': 'Memory files',
  'CLAUDE.md / project instructions': 'Memory files',
  'skills listing': 'Skills',
};
const SOURCE_ORDER = [
  'base system prompt', 'builtin tool definitions', 'MCP / extension tool definitions',
  'custom agent definitions', 'CLAUDE.md / project instructions', 'skills listing',
  'invoked skill bodies', 'auto memory', 'hooks / system reminders', 'user input',
  'assistant / conversation history', 'tool results / file reads', 'subagent summaries', 'uncategorized context',
];
const TOKEN_BUCKET: Record<string, string> = {
  'input tokens': 'input', 'prefix cache read': 'cache read',
  'prefix cache write 5m': 'cache write', 'prefix cache write 1h': 'cache write',
};

export const COMPOSE_MODES: Record<'context' | 'source' | 'token', ComposeMode> = {
  context: {
    key: 'context', bucketOf: (c) => CONTEXT_BUCKET[c] ?? 'Messages',
    order: ['System prompt', 'System tools', 'MCP tools', 'Custom agents', 'Memory files', 'Skills', 'Messages'],
    colors: { 'System prompt': '#3b5bdb', 'System tools': '#0c8599', 'MCP tools': '#15aabf', 'Custom agents': '#f76707', 'Memory files': '#2f9e44', Skills: '#7048e8', Messages: '#495057' },
    clickable: false,
  },
  source: { key: 'source', bucketOf: (c) => c, order: SOURCE_ORDER, colors: SOURCE_COLORS, clickable: true },
  token: {
    key: 'token', bucketOf: (c) => TOKEN_BUCKET[c] ?? null,
    order: ['input', 'cache read', 'cache write'],
    colors: { input: '#3b5bdb', 'cache read': '#0c8599', 'cache write': '#e8590c' },
    clickable: false,
  },
};

export interface Breakdown {
  buckets: string[]; byKey: Map<string, number>; colors: Record<string, string>; clickable: boolean;
}

export function breakdownData(mode: ComposeMode, rowsForRun: Turn[], componentsForRun: Component[]): Breakdown {
  const byKey = new Map<string, number>();
  const add = (pos: number, bucket: string | null, tokens: number) => {
    if (bucket == null) return;
    byKey.set(`${pos}:${bucket}`, (byKey.get(`${pos}:${bucket}`) ?? 0) + tokens);
  };
  if (mode.key === 'token') {
    rowsForRun.forEach((t, pos) => {
      add(pos, 'input', n(t.input_tokens));
      add(pos, 'cache read', n(t.cache_read));
      add(pos, 'cache write', n(t.cache_creation_5m) + n(t.cache_creation_1h));
    });
  } else {
    const posOf = new Map<number, number>();
    rowsForRun.forEach((t, i) => posOf.set(t.request_index, i));
    for (const c of componentsForRun) {
      const pos = posOf.get(c.request_index);
      if (pos == null) continue;
      add(pos, mode.bucketOf(c.component), n(c.est_tokens));
    }
  }
  const buckets = mode.order.filter((b) => [...byKey.keys()].some((k) => k.endsWith(`:${b}`)));
  return { buckets, byKey, colors: mode.colors, clickable: mode.clickable };
}

export function hitRateData(rowsForRun: Turn[], o: Ordered): (number | null)[] {
  return o.indexes.map((pos) => {
    const t = rowsForRun[pos];
    if (!t) return null;
    const ctx = promptTokens(t);
    return ctx > 0 ? (100 * n(t.cache_read)) / ctx : null;
  });
}
```

- [ ] **Step 4: Run → pass + build.** `cd web && npx vitest run src/charts/contextBreakdown.test.ts && npm run build`.

- [ ] **Step 5: Commit.**
```bash
git add web/src/charts/contextBreakdown.ts web/src/charts/contextBreakdown.test.ts
git commit -m "feat(web): context-breakdown compose modes + aggregation + hit-rate data"
```

---

### Task 2: Context-breakdown option builder + EChart onClick

**Files:** Create `web/src/charts/contextOption.ts`, `web/src/charts/contextOption.test.ts`; modify `web/src/components/EChart.tsx`, `web/src/components/EChart.test.tsx`.

**Interfaces:**
- `contextOption(bd: Breakdown, o: Ordered, showHit: boolean, hitData: (number|null)[]): EChartsOption` — port `echarts_report.py:2011-2045`: `barSeries = bd.buckets.map(b => ({ name:b, type:'bar', stack:'context', xAxisIndex:0, yAxisIndex:0, data:o.indexes.map(pos => bd.byKey.get(`${pos}:${b}`) ?? 0), itemStyle:{color: bd.colors[b] ?? '#868e96'} }))`; when `showHit`, append the hit line series (`yAxisIndex:1`, `#f03e3e`, connectNulls, symbol circle 4) and use 2-element `yAxis` (tokens; inverted hit axis 0–100); `xAxis: groupedXAxis(o)`; `bottomLegend(showHit ? buckets.concat(['prefix cache hit rate']) : buckets)`; `grid:{left:74,right: showHit?60:24, top:48, bottom:66}`; `tooltip:{...TOOLTIP, trigger:'axis'}`.
- `EChart` gains `onClick?: (p: { seriesName: string; dataIndex: number }) => void` — registers `chart.on('click', ...)` (after `chart.off('click')`), re-registered when `onClick` changes.

- [ ] **Step 1: Write the failing contract test** — `web/src/charts/contextOption.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import type { Turn } from '../types';
import { breakdownData, COMPOSE_MODES, hitRateData } from './contextBreakdown';
import { orderedRequests } from './ordered';
import { AGENT_TYPE_ORDER } from './agentSymbols';
import { contextOption } from './contextOption';

const rows = [
  { request_index: 0, request_type: 'main-agent', input_tokens: 10, cache_read: 30, cache_creation_5m: 0, cache_creation_1h: 0 },
] as unknown as Turn[];
const o = orderedRequests(new Map([[0, 'main-agent']]), [0], 'all', 'none', AGENT_TYPE_ORDER);

describe('contextOption', () => {
  it('stacked bars per bucket; adds hit overlay + inverted axis when showHit', () => {
    const bd = breakdownData(COMPOSE_MODES.token, rows, []);
    const noHit = contextOption(bd, o, false, []) as any;
    expect(noHit.series.every((s: any) => s.type === 'bar' && s.stack === 'context')).toBe(true);
    expect(Array.isArray(noHit.yAxis) ? noHit.yAxis.length : 1).toBe(1);

    const withHit = contextOption(bd, o, true, hitRateData(rows, o)) as any;
    const hit = withHit.series.find((s: any) => s.name === 'prefix cache hit rate');
    expect(hit.type).toBe('line');
    expect(hit.yAxisIndex).toBe(1);
    expect(withHit.yAxis[1].inverse).toBe(true);
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/charts/contextOption.test.ts`.

- [ ] **Step 3: Implement `web/src/charts/contextOption.ts`** by porting `echarts_report.py:2011-2045` (bar series per bucket; optional hit line + inverted right axis; xAxis groupedXAxis; legend; grid; tooltip). Imports: `baseTextStyle/TOOLTIP/valueAxis/yName/bottomLegend` from `./echartsTheme`, `groupedXAxis`+`Ordered` from `./ordered`, `Breakdown` from `./contextBreakdown`, `import type { EChartsOption } from 'echarts'`. Pure.

- [ ] **Step 4: Add `onClick` to `web/src/components/EChart.tsx`.** Add an optional `onClick?: (p: { seriesName: string; dataIndex: number }) => void` to the props; in a new effect keyed `[onClick]`, if a chart exists, `chart.off('click')` then (if `onClick`) `chart.on('click', (p) => onClick({ seriesName: String(p.seriesName ?? ''), dataIndex: Number(p.dataIndex) }))`. Keep existing behavior. Update `EChart.test.tsx`'s mock instance to include `on: vi.fn()` and `off: vi.fn()` so the new effect doesn't crash the existing tests (the mocked instance needs those methods).

- [ ] **Step 5: Run → pass + build.** `cd web && npx vitest run src/charts/contextOption.test.ts src/components/EChart.test.tsx && npm run build`.

- [ ] **Step 6: Commit.**
```bash
git add web/src/charts/contextOption.ts web/src/charts/contextOption.test.ts web/src/components/EChart.tsx web/src/components/EChart.test.tsx
git commit -m "feat(web): context-breakdown option builder + EChart onClick"
```

---

### Task 3: Context-text panel + wire breakdown into Section3

**Files:** Create `web/src/components/ContextTextPanel.tsx`, `web/src/components/ContextTextPanel.test.tsx`; modify `web/src/components/Section3.tsx`.

**Interfaces:**
- `ContextTextPanel({ runId, selection })` where `selection: { component: string; requestIndex: number; type: string; tokens: number } | null` — on a non-null `selection`, lazily `getComponentTexts(runId)` once per run (cache in state), build a lookup keyed `run|reqIndex|component` (volatile) / `run|*|component` (stable, from `row.stable`), resolve `selection`, and render the `.ctx-text-panel` markup (head: component, `request #${requestIndex+1}`, type, `${fmt(tokens)} est tokens`, `${fmt(bytes)} bytes` + truncated flag; body: text or "No captured text" empty state). When `selection` is null, render the default `.ctx-empty` prompt.
- `Section3` block: also render `<h3 className="drill-sub">Context Source Breakdown</h3>`, `<EChart className="chart tall" option={contextOption(bd, ordered, showHit, hitData)} onClick={mode.clickable ? (p)=>setSel[run](...) : undefined} />`, and `<ContextTextPanel runId={run.run_id} selection={selForRun} />`, where `bd = breakdownData(mode, rowsForRun, componentsForRun)`, `componentsForRun = components.filter(c => c.run_id===run.run_id)`, `hitData = showHit ? hitRateData(rowsForRun, ordered) : []`, `mode = COMPOSE_MODES[compose]`, `showHit = hitrate` (existing checkbox state). On click (source mode), set a per-run `selection` from the clicked segment: `requestIndex = rowsForRun[ordered.indexes[p.dataIndex]].request_index`, `component = p.seriesName`, `type/tokens` from that row + `bd.byKey`. Section3 needs a `components: Component[]` prop.

- [ ] **Step 1: Write the failing test for ContextTextPanel** — `web/src/components/ContextTextPanel.test.tsx`

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import * as client from '../api/client';
import { ContextTextPanel } from './ContextTextPanel';

afterEach(() => { vi.restoreAllMocks(); });

describe('ContextTextPanel', () => {
  it('shows the default prompt when nothing is selected', () => {
    render(<ContextTextPanel runId="a" selection={null} />);
    expect(screen.getByText(/click a stacked segment/i)).toBeInTheDocument();
  });
  it('lazily fetches and shows the selected component text (stable key)', async () => {
    vi.spyOn(client, 'getComponentTexts').mockResolvedValue([
      { run_id: 'a', request_index: 0, component: 'base system prompt', request_type: 'main-agent', text: 'SYS', truncated: false, bytes: 3, stable: true },
    ] as never);
    render(<ContextTextPanel runId="a" selection={{ component: 'base system prompt', requestIndex: 5, type: 'main-agent', tokens: 100 }} />);
    await waitFor(() => expect(screen.getByText('SYS')).toBeInTheDocument()); // resolved via run|*|component (stable)
    expect(client.getComponentTexts).toHaveBeenCalledWith('a');
  });
});
```

- [ ] **Step 2: Run → fail.** `cd web && npx vitest run src/components/ContextTextPanel.test.tsx`.

- [ ] **Step 3: Implement `web/src/components/ContextTextPanel.tsx`**

```tsx
import { useEffect, useState } from 'react';
import { getComponentTexts } from '../api/client';
import type { ComponentText } from '../types';
import { fmt } from '../charts/format';

export interface CtxSelection { component: string; requestIndex: number; type: string; tokens: number }

export function ContextTextPanel({ runId, selection }: { runId: string; selection: CtxSelection | null }) {
  const [texts, setTexts] = useState<ComponentText[] | null>(null);

  useEffect(() => {
    let live = true;
    if (selection && texts === null) {
      getComponentTexts(runId).then((rows) => { if (live) setTexts(rows); }).catch(() => { if (live) setTexts([]); });
    }
    return () => { live = false; };
  }, [selection, runId, texts]);

  if (!selection) {
    return <div className="ctx-text-panel"><div className="ctx-empty">Click a stacked segment above to view the text captured for that context part.</div></div>;
  }
  const lookup = new Map<string, ComponentText>();
  for (const r of texts ?? []) {
    lookup.set(r.stable ? `${r.run_id}|*|${r.component}` : `${r.run_id}|${r.request_index}|${r.component}`, r);
  }
  const entry = lookup.get(`${runId}|${selection.requestIndex}|${selection.component}`) ?? lookup.get(`${runId}|*|${selection.component}`);
  return (
    <div className="ctx-text-panel">
      <div className="ctx-head">
        <b>{selection.component}</b>
        <span>request #{selection.requestIndex + 1}</span>
        <span>{selection.type}</span>
        <span>{fmt(selection.tokens)} est tokens</span>
        {entry && <span>{fmt(entry.bytes)} bytes{entry.truncated ? <span className="ctx-trunc"> &middot; preview truncated</span> : null}</span>}
      </div>
      {entry && entry.text
        ? <pre className="ctx-body">{entry.text}</pre>
        : <div className="ctx-empty">{texts === null ? 'Loading…' : 'No captured text for this part (it may be externalized or empty).'}</div>}
    </div>
  );
}
```

- [ ] **Step 4: Run → pass.** `cd web && npx vitest run src/components/ContextTextPanel.test.tsx`.

- [ ] **Step 5: Wire into `web/src/components/Section3.tsx`.** Add a `components: Component[]` prop. Track per-run selection: `const [sel, setSel] = useState<Record<string, CtxSelection | null>>({})`. Compute `mode = COMPOSE_MODES[compose] ?? COMPOSE_MODES.context` and `showHit = hitrate`. Inside the per-run block (after the cost-timeline `EChart` from 2d-i), add:
```tsx
                const componentsForRun = components.filter((c) => c.run_id === run.run_id);
                const bd = breakdownData(mode, rowsForRun, componentsForRun);
                const hitData = showHit ? hitRateData(rowsForRun, ordered) : [];
                // ...
                <h3 className="drill-sub">Context Source Breakdown</h3>
                <EChart
                  className="chart tall"
                  option={contextOption(bd, ordered, showHit, hitData)}
                  onClick={mode.clickable ? (p) => {
                    const pos = ordered.indexes[p.dataIndex];
                    const row = rowsForRun[pos];
                    if (!row) return;
                    setSel((s) => ({ ...s, [run.run_id]: { component: p.seriesName, requestIndex: row.request_index, type: String(row.request_type ?? 'main-agent'), tokens: bd.byKey.get(`${pos}:${p.seriesName}`) ?? 0 } }));
                  } : undefined}
                />
                <ContextTextPanel runId={run.run_id} selection={sel[run.run_id] ?? null} />
```
Wire imports: `breakdownData`/`hitRateData`/`COMPOSE_MODES` from `../charts/contextBreakdown`, `contextOption` from `../charts/contextOption`, `ContextTextPanel` + `CtxSelection` from `./ContextTextPanel`, `Component` from `../types`. Update `App.tsx` to pass `components={data.components}` to Section3 (the DataProvider already loads `components`). The compose/group/hitrate `<select>`/checkbox already update `compose`/`group`/`hitrate` state from 2a.

- [ ] **Step 6: Update `web/src/components/Section3.charts.test.tsx`** to pass the new `components={[]}` prop in its render call (and confirm it still asserts the cost-timeline blocks — now each block has 2 charts: cost timeline + breakdown, so update `getAllByTestId('echart')` length from 2 to 4 for 2 runs, or assert on `.drilldown-run` count instead). Keep it green.

- [ ] **Step 7: Run → full suite + build.** `cd web && npm test && npm run build`.

- [ ] **Step 8: Commit.**
```bash
git add web/src/components/ContextTextPanel.tsx web/src/components/ContextTextPanel.test.tsx web/src/components/Section3.tsx web/src/components/Section3.charts.test.tsx web/src/App.tsx
git commit -m "feat(web): §3 context-source breakdown chart + clickable text panel"
```

---

## Done = SPA reproduces report.html
After this plan, all of §0–§3 render: masthead/switcher, §0 brief band, KPI band, §1 (matrix/comparison/overhead/quality-cost), §2 (cache lines/hit-vs-context), §3 (cost timeline + context breakdown + text panel). Remaining polish (pixel brackets, chart-width bar-density, §0 prompt-text box needing a backend `page` field) is tracked, not blocking.
