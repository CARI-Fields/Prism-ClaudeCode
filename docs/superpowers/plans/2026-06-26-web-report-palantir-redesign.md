# Web Report — Palantir-style Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Apply the `frontend-design:frontend-design` skill on every UI-building task (T7–T13, T16) for aesthetic decisions.

**Goal:** Rebuild the `web/app` report SPA on the Blueprint.js design system as a Palantir-style app-shell — top bar + persistent global filter rail + switchable views (Overview / §1 / §2 / §3) — with light/dark token theming and a global cross-filter that has per-view overrides.

**Architecture:** Big-bang rewrite of `web/app/src/` inside an isolated worktree. Salvage the pure, well-tested modules (`charts/*` option builders, `data/*`, `api/*`, `DataContext`, data interfaces, condition/source hues). Introduce one UI state store (report/view/theme/filter/overrides) exposed through `useTheme`/`useFilter`/`useView`/`useReport` hooks, an extended URL hash, registered ECharts light/dark themes, and a Blueprint component shell. Keep the old components rendering until the shell+views are ready (T14 cutover) so the suite stays green throughout.

**Tech Stack:** Vite 5, React 18.3, TypeScript 5.5, ECharts 6, `@blueprintjs/core`, `@blueprintjs/icons`, Vitest + React Testing Library.

## Global Constraints

- React **18.3.1**, TypeScript **5.5**, Vite **5.4**, ECharts **6.0** — do not bump majors.
- Blueprint: `@blueprintjs/core@^5.10.0` and `@blueprintjs/icons@^5.10.0` (v5 line; CSS namespace `.bp5-`; supports React 18). Do **not** install `@blueprintjs/table` or other sub-packages unless a task says so.
- Backend (`web/api`) is **out of scope** — consume the existing API unchanged.
- Dark mode is the `.bp5-dark` class on the shell root element. Theme **hues** for conditions/sources stay constant across modes (`src/theme.ts`); only neutrals swap.
- All new state reducers are **pure functions** (no mutation, return new objects), mirroring the existing `state/appState.ts` style.
- Tests: run a single file with `npx vitest run <path>`; full suite with `npm test`. Commit after every green task. Component tests select by **role/text**, not `.bp5-*` class names.
- Run all commands from `web/app/` (the Vite project root). The worktree root is `.claude/worktrees/feat+palantir-report-redesign`.

---

## File Structure

**Salvaged unchanged:** `src/api/*`, `src/data/filters.ts`, `src/data/kpis.ts`, `src/data/DataContext.tsx`, `src/charts/*` option builders & helpers (except `echartsTheme.ts`, refactored in T2), `src/theme.ts`, the data interfaces in `src/types.ts`.

**Created:**
- `src/theme/tokens.css` — light/dark CSS custom properties layered over Blueprint vars.
- `src/charts/echartsThemes.ts` — registers `report-light` / `report-dark` ECharts themes.
- `src/state/uiState.ts` — `UiState` + pure reducers + `effectiveSel`.
- `src/state/AppStateProvider.tsx` — single store; `useTheme`/`useFilter`/`useView`/`useReport` hooks; localStorage + URL sync.
- `src/components/shell/AppShell.tsx`, `TopBar.tsx`, `FilterRail.tsx`, `ViewNav.tsx`, `ViewCanvas.tsx`, `RailFilterGroup.tsx`.
- `src/views/OverviewView.tsx`, `Section1View.tsx`, `Section2View.tsx`, `Section3View.tsx`.

**Modified:** `src/charts/echartsTheme.ts` (strip hardcoded neutrals), `src/components/EChart.tsx` (theme-aware), `src/state/urlState.ts` (extend), `src/types.ts` (reshape `AppState`→`UiState` types), `src/components/TokenGate.tsx` + `src/components/ContextTextPanel.tsx` (Blueprint restyle), `src/App.tsx`, `src/main.tsx`.

**Deleted at cutover (T15):** `Masthead.tsx`, `GlobalTaskStrip.tsx`, `KpiBand.tsx`, `BriefBand.tsx`, `Section1.tsx`, `Section2.tsx`, `Section3.tsx`, `Chip.tsx`, `FilterChunk.tsx`, `state/appState.ts`, and their `.test.*` files (logic moved into views/rail or covered by new tests).

---

## Phase 0 — Foundation (theming infrastructure)

### Task 1: Install Blueprint, add token stylesheet

**Files:**
- Modify: `web/app/package.json` (deps)
- Create: `web/app/src/theme/tokens.css`
- Modify: `web/app/src/main.tsx`

**Interfaces:**
- Produces: global CSS — Blueprint base styles + `--app-*` tokens available to all components; `body`/`#root` get a base background from tokens.

- [ ] **Step 1: Install Blueprint**

Run from `web/app/`:
```bash
npm install @blueprintjs/core@^5.10.0 @blueprintjs/icons@^5.10.0
```
Expected: both added to `dependencies`; `npm test` still 72 passing (no source changes yet).

- [ ] **Step 2: Create the token stylesheet**

`web/app/src/theme/tokens.css`:
```css
/* App design tokens, layered on Blueprint. Light is default; .bp5-dark overrides. */
:root {
  --app-bg:        #eceef2;
  --app-panel:     #ffffff;
  --app-ink:       #10151d;
  --app-muted:     #5c6675;
  --app-line:      #dde2e9;
  --app-rail-bg:   #f4f6f9;
  --app-radius:    8px;
  --app-mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  --app-sans: 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.bp5-dark {
  --app-bg:        #1b2027;
  --app-panel:     #252b34;
  --app-ink:       #e7ecf3;
  --app-muted:     #9aa6b4;
  --app-line:      #38404b;
  --app-rail-bg:   #20262e;
}
html, body, #root { height: 100%; }
body { margin: 0; background: var(--app-bg); color: var(--app-ink); font-family: var(--app-sans); }
.app-root { min-height: 100%; background: var(--app-bg); }
```

- [ ] **Step 3: Import Blueprint + tokens in `main.tsx`**

Modify `web/app/src/main.tsx` — add these imports above the existing `./styles.css` import (keep `styles.css` for now; removed at T15):
```ts
import '@blueprintjs/core/lib/css/blueprint.css';
import '@blueprintjs/icons/lib/css/blueprint-icons.css';
import './theme/tokens.css';
```

- [ ] **Step 4: Verify build + tests**

Run: `npm run build` → Expected: succeeds. Run: `npm test` → Expected: 72 passing.

- [ ] **Step 5: Commit**
```bash
git add web/app/package.json web/app/package-lock.json web/app/src/theme/tokens.css web/app/src/main.tsx
git commit -m "feat(web): add Blueprint deps + design-token stylesheet"
```

---

### Task 2: ECharts light/dark themes; strip hardcoded neutrals

**Files:**
- Create: `web/app/src/charts/echartsThemes.ts`
- Create: `web/app/src/charts/echartsThemes.test.ts`
- Modify: `web/app/src/charts/echartsTheme.ts`

**Interfaces:**
- Produces: `registerReportThemes(): void`, `reportThemeName(mode: 'light'|'dark'): string`, exported theme objects `REPORT_LIGHT` / `REPORT_DARK`. After registration, `echarts.init(el, 'report-dark')` is valid. Neutral colors (axis/grid/legend/tooltip/text) come from the registered theme, not from option builders.
- Consumes: `echarts` from `echartsCore`.

- [ ] **Step 1: Write the failing test**

`web/app/src/charts/echartsThemes.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { REPORT_LIGHT, REPORT_DARK, reportThemeName } from './echartsThemes';
import { axisLabelStyle, valueAxis } from './echartsTheme';

describe('report ECharts themes', () => {
  it('names themes by mode', () => {
    expect(reportThemeName('light')).toBe('report-light');
    expect(reportThemeName('dark')).toBe('report-dark');
  });
  it('light and dark differ in neutral surfaces', () => {
    expect(REPORT_LIGHT.backgroundColor).toBe('transparent');
    expect(REPORT_DARK.backgroundColor).toBe('transparent');
    expect(REPORT_LIGHT.textStyle.color).not.toBe(REPORT_DARK.textStyle.color);
    expect(REPORT_LIGHT.valueAxis.splitLine.lineStyle.color)
      .not.toBe(REPORT_DARK.valueAxis.splitLine.lineStyle.color);
  });
  it('builders no longer hardcode neutral colors (theme supplies them)', () => {
    expect('color' in axisLabelStyle()).toBe(false);
    expect(valueAxis().splitLine).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/charts/echartsThemes.test.ts`
Expected: FAIL (module `./echartsThemes` not found; `axisLabelStyle` still has `color`).

- [ ] **Step 3: Create the themes module**

`web/app/src/charts/echartsThemes.ts`:
```ts
import { echarts } from './echartsCore';

const MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

function theme(ink: string, muted: string, line: string, panel: string) {
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: MONO, color: ink },
    categoryAxis: {
      axisLine: { lineStyle: { color: line } },
      axisTick: { show: false },
      axisLabel: { color: muted, fontFamily: MONO, fontSize: 11 },
      splitLine: { show: false },
    },
    valueAxis: {
      axisLabel: { color: muted, fontFamily: MONO, fontSize: 11 },
      splitLine: { lineStyle: { color: line, type: 'dashed' } },
    },
    legend: { textStyle: { color: ink, fontFamily: MONO, fontSize: 11 } },
    tooltip: {
      backgroundColor: panel,
      borderColor: line,
      textStyle: { color: ink, fontFamily: MONO, fontSize: 12 },
    },
  };
}

export const REPORT_LIGHT = theme('#10151d', '#5c6675', '#dde2e9', '#ffffff');
export const REPORT_DARK = theme('#e7ecf3', '#9aa6b4', '#38404b', '#252b34');

export function reportThemeName(mode: 'light' | 'dark'): string {
  return mode === 'dark' ? 'report-dark' : 'report-light';
}

let registered = false;
export function registerReportThemes(): void {
  if (registered) return;
  echarts.registerTheme('report-light', REPORT_LIGHT);
  echarts.registerTheme('report-dark', REPORT_DARK);
  registered = true;
}
```

- [ ] **Step 4: Strip hardcoded neutrals from `echartsTheme.ts`**

Edit `web/app/src/charts/echartsTheme.ts` so the registered theme supplies neutrals. Replace the helper bodies (keep export names; the data **hues** `PALETTE`, `STATUS_COLORS`, `STATUS_GLYPHS` stay):
```ts
import { fmtAxis } from './format';

export const STATUS_COLORS = ['#eef1f5', '#e03131', '#2f9e44', '#adb5bd'];
export const STATUS_GLYPHS = ['', '✗', '✓', '–'];
export const PALETTE = ['#3b5bdb', '#0c8599', '#e8590c', '#7048e8', '#c2255c', '#1098ad', '#f59f00'];
const MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

export function baseTextStyle() { return { fontFamily: MONO }; }
export function axisLabelStyle() { return { fontFamily: MONO, fontSize: 11 }; }
export const TOOLTIP = { confine: true, padding: [8, 11] as [number, number], extraCssText: 'border-radius:8px;' };

export function valueAxis(extra: Record<string, unknown> = {}) {
  return { type: 'value', axisLabel: { ...axisLabelStyle(), formatter: fmtAxis }, ...extra };
}
export function catAxis(extra: Record<string, unknown> = {}) {
  return { type: 'category', axisLabel: axisLabelStyle(), axisTick: { show: false }, ...extra };
}
export function xName(name: string, gap: number) {
  return { name, nameLocation: 'middle', nameGap: gap, nameTextStyle: { fontFamily: MONO, fontSize: 11 } };
}
export function yName(name: string, gap: number) {
  return { name, nameLocation: 'middle', nameGap: gap, nameRotate: 90, nameTextStyle: { fontFamily: MONO, fontSize: 11 } };
}
export function rightLegend(items: string[]) {
  return { type: 'scroll', orient: 'vertical', right: 6, top: 'middle', icon: 'roundRect',
    itemWidth: 14, itemHeight: 9, itemGap: 9, data: items, textStyle: { fontFamily: MONO, fontSize: 11 } };
}
export function bottomLegend(items: string[]) {
  return { type: 'scroll', bottom: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 9, data: items,
    textStyle: { fontFamily: MONO, fontSize: 11 } };
}
```
> Note: `INK`/`MUTED`/`LINE`/`SANS`/`MONO` named exports are removed. If `npx vitest run` or `npm run build` reports any other module importing `INK`/`MUTED`/`LINE` from `echartsTheme`, update that import to drop the color (the registered theme now supplies it). Search first: `grep -rn "from './echartsTheme'" web/app/src` and `grep -rn "INK\|MUTED\|LINE" web/app/src/charts`.

- [ ] **Step 5: Run tests**

Run: `npx vitest run src/charts/echartsThemes.test.ts` → Expected: PASS.
Run: `npm test` → Expected: green. Fix any builder/snapshot test that asserted a removed neutral color by removing that assertion (the color now lives in the theme).

- [ ] **Step 6: Commit**
```bash
git add web/app/src/charts/echartsThemes.ts web/app/src/charts/echartsThemes.test.ts web/app/src/charts/echartsTheme.ts
git commit -m "feat(web): register light/dark ECharts themes; move neutrals out of builders"
```

---

### Task 3: Make `EChart` theme-aware

**Files:**
- Modify: `web/app/src/components/EChart.tsx`
- Modify: `web/app/src/components/EChart.test.tsx`

**Interfaces:**
- Consumes: `useTheme()` is **not yet available** (T6). For this task, add an optional `themeMode?: 'light'|'dark'` prop (default `'light'`); T14 wires it from `useTheme`. `registerReportThemes()` from T2.
- Produces: `<EChart option themeMode? className? onClick? />` re-initializes the chart under `report-<mode>` and disposes/re-inits when `themeMode` changes.

- [ ] **Step 1: Write the failing test**

Replace `web/app/src/components/EChart.test.tsx` with a test that asserts re-init on theme change. Mock `echartsCore`:
```tsx
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { EChart } from './EChart';

const init = vi.fn();
vi.mock('../charts/echartsCore', () => {
  const chart = { setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(), on: vi.fn(), off: vi.fn() };
  return { echarts: { init: (...a: unknown[]) => { init(...a); return chart; }, registerTheme: vi.fn() } };
});

afterEach(() => { cleanup(); init.mockClear(); });

describe('EChart theming', () => {
  it('initializes under the report theme for the active mode', () => {
    render(<EChart option={{}} themeMode="dark" />);
    expect(init).toHaveBeenCalledWith(expect.anything(), 'report-dark');
  });
  it('re-initializes when the theme mode changes', () => {
    const { rerender } = render(<EChart option={{}} themeMode="light" />);
    expect(init).toHaveBeenLastCalledWith(expect.anything(), 'report-light');
    rerender(<EChart option={{}} themeMode="dark" />);
    expect(init).toHaveBeenLastCalledWith(expect.anything(), 'report-dark');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/EChart.test.tsx`
Expected: FAIL (`init` called without a theme arg).

- [ ] **Step 3: Implement theme-aware EChart**

`web/app/src/components/EChart.tsx`:
```tsx
import { useEffect, useRef } from 'react';
import { echarts } from '../charts/echartsCore';
import { registerReportThemes, reportThemeName } from '../charts/echartsThemes';
import type { ECharts } from 'echarts/core';

interface EChartProps {
  option: unknown;
  themeMode?: 'light' | 'dark';
  className?: string;
  onClick?: (p: { seriesName: string; dataIndex: number }) => void;
}

export function EChart({ option, themeMode = 'light', className, onClick }: EChartProps) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECharts | null>(null);

  useEffect(() => {
    if (!elRef.current) return;
    registerReportThemes();
    const chart = echarts.init(elRef.current, reportThemeName(themeMode));
    chartRef.current = chart;
    chart.setOption(option as Parameters<ECharts['setOption']>[0], true);
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); chart.dispose(); chartRef.current = null; };
  }, [themeMode]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    chartRef.current?.setOption(option as Parameters<ECharts['setOption']>[0], true);
  }, [option]);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.off('click');
    if (onClick) chartRef.current.on('click', (p) => onClick({ seriesName: String(p.seriesName ?? ''), dataIndex: Number(p.dataIndex) }));
  }, [onClick]);

  return <div ref={elRef} className={className ?? 'chart'} />;
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/components/EChart.test.tsx` → Expected: PASS.
Run: `npm test` → Expected: green (existing Section chart tests still render via the default `themeMode="light"`).

- [ ] **Step 5: Commit**
```bash
git add web/app/src/components/EChart.tsx web/app/src/components/EChart.test.tsx
git commit -m "feat(web): make EChart theme-aware (re-init on light/dark change)"
```

---

## Phase 1 — State + Shell

### Task 4: UI state model + pure reducers

**Files:**
- Create: `web/app/src/state/uiState.ts`
- Create: `web/app/src/state/uiState.test.ts`
- Modify: `web/app/src/types.ts` (add UI types alongside existing data interfaces)

**Interfaces:**
- Produces:
  - Types (in `types.ts`): `type ViewKey = 'overview'|'s1'|'s2'|'s3'`; `type ThemeMode = 'light'|'dark'`; `interface GlobalFilter { task: string[]; condition: string[]; rep: string[]; agent: string[] }`; `interface UiState { report: string; theme: ThemeMode; view: ViewKey; filter: GlobalFilter; overrides: Partial<Record<ViewKey, Partial<GlobalFilter>>> }`. Keep existing `Run/Turn/Component/ComponentText/Variant/Manifest`. Remove the old `AppState/SectionSel/ScopeKey/Dimension` exports (replaced).
  - Reducers (in `uiState.ts`): `initUiState(report, theme, view?, filter?)`, `setReport`, `setView`, `setTheme`, `toggleFilter(state, dim, token)`, `clearFilter(state, dim)`, `setOverrideSingle(state, view, dim, token)`, and selector `effectiveSel(state, view): SectionSel` where `SectionSel = { condition: string[]; rep: string[]; agent: string[] }` (re-export this name from `uiState.ts` for `data/filters.ts` compatibility).
- Consumes: `data/filters.ts` `scopeRuns/scopeTurns` expect `{condition,rep,agent}` + a separate `task[]`. `effectiveSel` returns the `{condition,rep,agent}` triple; callers pass `state.filter.task` (merged with override task if any) as the `task` arg.

- [ ] **Step 1: Write the failing test**

`web/app/src/state/uiState.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import {
  initUiState, setReport, setView, setTheme, toggleFilter, clearFilter,
  setOverrideSingle, effectiveSel,
} from './uiState';

const base = initUiState('r1', 'light');

describe('uiState reducers', () => {
  it('toggles a global filter dimension', () => {
    const s = toggleFilter(base, 'condition', 'goal');
    expect(s.filter.condition).toEqual(['goal']);
    expect(toggleFilter(s, 'condition', 'goal').filter.condition).toEqual([]);
  });
  it('clears a dimension', () => {
    const s = toggleFilter(base, 'rep', 'r1');
    expect(clearFilter(s, 'rep').filter.rep).toEqual([]);
  });
  it('setReport resets filter, overrides, keeps theme', () => {
    const s = setOverrideSingle(toggleFilter(setTheme(base, 'dark'), 'condition', 'goal'), 's3', 'condition', 'goal');
    const r = setReport(s, 'r2');
    expect(r.report).toBe('r2');
    expect(r.filter.condition).toEqual([]);
    expect(r.overrides).toEqual({});
    expect(r.theme).toBe('dark');
  });
  it('setView and setTheme', () => {
    expect(setView(base, 's2').view).toBe('s2');
    expect(setTheme(base, 'dark').theme).toBe('dark');
  });
  it('§3 Feature override is single-select (replace, re-click clears)', () => {
    let s = setOverrideSingle(base, 's3', 'condition', 'goal');
    expect(s.overrides.s3?.condition).toEqual(['goal']);
    s = setOverrideSingle(s, 's3', 'condition', 'subagents');
    expect(s.overrides.s3?.condition).toEqual(['subagents']);
    s = setOverrideSingle(s, 's3', 'condition', 'subagents');
    expect(s.overrides.s3?.condition).toEqual([]);
  });
  it('effectiveSel merges global filter with per-view override', () => {
    const s = setOverrideSingle(toggleFilter(toggleFilter(base, 'condition', 'goal'), 'rep', 'r1'), 's3', 'condition', 'subagents');
    expect(effectiveSel(s, 's1')).toEqual({ condition: ['goal'], rep: ['r1'], agent: [] });
    expect(effectiveSel(s, 's3')).toEqual({ condition: ['subagents'], rep: ['r1'], agent: [] });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/state/uiState.test.ts` → Expected: FAIL (module not found).

- [ ] **Step 3: Add the UI types to `types.ts`**

Replace the block after the data interfaces (lines 42–49, the old `Dimension/ScopeKey/SectionSel/AppState`) in `web/app/src/types.ts` with:
```ts
export type ViewKey = 'overview' | 's1' | 's2' | 's3';
export type ThemeMode = 'light' | 'dark';
export type FilterDim = 'task' | 'condition' | 'rep' | 'agent';
export interface GlobalFilter { task: string[]; condition: string[]; rep: string[]; agent: string[]; }
export interface SectionSel { condition: string[]; rep: string[]; agent: string[]; }
export interface UiState {
  report: string;
  theme: ThemeMode;
  view: ViewKey;
  filter: GlobalFilter;
  overrides: Partial<Record<ViewKey, Partial<GlobalFilter>>>;
}
```

- [ ] **Step 4: Implement the reducers**

`web/app/src/state/uiState.ts`:
```ts
import type { FilterDim, GlobalFilter, SectionSel, ThemeMode, UiState, ViewKey } from '../types';

const emptyFilter = (): GlobalFilter => ({ task: [], condition: [], rep: [], agent: [] });

export function initUiState(report: string, theme: ThemeMode, view: ViewKey = 'overview', filter?: Partial<GlobalFilter>): UiState {
  return { report, theme, view, filter: { ...emptyFilter(), ...filter }, overrides: {} };
}
export function setReport(s: UiState, report: string): UiState {
  return { ...s, report, filter: emptyFilter(), overrides: {} };
}
export function setView(s: UiState, view: ViewKey): UiState { return { ...s, view }; }
export function setTheme(s: UiState, theme: ThemeMode): UiState { return { ...s, theme }; }

const toggleInList = (list: string[], t: string): string[] =>
  list.includes(t) ? list.filter((x) => x !== t) : [...list, t];

export function toggleFilter(s: UiState, dim: FilterDim, token: string): UiState {
  return { ...s, filter: { ...s.filter, [dim]: toggleInList(s.filter[dim], token) } };
}
export function clearFilter(s: UiState, dim: FilterDim): UiState {
  return { ...s, filter: { ...s.filter, [dim]: [] } };
}
export function setOverrideSingle(s: UiState, view: ViewKey, dim: FilterDim, token: string): UiState {
  const cur = s.overrides[view]?.[dim] ?? [];
  const next = cur.length === 1 && cur[0] === token ? [] : [token];
  return { ...s, overrides: { ...s.overrides, [view]: { ...s.overrides[view], [dim]: next } } };
}
export function effectiveSel(s: UiState, view: ViewKey): SectionSel {
  const o = s.overrides[view] ?? {};
  return {
    condition: o.condition ?? s.filter.condition,
    rep: o.rep ?? s.filter.rep,
    agent: o.agent ?? s.filter.agent,
  };
}
export function effectiveTask(s: UiState, view: ViewKey): string[] {
  return s.overrides[view]?.task ?? s.filter.task;
}
```

- [ ] **Step 5: Run tests + build**

Run: `npx vitest run src/state/uiState.test.ts` → PASS.
Run: `npm run build` → may fail where old code imports `AppState`/`appState` (Section1/2/3, App). That's expected; those are replaced in later tasks and the **old** `state/appState.ts` + `Section*` still compile against their own `AppState` import. To keep the build green now, **leave `state/appState.ts` and the old components importing from it untouched** — they import `AppState` from `types.ts`, which we just removed. **Therefore:** temporarily keep the old `AppState/SectionSel` exports by appending them back to `types.ts` under an `// @deprecated until T15 cutover` comment:
```ts
export type Dimension = 'condition' | 'rep' | 'agent';
export type ScopeKey = 's1' | 's2' | 's3';
export interface AppState { report: string; task: string[]; s1: SectionSel; s2: SectionSel; s3: SectionSel; }
```
Re-run `npm test` → Expected: green (old + new coexist).

- [ ] **Step 6: Commit**
```bash
git add web/app/src/state/uiState.ts web/app/src/state/uiState.test.ts web/app/src/types.ts
git commit -m "feat(web): UI state model + pure reducers (global filter + per-view overrides)"
```

---

### Task 5: Extend URL hash state

**Files:**
- Modify: `web/app/src/state/urlState.ts`
- Modify: `web/app/src/state/urlState.test.ts`

**Interfaces:**
- Produces: `interface UrlState { report: string|null; theme: ThemeMode|null; view: ViewKey|null; filter: Partial<GlobalFilter> }`; `parseHash(hash): UrlState`; `toHash(u: UrlState): string`. Round-trips `report`, `theme`, `view`, and each filter dim as comma lists. Backward-compatible: a bare `#report=x&task=a,b` still parses.

- [ ] **Step 1: Write the failing test**

Replace `web/app/src/state/urlState.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { parseHash, toHash } from './urlState';

describe('urlState', () => {
  it('round-trips report/theme/view/filter', () => {
    const u = { report: 'r1', theme: 'dark' as const, view: 's2' as const,
      filter: { task: ['coding'], condition: ['goal', 'subagents'], rep: ['r1'], agent: [] } };
    expect(parseHash(toHash(u))).toEqual({
      report: 'r1', theme: 'dark', view: 's2',
      filter: { task: ['coding'], condition: ['goal', 'subagents'], rep: ['r1'], agent: [] },
    });
  });
  it('parses a minimal hash', () => {
    expect(parseHash('#report=r1')).toEqual({ report: 'r1', theme: null, view: null, filter: { task: [], condition: [], rep: [], agent: [] } });
  });
  it('empty state → empty hash', () => {
    expect(toHash({ report: null, theme: null, view: null, filter: { task: [], condition: [], rep: [], agent: [] } })).toBe('');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/state/urlState.test.ts` → Expected: FAIL.

- [ ] **Step 3: Implement**

`web/app/src/state/urlState.ts`:
```ts
import type { GlobalFilter, ThemeMode, ViewKey } from '../types';

export interface UrlState {
  report: string | null;
  theme: ThemeMode | null;
  view: ViewKey | null;
  filter: GlobalFilter;
}

const DIMS = ['task', 'condition', 'rep', 'agent'] as const;

export function parseHash(hash: string): UrlState {
  const h = hash.replace(/^#/, '');
  const map = new Map<string, string>();
  for (const seg of h.split('&')) {
    if (!seg) continue;
    const eq = seg.indexOf('=');
    if (eq !== -1) map.set(seg.slice(0, eq), seg.slice(eq + 1));
  }
  const list = (k: string): string[] => { const v = map.get(k); return v ? v.split(',').filter(Boolean) : []; };
  const theme = map.get('theme'); const view = map.get('view');
  return {
    report: map.get('report') ?? null,
    theme: theme === 'light' || theme === 'dark' ? theme : null,
    view: ['overview', 's1', 's2', 's3'].includes(view ?? '') ? (view as ViewKey) : null,
    filter: { task: list('task'), condition: list('condition'), rep: list('rep'), agent: list('agent') },
  };
}

export function toHash(u: UrlState): string {
  const parts: string[] = [];
  if (u.report) parts.push(`report=${u.report}`);
  if (u.theme) parts.push(`theme=${u.theme}`);
  if (u.view) parts.push(`view=${u.view}`);
  for (const d of DIMS) if (u.filter[d as keyof GlobalFilter].length) parts.push(`${d}=${u.filter[d as keyof GlobalFilter].join(',')}`);
  return parts.length ? `#${parts.join('&')}` : '';
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/state/urlState.test.ts` → PASS. Run `npm test` → green (note: `App.tsx` still imports the old `UrlState`/`parseHash` shape; it builds because `parseHash` still returns `report`, and App reads `.report`/`.task`. If TS complains about `.task` removed from `UrlState`, App is replaced in T14 — to keep green now, App still uses the old fields via `parseHash(...).filter.task`. If build breaks, adjust App's two call sites to read `.filter.task` / `.report`.)

- [ ] **Step 5: Commit**
```bash
git add web/app/src/state/urlState.ts web/app/src/state/urlState.test.ts
git commit -m "feat(web): extend URL hash to report/theme/view/filter"
```

---

### Task 6: App state provider + hooks (store + URL/localStorage sync)

**Files:**
- Create: `web/app/src/state/AppStateProvider.tsx`
- Create: `web/app/src/state/AppStateProvider.test.tsx`

**Interfaces:**
- Produces:
  - `<AppStateProvider manifest={Manifest}>` — initializes `UiState` from URL hash → else localStorage theme → else `prefers-color-scheme`; default report = first variant; default view = `overview`. Syncs `report/theme/view/filter` to the URL hash (replaceState) and persists `theme` to `localStorage('cc_report_theme')`. Applies `.bp5-dark` to its root `<div className="app-root bp5-dark?">`.
  - Hooks: `useUi(): { state: UiState; dispatch: Dispatch }` where `dispatch` exposes `setReport/setView/setTheme/toggleFilter/clearFilter/setOverrideSingle`. Convenience hooks: `useTheme(): { mode; toggle() }`, `useFilter(): { filter; toggle(dim,token); clear(dim); setOverrideSingle(view,dim,token); effective(view); effectiveTask(view) }`, `useView(): { view; setView }`, `useReport(): { report; setReport }`.
- Consumes: `uiState.ts` reducers, `urlState.ts`, `types.ts`.

- [ ] **Step 1: Write the failing test**

`web/app/src/state/AppStateProvider.test.tsx`:
```tsx
import { describe, expect, it, beforeEach } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { AppStateProvider, useTheme, useView } from './AppStateProvider';
import type { Manifest } from '../types';

const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal'], tasks: ['coding'] }],
  strategy_desc: {}, task_meta: {}, available: [] };

function Probe() {
  const { mode, toggle } = useTheme();
  const { view, setView } = useView();
  return (<div>
    <span>mode:{mode}</span><span>view:{view}</span>
    <button onClick={toggle}>t</button><button onClick={() => setView('s2')}>v</button>
  </div>);
}

beforeEach(() => { window.location.hash = ''; localStorage.clear(); });

describe('AppStateProvider', () => {
  it('defaults to overview + light and toggles theme + view', () => {
    render(<AppStateProvider manifest={manifest}><Probe /></AppStateProvider>);
    expect(screen.getByText('mode:light')).toBeInTheDocument();
    expect(screen.getByText('view:overview')).toBeInTheDocument();
    act(() => screen.getByText('t').click());
    expect(screen.getByText('mode:dark')).toBeInTheDocument();
    expect(window.location.hash).toContain('theme=dark');
    act(() => screen.getByText('v').click());
    expect(window.location.hash).toContain('view=s2');
  });
  it('hydrates from the URL hash', () => {
    window.location.hash = '#report=r1&theme=dark&view=s2';
    render(<AppStateProvider manifest={manifest}><Probe /></AppStateProvider>);
    expect(screen.getByText('mode:dark')).toBeInTheDocument();
    expect(screen.getByText('view:s2')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/state/AppStateProvider.test.tsx` → Expected: FAIL (module not found).

- [ ] **Step 3: Implement the provider**

`web/app/src/state/AppStateProvider.tsx`:
```tsx
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { FilterDim, Manifest, ThemeMode, UiState, ViewKey } from '../types';
import * as R from './uiState';
import { parseHash, toHash } from './urlState';

const THEME_KEY = 'cc_report_theme';

function initialTheme(urlTheme: ThemeMode | null): ThemeMode {
  if (urlTheme) return urlTheme;
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function bootstrap(manifest: Manifest): UiState {
  const url = parseHash(window.location.hash);
  const report = url.report && manifest.variants.some((v) => v.key === url.report) ? url.report : manifest.variants[0]?.key ?? '';
  const s = R.initUiState(report, initialTheme(url.theme), url.view ?? 'overview', url.filter);
  return s;
}

interface Ctx { state: UiState; setState: React.Dispatch<React.SetStateAction<UiState>>; }
const StateCtx = createContext<Ctx | null>(null);
function useCtx(): Ctx { const v = useContext(StateCtx); if (!v) throw new Error('AppStateProvider missing'); return v; }

export function AppStateProvider({ manifest, children }: { manifest: Manifest; children: ReactNode }) {
  const [state, setState] = useState<UiState>(() => bootstrap(manifest));

  useEffect(() => {
    const next = toHash({ report: state.report, theme: state.theme, view: state.view, filter: state.filter });
    if (next !== window.location.hash) window.history.replaceState(null, '', next || window.location.pathname);
    localStorage.setItem(THEME_KEY, state.theme);
  }, [state.report, state.theme, state.view, state.filter]);

  const value = useMemo(() => ({ state, setState }), [state]);
  return <StateCtx.Provider value={value}><div className={`app-root${state.theme === 'dark' ? ' bp5-dark' : ''}`}>{children}</div></StateCtx.Provider>;
}

export function useUi() { return useCtx().state; }
export function useTheme() {
  const { state, setState } = useCtx();
  return { mode: state.theme, toggle: () => setState((s) => R.setTheme(s, s.theme === 'dark' ? 'light' : 'dark')),
    set: (m: ThemeMode) => setState((s) => R.setTheme(s, m)) };
}
export function useView() {
  const { state, setState } = useCtx();
  return { view: state.view, setView: (v: ViewKey) => setState((s) => R.setView(s, v)) };
}
export function useReport() {
  const { state, setState } = useCtx();
  return { report: state.report, setReport: (k: string) => setState((s) => R.setReport(s, k)) };
}
export function useFilter() {
  const { state, setState } = useCtx();
  return {
    filter: state.filter, overrides: state.overrides,
    toggle: (dim: FilterDim, t: string) => setState((s) => R.toggleFilter(s, dim, t)),
    clear: (dim: FilterDim) => setState((s) => R.clearFilter(s, dim)),
    setOverrideSingle: (view: ViewKey, dim: FilterDim, t: string) => setState((s) => R.setOverrideSingle(s, view, dim, t)),
    effective: (view: ViewKey) => R.effectiveSel(state, view),
    effectiveTask: (view: ViewKey) => R.effectiveTask(state, view),
  };
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/state/AppStateProvider.test.tsx` → PASS. Run `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/state/AppStateProvider.tsx web/app/src/state/AppStateProvider.test.tsx
git commit -m "feat(web): app state provider with URL + localStorage sync and theme/filter hooks"
```

---

### Task 7: AppShell + TopBar (Blueprint Navbar, variant switch, theme toggle)

**Files:**
- Create: `web/app/src/components/shell/AppShell.tsx`
- Create: `web/app/src/components/shell/TopBar.tsx`
- Create: `web/app/src/components/shell/TopBar.test.tsx`

**Interfaces:**
- Consumes: `useReport`, `useTheme`, `useData().reload` (existing `DataContext`), `Manifest`.
- Produces: `<AppShell manifest sidebar={ReactNode} canvas={ReactNode} />` rendering `TopBar` + a two-column grid (rail | canvas). `<TopBar manifest />` with the variant `Tabs` (hidden when ≤1 variant), a theme `Switch` (label sun/moon), and a reload `Button`.

- [ ] **Step 1: Write the failing test**

`web/app/src/components/shell/TopBar.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider, useTheme } from '../../state/AppStateProvider';
import { TopBar } from './TopBar';
import type { Manifest } from '../../types';

vi.mock('../../data/DataContext', () => ({ useData: () => ({ reload: vi.fn() }) }));
const manifest: Manifest = { variants: [
  { key: 'r1', eyebrow: '', title: 'Report One', lede: '', conditions: ['goal'], tasks: ['coding'] },
  { key: 'r2', eyebrow: '', title: 'Report Two', lede: '', conditions: ['goal'], tasks: ['coding'] }],
  strategy_desc: {}, task_meta: {}, available: [] };
function Mode() { return <span>mode:{useTheme().mode}</span>; }

describe('TopBar', () => {
  it('shows variant tabs and toggles theme', async () => {
    render(<AppStateProvider manifest={manifest}><TopBar manifest={manifest} /><Mode /></AppStateProvider>);
    expect(screen.getByRole('tab', { name: 'Report One' })).toBeInTheDocument();
    expect(screen.getByText('mode:light')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('switch'));
    expect(screen.getByText('mode:dark')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/shell/TopBar.test.tsx` → Expected: FAIL.

- [ ] **Step 3: Implement TopBar + AppShell**

`web/app/src/components/shell/TopBar.tsx`:
```tsx
import { Alignment, Button, Navbar, Switch, Tab, Tabs } from '@blueprintjs/core';
import type { Manifest } from '../../types';
import { useReport, useTheme } from '../../state/AppStateProvider';
import { useData } from '../../data/DataContext';

export function TopBar({ manifest }: { manifest: Manifest }) {
  const { report, setReport } = useReport();
  const { mode, toggle } = useTheme();
  const { reload } = useData();
  return (
    <Navbar className="app-topbar">
      <Navbar.Group align={Alignment.LEFT}>
        <Navbar.Heading>CC Orchestration Report</Navbar.Heading>
        {manifest.variants.length > 1 && (
          <Tabs id="variant" selectedTabId={report} onChange={(id) => setReport(String(id))} animate>
            {manifest.variants.map((v) => <Tab key={v.key} id={v.key} title={v.title} />)}
          </Tabs>
        )}
      </Navbar.Group>
      <Navbar.Group align={Alignment.RIGHT}>
        <Switch checked={mode === 'dark'} onChange={toggle} label={mode === 'dark' ? '☾ Dark' : '☀ Light'} style={{ margin: 0 }} />
        <Navbar.Divider />
        <Button minimal icon="refresh" aria-label="Reload data" onClick={reload} />
      </Navbar.Group>
    </Navbar>
  );
}
```

`web/app/src/components/shell/AppShell.tsx`:
```tsx
import type { ReactNode } from 'react';
import type { Manifest } from '../../types';
import { TopBar } from './TopBar';

export function AppShell({ manifest, sidebar, canvas }: { manifest: Manifest; sidebar: ReactNode; canvas: ReactNode }) {
  return (
    <div className="app-shell">
      <TopBar manifest={manifest} />
      <div className="app-body">
        <aside className="app-rail">{sidebar}</aside>
        <main className="app-canvas">{canvas}</main>
      </div>
    </div>
  );
}
```

Add to `tokens.css` (layout):
```css
.app-body { display: grid; grid-template-columns: 248px minmax(0, 1fr); gap: 0; }
.app-rail { background: var(--app-rail-bg); border-right: 1px solid var(--app-line); padding: 16px 14px; min-height: calc(100vh - 50px); position: sticky; top: 0; align-self: start; }
.app-canvas { padding: 20px 24px 56px; max-width: 1280px; }
@media (max-width: 880px) { .app-body { grid-template-columns: 1fr; } .app-rail { position: static; min-height: 0; } }
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/components/shell/TopBar.test.tsx` → PASS. `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/components/shell/AppShell.tsx web/app/src/components/shell/TopBar.tsx web/app/src/components/shell/TopBar.test.tsx web/app/src/theme/tokens.css
git commit -m "feat(web): AppShell + Blueprint TopBar (variant tabs, theme switch, reload)"
```

---

### Task 8: FilterRail (global cross-filter UI)

**Files:**
- Create: `web/app/src/components/shell/RailFilterGroup.tsx`
- Create: `web/app/src/components/shell/FilterRail.tsx`
- Create: `web/app/src/components/shell/FilterRail.test.tsx`

**Interfaces:**
- Consumes: `useFilter`, `useReport` (active variant for the dimension domains), `useData().data` (runs/turns to derive rep + agent domains), `Manifest`.
- Produces: `<FilterRail />` — four `RailFilterGroup`s (Task, Feature/condition, Rollout/rep, Agent) of toggle `Tag`s + a per-group clear and a global Reset `Button`. `<RailFilterGroup label items active dotFor? onToggle onClear />`.
- Domains: tasks = active variant `tasks`; conditions = active variant `conditions`; reps = distinct `r{rep}` across variant runs; agents = `presentAgentTypes` over variant turns. (Same derivation the old `App.tsx`/sections used.)

- [ ] **Step 1: Write the failing test**

`web/app/src/components/shell/FilterRail.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider, useFilter } from '../../state/AppStateProvider';
import { FilterRail } from './FilterRail';
import type { Manifest } from '../../types';

const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal', 'subagents'], tasks: ['coding'] }],
  strategy_desc: {}, task_meta: {}, available: [] };
vi.mock('../../data/DataContext', () => ({ useData: () => ({ data: { runs: [{ run_id: 'a', task: 'coding', condition: 'goal', rep: 1 }], turns: [] } }) }));
function Probe() { const f = useFilter(); return <span>cond:{f.filter.condition.join(',')}</span>; }

describe('FilterRail', () => {
  it('toggles a global condition filter', async () => {
    render(<AppStateProvider manifest={manifest}><FilterRail /><Probe /></AppStateProvider>);
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    expect(screen.getByText('cond:goal')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/shell/FilterRail.test.tsx` → Expected: FAIL.

- [ ] **Step 3: Implement**

`web/app/src/components/shell/RailFilterGroup.tsx`:
```tsx
import { Button, Tag } from '@blueprintjs/core';

interface Props {
  label: string; items: string[]; active: string[];
  dotFor?: (t: string) => string; onToggle: (t: string) => void; onClear: () => void;
}
export function RailFilterGroup({ label, items, active, dotFor, onToggle, onClear }: Props) {
  if (!items.length) return null;
  return (
    <div className="rail-group">
      <div className="rail-head"><span className="rail-name">{label}</span>
        {active.length > 0 && <Button minimal small text="clear" onClick={onClear} />}</div>
      <div className="rail-chips">
        {items.map((t) => (
          <Tag key={t} interactive round minimal={!active.includes(t)}
            intent={active.includes(t) ? 'primary' : 'none'} onClick={() => onToggle(t)}
            aria-pressed={active.includes(t)} role="button">
            {dotFor && <span className="rail-dot" style={{ background: dotFor(t) }} />}{t}
          </Tag>
        ))}
      </div>
    </div>
  );
}
```

`web/app/src/components/shell/FilterRail.tsx`:
```tsx
import { Button } from '@blueprintjs/core';
import { useMemo } from 'react';
import { RailFilterGroup } from './RailFilterGroup';
import { useFilter, useReport } from '../../state/AppStateProvider';
import { useData } from '../../data/DataContext';
import { conditionColor } from '../../theme';
import { presentAgentTypes } from '../../data/filters';

export function FilterRail() {
  const { report } = useReport();
  const { data } = useData();
  const { filter, toggle, clear } = useFilter();
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  const variantRuns = useMemo(() => (data?.runs ?? []).filter((r) => variant && variant.tasks.includes(r.task) && variant.conditions.includes(r.condition)), [data, variant]);
  const reps = useMemo(() => Array.from(new Set(variantRuns.map((r) => `r${r.rep}`))).sort(), [variantRuns]);
  const variantTurns = useMemo(() => (data?.turns ?? []).filter((t) => variant && variant.tasks.includes(t.task) && variant.conditions.includes(t.condition)), [data, variant]);
  const agents = useMemo(() => presentAgentTypes(variantTurns), [variantTurns]);
  if (!variant) return null;
  const anyActive = filter.task.length || filter.condition.length || filter.rep.length || filter.agent.length;
  return (
    <div className="rail">
      <div className="rail-top"><span className="rail-title">Filters</span>
        {anyActive ? <Button minimal small text="Reset all" onClick={() => { clear('task'); clear('condition'); clear('rep'); clear('agent'); }} /> : null}</div>
      <RailFilterGroup label="Task" items={variant.tasks} active={filter.task} onToggle={(t) => toggle('task', t)} onClear={() => clear('task')} />
      <RailFilterGroup label="Feature" items={variant.conditions} active={filter.condition} dotFor={conditionColor} onToggle={(t) => toggle('condition', t)} onClear={() => clear('condition')} />
      <RailFilterGroup label="Rollout" items={reps} active={filter.rep} onToggle={(t) => toggle('rep', t)} onClear={() => clear('rep')} />
      <RailFilterGroup label="Agent" items={agents} active={filter.agent} onToggle={(t) => toggle('agent', t)} onClear={() => clear('agent')} />
    </div>
  );
}
```

Add to `tokens.css`:
```css
.rail-top, .rail-head { display: flex; align-items: center; justify-content: space-between; }
.rail-title { font-family: var(--app-mono); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--app-muted); }
.rail-group { margin: 14px 0; }
.rail-name { font-family: var(--app-mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--app-ink); font-weight: 600; }
.rail-chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
.rail-dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; display: inline-block; }
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/components/shell/FilterRail.test.tsx` → PASS. `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/components/shell/RailFilterGroup.tsx web/app/src/components/shell/FilterRail.tsx web/app/src/components/shell/FilterRail.test.tsx web/app/src/theme/tokens.css
git commit -m "feat(web): global cross-filter rail (Task/Feature/Rollout/Agent + reset)"
```

---

### Task 9: ViewNav + ViewCanvas

**Files:**
- Create: `web/app/src/components/shell/ViewNav.tsx`
- Create: `web/app/src/components/shell/ViewCanvas.tsx`
- Create: `web/app/src/components/shell/ViewNav.test.tsx`

**Interfaces:**
- Consumes: `useView`. Placeholder view bodies for now (real views land T10–T13).
- Produces: `<ViewNav />` (Blueprint `Tabs`, ids `overview|s1|s2|s3`, titles `Overview / §1 Averages / §2 Distributions / §3 Single run`); `<ViewCanvas views={{overview,s1,s2,s3}} />` renders the active view by `useView().view`.

- [ ] **Step 1: Write the failing test**

`web/app/src/components/shell/ViewNav.test.tsx`:
```tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider } from '../../state/AppStateProvider';
import { ViewNav } from './ViewNav';
import { ViewCanvas } from './ViewCanvas';
import type { Manifest } from '../../types';

const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal'], tasks: ['coding'] }], strategy_desc: {}, task_meta: {}, available: [] };
const views = { overview: <p>OVERVIEW</p>, s1: <p>S1</p>, s2: <p>S2</p>, s3: <p>S3</p> };

describe('ViewNav + ViewCanvas', () => {
  it('switches the active view', async () => {
    render(<AppStateProvider manifest={manifest}><ViewNav /><ViewCanvas views={views} /></AppStateProvider>);
    expect(screen.getByText('OVERVIEW')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: /Distributions/ }));
    expect(screen.getByText('S2')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/shell/ViewNav.test.tsx` → Expected: FAIL.

- [ ] **Step 3: Implement**

`web/app/src/components/shell/ViewNav.tsx`:
```tsx
import { Tab, Tabs } from '@blueprintjs/core';
import { useView } from '../../state/AppStateProvider';
import type { ViewKey } from '../../types';

const TABS: { id: ViewKey; title: string }[] = [
  { id: 'overview', title: 'Overview' }, { id: 's1', title: '§1 Averages' },
  { id: 's2', title: '§2 Distributions' }, { id: 's3', title: '§3 Single run' },
];
export function ViewNav() {
  const { view, setView } = useView();
  return (
    <Tabs id="view-nav" large selectedTabId={view} onChange={(id) => setView(id as ViewKey)} className="view-nav">
      {TABS.map((t) => <Tab key={t.id} id={t.id} title={t.title} />)}
    </Tabs>
  );
}
```

`web/app/src/components/shell/ViewCanvas.tsx`:
```tsx
import type { ReactNode } from 'react';
import { useView } from '../../state/AppStateProvider';
import type { ViewKey } from '../../types';

export function ViewCanvas({ views }: { views: Record<ViewKey, ReactNode> }) {
  const { view } = useView();
  return <div className="view-canvas">{views[view]}</div>;
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/components/shell/ViewNav.test.tsx` → PASS. `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/components/shell/ViewNav.tsx web/app/src/components/shell/ViewCanvas.tsx web/app/src/components/shell/ViewNav.test.tsx
git commit -m "feat(web): ViewNav tabs + ViewCanvas switcher"
```

---

## Phase 2 — Views

> Each view is a presentational component reading filtered data via `useFilter().effective(view)` + `effectiveTask(view)`, passing `useTheme().mode` to every `<EChart>`. They reuse the **salvaged** chart builders exactly as the old sections did. Wrap chart panels in Blueprint `Card`/`Section`. Apply the `frontend-design` skill for layout/spacing/typography on each.

### Task 10: OverviewView (brief + strategy legend + KPI cards + headline)

**Files:**
- Create: `web/app/src/views/OverviewView.tsx`
- Create: `web/app/src/views/OverviewView.test.tsx`

**Interfaces:**
- Consumes: `useData().data` (manifest/runs), `useReport`, `useFilter`, `useTheme`; salvaged `computeKpis` (`data/kpis`), `conditionColor`, `matrixOption`+`matrixData` for a headline chart, `Variant.lede` (HTML), `manifest.strategy_desc`, `manifest.task_meta`.
- Produces: `<OverviewView />` — KPI `Card` row (from `computeKpis(scopedRuns)`), a variant brief card (`task_meta` title/measures + `lede`), a strategy legend (`strategy_desc` keyed by condition with `conditionColor` dots), and one headline §1 matrix chart.

- [ ] **Step 1: Write the failing test**

`web/app/src/views/OverviewView.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppStateProvider } from '../state/AppStateProvider';
import { OverviewView } from './OverviewView';
import type { Manifest, Run } from '../types';

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: 'E', title: 'R1', lede: 'Lede', conditions: ['goal'], tasks: ['coding'] }],
  strategy_desc: { goal: 'Goal strategy' }, task_meta: { coding: { title: 'Coding', measures: 'speed' } }, available: [] };
const runs: Run[] = [{ run_id: 'a', task: 'coding', condition: 'goal', rep: 1, success: true, speedup: null, total_cost_usd: 1, num_requests: 3, cache_hit_ratio: 0.5, quality_score: 0.8, research_rubric_score: null }];
vi.mock('../data/DataContext', () => ({ useData: () => ({ data: { manifest, runs, turns: [], components: [] } }) }));

describe('OverviewView', () => {
  it('renders KPI cards, the strategy legend, and a headline chart', () => {
    render(<AppStateProvider manifest={manifest}><OverviewView /></AppStateProvider>);
    expect(screen.getByText('Runs')).toBeInTheDocument();
    expect(screen.getByText('Goal strategy')).toBeInTheDocument();
    expect(screen.getByTestId('chart')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/OverviewView.test.tsx` → Expected: FAIL.

- [ ] **Step 3: Implement**

`web/app/src/views/OverviewView.tsx`:
```tsx
import { useMemo } from 'react';
import { Card, Elevation } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { computeKpis } from '../data/kpis';
import { scopeRuns } from '../data/filters';
import { conditionColor } from '../theme';
import { EChart } from '../components/EChart';
import { matrixData } from '../charts/matrix';
import { matrixOption } from '../charts/section1Options';

export function OverviewView() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  const runs = data?.runs ?? [];
  const scoped = useMemo(() => scopeRuns(runs, effectiveTask('overview'), effective('overview')), [runs, effective, effectiveTask]);
  if (!variant || !data) return null;

  const k = computeKpis(scoped);
  const fmt = (v: number | null, d = 2, u = '') => (v == null ? '—' : `${v.toFixed(d)}${u}`);
  const cards = [
    { label: 'Runs', value: String(k.runs) }, { label: 'Mean requests', value: fmt(k.meanRequests, 1) },
    { label: 'Mean total cost', value: k.meanCost == null ? '—' : `$${k.meanCost.toFixed(3)}` },
    { label: 'Mean quality', value: fmt(k.meanQuality, 2) },
    { label: 'Mean cache hit', value: k.meanCacheHit == null ? '—' : `${(k.meanCacheHit * 100).toFixed(0)}%` },
  ];
  const tasks = effectiveTask('overview').length ? effectiveTask('overview') : variant.tasks;
  const reps = Array.from(new Set(scoped.map((r) => r.rep))).sort((a, b) => a - b);
  const matrix = matrixData(scoped, tasks, reps, variant.conditions);

  return (
    <div className="view view-overview">
      <div className="kpi-row">
        {cards.map((c) => (
          <Card key={c.label} elevation={Elevation.ZERO} className="kpi-card">
            <div className="kpi-label">{c.label}</div><div className="kpi-value">{c.value}</div>
          </Card>
        ))}
      </div>
      <div className="overview-grid">
        <Card elevation={Elevation.ZERO} className="panel-card">
          <h2 className="panel-title">{data.manifest.task_meta[tasks[0]]?.title ?? variant.title}</h2>
          <p className="panel-lede" dangerouslySetInnerHTML={{ __html: variant.lede }} />
          <ul className="strategy-legend">
            {variant.conditions.map((c) => (
              <li key={c}><span className="rail-dot" style={{ background: conditionColor(c) }} /><b>{c}</b> — {data.manifest.strategy_desc[c] ?? ''}</li>
            ))}
          </ul>
        </Card>
        <Card elevation={Elevation.ZERO} className="panel-card">
          <h2 className="panel-title">Experiment matrix</h2>
          <EChart className="chart" themeMode={mode} option={matrixOption(matrix)} />
        </Card>
      </div>
    </div>
  );
}
```

Add to `tokens.css`:
```css
.kpi-row { display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 12px; margin-bottom: 18px; }
.kpi-card { border-left: 3px solid var(--app-muted); }
.kpi-label { font-family: var(--app-mono); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--app-muted); }
.kpi-value { font-family: var(--app-mono); font-size: 24px; font-weight: 600; margin-top: 6px; }
.overview-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }
.panel-card { min-width: 0; } .panel-title { font-size: 14.5px; font-weight: 600; margin: 0 0 8px; }
.strategy-legend { list-style: none; padding: 0; margin: 10px 0 0; } .strategy-legend li { margin: 6px 0; color: var(--app-muted); }
@media (max-width: 880px) { .kpi-row { grid-template-columns: repeat(2,1fr); } .overview-grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/views/OverviewView.test.tsx` → PASS. `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/views/OverviewView.tsx web/app/src/views/OverviewView.test.tsx web/app/src/theme/tokens.css
git commit -m "feat(web): Overview view (KPI cards, strategy legend, headline matrix)"
```

---

### Task 11: Section1View (§1 averages)

**Files:**
- Create: `web/app/src/views/Section1View.tsx`
- Create: `web/app/src/views/Section1View.test.tsx`

**Interfaces:**
- Consumes: `useData`, `useReport`, `useFilter`, `useTheme`; salvaged `conditionMetrics`/`conditionOverheads`, `matrixData`, `matrixOption`/`conditionOption`/`overheadOption`/`efficiencyOption`, `STATUS_COLORS`/`STATUS_GLYPHS`. Local `useState` for the metric/overhead `<select>` (kept local, not global — view-internal UI).
- Produces: `<Section1View />` — matrix card + condition-comparison card (metric select) + overhead card (if baseline) + quality/cost map card. Scoped by `effective('s1')`.

- [ ] **Step 1: Write the failing test**

`web/app/src/views/Section1View.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppStateProvider } from '../state/AppStateProvider';
import { Section1View } from './Section1View';
import type { Manifest, Run } from '../types';

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['single_agent', 'goal'], tasks: ['coding'] }], strategy_desc: {}, task_meta: {}, available: [] };
const runs: Run[] = [{ run_id: 'a', task: 'coding', condition: 'goal', rep: 1, success: true, speedup: 1, total_cost_usd: 1, num_requests: 3, cache_hit_ratio: 0.5, quality_score: 0.8, research_rubric_score: null }];
vi.mock('../data/DataContext', () => ({ useData: () => ({ data: { manifest, runs, turns: [], components: [] } }) }));

describe('Section1View', () => {
  it('renders the matrix and comparison panels with a baseline overhead panel', () => {
    render(<AppStateProvider manifest={manifest}><Section1View /></AppStateProvider>);
    expect(screen.getByText('Experiment matrix')).toBeInTheDocument();
    expect(screen.getByText('Overhead vs single agent')).toBeInTheDocument();
    expect(screen.getAllByTestId('chart').length).toBeGreaterThanOrEqual(3);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/Section1View.test.tsx` → Expected: FAIL.

- [ ] **Step 3: Implement** — port `Section1.tsx` body, replacing `state.s1`/`state.task` with `effective('s1')`/`effectiveTask('s1')`, wrapping panels in `Card`, threading `themeMode={mode}` into each `<EChart>`, and keeping the metric/overhead selects as local `useState`. Use the same `METRICS`, `OVERHEADS`, `KEY_ORDER`, `STATUS_LABELS` constants from `Section1.tsx`.

`web/app/src/views/Section1View.tsx`:
```tsx
import { useMemo, useState } from 'react';
import { Card, Elevation, HTMLSelect } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { scopeRuns } from '../data/filters';
import { EChart } from '../components/EChart';
import { matrixOption, conditionOption, overheadOption, efficiencyOption } from '../charts/section1Options';
import { conditionMetrics, conditionOverheads } from '../charts/conditionMetrics';
import { matrixData } from '../charts/matrix';
import { STATUS_COLORS, STATUS_GLYPHS } from '../charts/echartsTheme';

const METRICS = [
  ['mean_completion_time_s', 'Mean completion time (s)'], ['mean_num_requests', 'Mean requests'],
  ['mean_total_cost_usd', 'Mean total cost ($)'], ['mean_quality_score', 'Mean quality score'],
  ['mean_cost_efficiency_score', 'Mean cost efficiency'], ['mean_speedup', 'Mean coding speedup'],
  ['mean_research_rubric_score', 'Mean research rubric score'], ['mean_peak_prompt_tokens', 'Mean peak prompt tokens'],
  ['mean_total_cache_read', 'Mean cache read tokens'], ['mean_cache_hit_ratio', 'Mean cache hit ratio'],
  ['success_rate', 'Success rate'],
] as const;
const OVERHEADS = [
  ['num_requests_factor', 'Requests'], ['completion_time_factor', 'Completion time'],
  ['total_cost_factor', 'Total cost'], ['peak_prompt_tokens_factor', 'Peak prompt tokens'],
  ['total_cache_read_factor', 'Cache reads'], ['output_tokens_factor', 'Output tokens'],
] as const;
const KEY_ORDER = [2, 1, 3, 0] as const;
const STATUS_LABELS = ['missing', 'failed', 'success', 'skipped'] as const;

export function Section1View() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const [metric, setMetric] = useState('mean_completion_time_s');
  const [overhead, setOverhead] = useState('num_requests_factor');
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  const runs = useMemo(() => scopeRuns(data?.runs ?? [], effectiveTask('s1'), effective('s1')), [data, effective, effectiveTask]);
  if (!variant) return null;

  const hasBaseline = variant.conditions.includes('single_agent');
  const conds = effective('s1').condition.length ? effective('s1').condition : variant.conditions;
  const tasks = effectiveTask('s1').length ? effectiveTask('s1') : variant.tasks;
  const reps = Array.from(new Set(runs.map((r) => r.rep))).sort((a, b) => a - b);
  const metrics = conditionMetrics(runs, tasks, variant.conditions);
  const overheads = conditionOverheads(metrics, tasks, variant.conditions);
  const matrix = matrixData(runs, tasks, reps, conds);
  const metricLabel = METRICS.find(([v]) => v === metric)?.[1] ?? metric;
  const overheadLabel = OVERHEADS.find(([v]) => v === overhead)?.[1] ?? overhead;

  return (
    <div className="view view-grid">
      <Card elevation={Elevation.ZERO} className="panel-card">
        <h2 className="panel-title">Experiment matrix</h2>
        <EChart className="chart" themeMode={mode} option={matrixOption(matrix)} />
        <div className="status-key">{KEY_ORDER.map((i) => (
          <span key={i} className="status-swatch"><span style={{ background: STATUS_COLORS[i] }}>{STATUS_GLYPHS[i]}</span>{STATUS_LABELS[i]}</span>))}</div>
      </Card>
      <Card elevation={Elevation.ZERO} className="panel-card">
        <div className="panel-head"><h2 className="panel-title">Condition comparison</h2>
          <HTMLSelect value={metric} onChange={(e) => setMetric(e.currentTarget.value)} aria-label="metric">
            {METRICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</HTMLSelect></div>
        <EChart className="chart" themeMode={mode} option={conditionOption(metrics, conds, tasks, metric, metricLabel)} />
      </Card>
      {hasBaseline && (
        <Card elevation={Elevation.ZERO} className="panel-card">
          <div className="panel-head"><h2 className="panel-title">Overhead vs single agent</h2>
            <HTMLSelect value={overhead} onChange={(e) => setOverhead(e.currentTarget.value)} aria-label="resource">
              {OVERHEADS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</HTMLSelect></div>
          <EChart className="chart" themeMode={mode} option={overheadOption(overheads, conds, tasks, overhead, overheadLabel)} />
        </Card>
      )}
      <Card elevation={Elevation.ZERO} className="panel-card">
        <h2 className="panel-title">Quality vs cost map</h2>
        <EChart className="chart" themeMode={mode} option={efficiencyOption(metrics, conds, tasks[0] ?? '')} />
      </Card>
    </div>
  );
}
```

Add to `tokens.css`:
```css
.view-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.status-key { display: flex; flex-wrap: wrap; gap: 7px 14px; margin-top: 10px; font-family: var(--app-mono); font-size: 11px; color: var(--app-muted); }
.status-key .status-swatch span:first-child { display: inline-flex; width: 16px; height: 16px; align-items: center; justify-content: center; border-radius: 3px; margin-right: 5px; }
@media (max-width: 880px) { .view-grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/views/Section1View.test.tsx` → PASS. `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/views/Section1View.tsx web/app/src/views/Section1View.test.tsx web/app/src/theme/tokens.css
git commit -m "feat(web): §1 Averages view on Blueprint cards"
```

---

### Task 12: Section2View (§2 distributions)

**Files:**
- Create: `web/app/src/views/Section2View.tsx`
- Create: `web/app/src/views/Section2View.test.tsx`

**Interfaces:**
- Consumes: `useData`, `useReport`, `useFilter`, `useTheme`; salvaged `cacheByAgent` (`cacheTimeline`), `cacheOption`/`latencyOption` (`section2Options`), `scopeTurns`. Scope by `effective('s2')`/`effectiveTask('s2')`.
- Produces: `<Section2View />` — per-task cache-hit-rate card + cache-vs-context card, mirroring `Section2.tsx` (single-agent derived from `effective('s2').agent.length===1`).

- [ ] **Step 1: Write the failing test**

`web/app/src/views/Section2View.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppStateProvider } from '../state/AppStateProvider';
import { Section2View } from './Section2View';
import type { Manifest } from '../types';

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal'], tasks: ['coding'] }], strategy_desc: {}, task_meta: {}, available: [] };
vi.mock('../data/DataContext', () => ({ useData: () => ({ data: { manifest, runs: [], turns: [{ run_id: 'a', task: 'coding', condition: 'goal', rep: 1, request_index: 0, request_type: 'main-agent', input_tokens: 1, output_tokens: 1, cache_read: 1, cache_creation_5m: 0, cache_creation_1h: 0, ttft_s: null, total_s: null }], components: [] } }) }));

describe('Section2View', () => {
  it('renders the distribution panels', () => {
    render(<AppStateProvider manifest={manifest}><Section2View /></AppStateProvider>);
    expect(screen.getByText(/Prefix Cache Hit Rate/)).toBeInTheDocument();
    expect(screen.getAllByTestId('chart').length).toBeGreaterThanOrEqual(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails** — Run: `npx vitest run src/views/Section2View.test.tsx` → FAIL.

- [ ] **Step 3: Implement** — port `Section2.tsx`:
```tsx
import { useMemo } from 'react';
import { Card, Elevation } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { scopeTurns } from '../data/filters';
import { EChart } from '../components/EChart';
import { cacheByAgent } from '../charts/cacheTimeline';
import { cacheOption, latencyOption } from '../charts/section2Options';

export function Section2View() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  const sel = effective('s2');
  const turns = useMemo(() => scopeTurns(data?.turns ?? [], effectiveTask('s2'), sel), [data, effectiveTask, sel]);
  if (!variant) return null;
  const conds = sel.condition.length ? sel.condition : variant.conditions;
  const tasks = effectiveTask('s2').length ? effectiveTask('s2') : variant.tasks;
  const singleAgent = sel.agent.length === 1 ? sel.agent[0] : 'all';
  return (
    <div className="view view-stack">
      <Card elevation={Elevation.ZERO} className="panel-card">
        <h2 className="panel-title">Prefix Cache Hit Rate (accumulated)</h2>
        {tasks.map((task) => (
          <div key={task}>
            <h3 className="cache-sub">{task}</h3>
            <EChart className="chart short" themeMode={mode} option={cacheOption(cacheByAgent(turns.filter((t) => t.task === task)), conds, singleAgent)} />
          </div>
        ))}
      </Card>
      <Card elevation={Elevation.ZERO} className="panel-card">
        <h2 className="panel-title">Prefix cache hit rate vs context length</h2>
        <EChart className="chart" themeMode={mode} option={latencyOption(turns, conds)} />
      </Card>
    </div>
  );
}
```
Add to `tokens.css`: `.view-stack { display: grid; gap: 16px; } .cache-sub { font-family: var(--app-mono); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--app-muted); margin: 8px 0 2px; } .chart { width: 100%; height: 340px; } .chart.short { height: 290px; } .chart.tall { height: 440px; }`

- [ ] **Step 4: Run tests** — `npx vitest run src/views/Section2View.test.tsx` → PASS. `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/views/Section2View.tsx web/app/src/views/Section2View.test.tsx web/app/src/theme/tokens.css
git commit -m "feat(web): §2 Distributions view on Blueprint cards"
```

---

### Task 13: Section3View (§3 single-run drilldown, single-select Feature override)

**Files:**
- Create: `web/app/src/views/Section3View.tsx`
- Create: `web/app/src/views/Section3View.test.tsx`

**Interfaces:**
- Consumes: `useData`, `useReport`, `useFilter`, `useTheme`; salvaged `orderedRequests`, `AGENT_TYPE_ORDER`, `costTimelineOption`, `breakdownData`/`hitRateData`/`COMPOSE_MODES`, `contextOption`, `ContextTextPanel` (+`CtxSelection`), `scopeRuns`/`scopeTurns`. The **Feature** filter for §3 is a per-view single-select override via `useFilter().setOverrideSingle('s3','condition',token)`; scoping uses `effective('s3')` (which reads the override). A small in-view Feature selector renders Blueprint `Tag`s for `variant.conditions`, active = `effective('s3').condition`.
- Produces: `<Section3View />` — one drilldown card per scoped run (cost timeline + context breakdown + text panel), plus the local compose/group/hitrate/density controls (local `useState`, as in `Section3.tsx`).

- [ ] **Step 1: Write the failing test** (mirrors commit `73cd514` — Feature is single-select)

`web/app/src/views/Section3View.test.tsx`:
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider, useFilter } from '../state/AppStateProvider';
import { Section3View } from './Section3View';
import type { Manifest } from '../types';

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
vi.mock('../components/ContextTextPanel', () => ({ ContextTextPanel: () => <div /> }));
const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal', 'subagents'], tasks: ['coding'] }], strategy_desc: {}, task_meta: {}, available: [] };
vi.mock('../data/DataContext', () => ({ useData: () => ({ data: { manifest, runs: [], turns: [], components: [] } }) }));
function Probe() { const f = useFilter(); return <span>s3cond:{f.effective('s3').condition.join(',')}</span>; }

describe('Section3View Feature override', () => {
  it('is single-select: picking a second Feature replaces the first', async () => {
    render(<AppStateProvider manifest={manifest}><Section3View /><Probe /></AppStateProvider>);
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    expect(screen.getByText('s3cond:goal')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'subagents' }));
    expect(screen.getByText('s3cond:subagents')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails** — Run: `npx vitest run src/views/Section3View.test.tsx` → FAIL.

- [ ] **Step 3: Implement** — port `Section3.tsx`, replacing the §3 Feature `FilterChunk` with single-select `Tag`s wired to `setOverrideSingle('s3','condition',...)`, scoping runs/turns via `effective('s3')`/`effectiveTask('s3')`, threading `themeMode={mode}`:
```tsx
import { useState } from 'react';
import { Card, Checkbox, Elevation, HTMLSelect, Slider, Tag } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { scopeRuns, scopeTurns } from '../data/filters';
import { EChart } from '../components/EChart';
import { orderedRequests } from '../charts/ordered';
import { AGENT_TYPE_ORDER } from '../charts/agentSymbols';
import { costTimelineOption } from '../charts/costTimeline';
import { breakdownData, hitRateData, COMPOSE_MODES } from '../charts/contextBreakdown';
import { contextOption } from '../charts/contextOption';
import { ContextTextPanel } from '../components/ContextTextPanel';
import type { CtxSelection } from '../components/ContextTextPanel';

export function Section3View() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask, setOverrideSingle } = useFilter();
  const { mode } = useTheme();
  const [compose, setCompose] = useState('context');
  const [group, setGroup] = useState('agent');
  const [hitrate, setHitrate] = useState(true);
  const [density, setDensity] = useState(100);
  const [sel, setSel] = useState<Record<string, CtxSelection | null>>({});
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  if (!variant || !data) return null;

  const s3 = effective('s3');
  const runs = scopeRuns(data.runs, effectiveTask('s3'), s3);
  const turns = scopeTurns(data.turns, effectiveTask('s3'), s3);
  const singleAgent = s3.agent.length === 1 ? s3.agent[0] : 'all';
  const mdef = COMPOSE_MODES[compose as 'context' | 'source' | 'token'] ?? COMPOSE_MODES.context;

  return (
    <div className="view view-stack">
      <Card elevation={Elevation.ZERO} className="panel-card">
        <div className="rail-head"><span className="rail-name">Feature (single run)</span></div>
        <div className="rail-chips">
          {variant.conditions.map((c) => (
            <Tag key={c} interactive round minimal={!s3.condition.includes(c)} intent={s3.condition.includes(c) ? 'primary' : 'none'}
              role="button" aria-pressed={s3.condition.includes(c)} onClick={() => setOverrideSingle('s3', 'condition', c)}>{c}</Tag>
          ))}
        </div>
        <div className="s3-controls">
          <label>bar density<Slider min={0} max={100} stepSize={1} labelRenderer={false} value={density} onChange={setDensity} /></label>
          <label>compose by<HTMLSelect value={compose} onChange={(e) => setCompose(e.currentTarget.value)}>
            <option value="context">/context</option><option value="source">source (detailed)</option><option value="token">token type</option></HTMLSelect></label>
          <label>group<HTMLSelect value={group} onChange={(e) => setGroup(e.currentTarget.value)}>
            <option value="agent">agent type</option><option value="none">none</option></HTMLSelect></label>
          <Checkbox checked={hitrate} onChange={(e) => setHitrate(e.currentTarget.checked)} label="cache hit rate" />
        </div>
      </Card>
      {runs.map((run) => {
        const rowsForRun = turns.filter((t) => t.run_id === run.run_id).sort((a, b) => a.request_index - b.request_index);
        const typeByIndex = new Map<number, string>(rowsForRun.map((t, i) => [i, t.request_type ?? 'main-agent']));
        const ordered = orderedRequests(typeByIndex, rowsForRun.map((_, i) => i), singleAgent, group, AGENT_TYPE_ORDER);
        const barMaxWidth = Math.max(6, Math.round(6 + 40 * (density / 100)));
        const bd = breakdownData(mdef, rowsForRun, data.components.filter((c) => c.run_id === run.run_id));
        const hitData = hitrate ? hitRateData(rowsForRun, ordered) : [];
        return (
          <Card elevation={Elevation.ZERO} className="panel-card" key={run.run_id}>
            <div className="panel-head"><h2 className="panel-title">{run.task} / {run.condition} / r{run.rep}</h2><span className="run-tag">{run.run_id}</span></div>
            <h3 className="cache-sub">Per-Run Request Cost Timeline</h3>
            <EChart className="chart" themeMode={mode} option={costTimelineOption(rowsForRun, ordered, barMaxWidth)} />
            <h3 className="cache-sub">Context Source Breakdown</h3>
            <EChart className="chart tall" themeMode={mode} option={contextOption(bd, ordered, hitrate, hitData)}
              onClick={mdef.clickable ? (p) => { const pos = ordered.indexes[p.dataIndex]; const row = rowsForRun[pos]; if (!row) return;
                setSel((s) => ({ ...s, [run.run_id]: { component: p.seriesName, requestIndex: row.request_index, type: String(row.request_type ?? 'main-agent'), tokens: bd.byKey.get(`${pos}:${p.seriesName}`) ?? 0 } })); } : undefined} />
            <ContextTextPanel runId={run.run_id} selection={mdef.clickable ? (sel[run.run_id] ?? null) : null} />
          </Card>
        );
      })}
    </div>
  );
}
```
Add to `tokens.css`: `.s3-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; margin-top: 12px; } .s3-controls label { display: flex; align-items: center; gap: 6px; font-family: var(--app-mono); font-size: 11px; text-transform: uppercase; color: var(--app-muted); } .run-tag { font-family: var(--app-mono); font-size: 11px; color: var(--app-muted); }`

- [ ] **Step 4: Run tests** — `npx vitest run src/views/Section3View.test.tsx` → PASS. `npm test` → green.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/views/Section3View.tsx web/app/src/views/Section3View.test.tsx web/app/src/theme/tokens.css
git commit -m "feat(web): §3 single-run view with single-select Feature override"
```

---

## Phase 3 — Integration & cleanup

### Task 14: Wire `App.tsx`; restyle TokenGate + ContextTextPanel

**Files:**
- Modify: `web/app/src/App.tsx`
- Modify: `web/app/src/components/TokenGate.tsx`
- Modify: `web/app/src/components/ContextTextPanel.tsx`

**Interfaces:**
- Consumes: `AppStateProvider`, `AppShell`, `ViewNav`, `ViewCanvas`, `FilterRail`, the four views, existing `DataProvider`/`useData`/`TokenGate`.
- Produces: the live app — `DataProvider` → `Gate` → `AppStateProvider` → `AppShell` (rail=`FilterRail`, canvas=`ViewNav`+`ViewCanvas`). `Gate` still handles `loading/need-token/error`.

- [ ] **Step 1: Rewrite `App.tsx`**
```tsx
import { DataProvider, useData } from './data/DataContext';
import { TokenGate } from './components/TokenGate';
import { AppStateProvider } from './state/AppStateProvider';
import { AppShell } from './components/shell/AppShell';
import { FilterRail } from './components/shell/FilterRail';
import { ViewNav } from './components/shell/ViewNav';
import { ViewCanvas } from './components/shell/ViewCanvas';
import { OverviewView } from './views/OverviewView';
import { Section1View } from './views/Section1View';
import { Section2View } from './views/Section2View';
import { Section3View } from './views/Section3View';
import type { ViewKey } from './types';

function Dashboard() {
  const { data } = useData();
  if (!data) return null;
  const views: Record<ViewKey, JSX.Element> = {
    overview: <OverviewView />, s1: <Section1View />, s2: <Section2View />, s3: <Section3View />,
  };
  return (
    <AppStateProvider manifest={data.manifest}>
      <AppShell manifest={data.manifest} sidebar={<FilterRail />}
        canvas={<><ViewNav /><ViewCanvas views={views} /></>} />
    </AppStateProvider>
  );
}
function Gate() {
  const { status, data, error } = useData();
  if (status === 'loading') return <div className="app-root"><p className="bp5-running-text" style={{ padding: 24 }}>Loading…</p></div>;
  if (status === 'need-token') return <TokenGate />;
  if (status === 'error') return <div className="app-root"><p style={{ padding: 24 }}>Failed to load: {error}</p></div>;
  if (status === 'ready' && data) return <Dashboard />;
  return null;
}
export default function App() { return <DataProvider><Gate /></DataProvider>; }
```

- [ ] **Step 2: Restyle `TokenGate.tsx`** — keep its existing token-submit logic (read the current file first), but render with Blueprint `Card`, `InputGroup`, `Button` inside a `.app-root` wrapper. Preserve the input's accessible label and submit behavior so any existing TokenGate test (selecting by label/role) still passes.

- [ ] **Step 3: Restyle `ContextTextPanel.tsx`** — keep its props (`runId`, `selection: CtxSelection|null`) and logic; swap the outer markup to a Blueprint `Callout`/`Card` and token-driven classes. Keep existing text/headers so `ContextTextPanel.test.tsx` still passes (adjust selectors to role/text if needed).

- [ ] **Step 4: Verify** — Run `npm test`. Expected: green **except** old `Section1/2/3`, `Masthead`, `KpiBand`, `BriefBand`, `GlobalTaskStrip`, `FilterChunk` tests that reference removed props/`AppState`. Leave those failing **only if** they now fail to compile — if so, this task's build is red; proceed directly to Task 15 (deletion) in the same work session and do not commit a red state. If they still pass (old components untouched), commit now.

- [ ] **Step 5: Commit**
```bash
git add web/app/src/App.tsx web/app/src/components/TokenGate.tsx web/app/src/components/ContextTextPanel.tsx
git commit -m "feat(web): wire app shell + views; restyle TokenGate + ContextTextPanel"
```

---

### Task 15: Remove superseded components; finalize test suite

**Files:**
- Delete: `web/app/src/components/{Masthead,GlobalTaskStrip,KpiBand,BriefBand,Section1,Section2,Section3,Chip,FilterChunk}.tsx` and their `.test.tsx`; `web/app/src/state/appState.ts` + `appState.test.ts`; the salvaged-but-unused `BriefBand`/`KpiBand` only if fully replaced.
- Modify: `web/app/src/types.ts` (remove the deprecated `AppState/Dimension/ScopeKey` block re-added in T4 Step 5).

**Interfaces:** none new. After this task the only state module is `uiState.ts` + `AppStateProvider.tsx`.

- [ ] **Step 1: Delete superseded files**
```bash
cd web/app
git rm src/components/Masthead.tsx src/components/Masthead.test.tsx \
  src/components/GlobalTaskStrip.tsx \
  src/components/KpiBand.tsx src/components/KpiBand.test.tsx \
  src/components/BriefBand.tsx src/components/BriefBand.test.tsx \
  src/components/Section1.tsx src/components/Section1.test.tsx \
  src/components/Section2.tsx src/components/Section2.test.tsx src/components/Section2.charts.test.tsx \
  src/components/Section3.tsx src/components/Section3.charts.test.tsx \
  src/components/Chip.tsx src/components/FilterChunk.tsx src/components/FilterChunk.test.tsx \
  src/state/appState.ts src/state/appState.test.ts
```
> If `BriefBand`/`KpiBand` logic is still referenced anywhere, `grep -rn "BriefBand\|KpiBand\|FilterChunk\|appState\|Masthead" web/app/src` returns only the deletions above. Resolve any stray import before continuing.

- [ ] **Step 2: Remove the deprecated types block** from `types.ts` (the `Dimension/ScopeKey/AppState` lines added in Task 4 Step 5).

- [ ] **Step 3: Verify build + full suite**

Run: `npm run build` → Expected: succeeds (no dangling imports).
Run: `npm test` → Expected: all green. Fix any remaining selector that targets a removed `.fstrip`/`.chip`/`.band` class by switching to role/text.

- [ ] **Step 4: Commit**
```bash
git add -A
git commit -m "refactor(web): remove pre-redesign components and per-section state"
```

---

### Task 16: Theming/a11y/responsive polish + manual smoke

**Files:**
- Modify: `web/app/src/theme/tokens.css` and any view as needed (frontend-design pass).
- Delete: `web/app/src/styles.css` and its import in `main.tsx` (its rules are superseded by `tokens.css` + Blueprint).

**Interfaces:** none.

- [ ] **Step 1: Apply the `frontend-design` skill** for a deliberate visual pass — spacing scale, type hierarchy (IBM Plex Mono labels vs Sans body), card density, rail rhythm, focus rings, and a distinctive (non-default-Blueprint) accent. Verify both `.bp5-dark` and light read well; check chart legibility on dark (axis/grid from the registered themes).

- [ ] **Step 2: Remove the legacy stylesheet**

Delete `src/styles.css`; remove its `import './styles.css'` from `main.tsx`. Run `npm run build` and `npm test` → Expected: both green (no rule depends on `styles.css`).

- [ ] **Step 3: A11y + responsive checks**

Verify: tab order through TopBar → rail → view; the theme `Switch` and filter `Tag`s are keyboard-operable with visible focus; at ≤880px the rail stacks above the canvas. Fix issues found.

- [ ] **Step 4: Manual smoke (both themes)**

Run a local backend (`make serve` from worktree root after `make analyze`) and `npm run dev`. Confirm: all four views render; toggling theme re-themes chrome **and** charts; global filters cross-apply; §3 Feature stays single-select; a deep-link hash (`#report=…&theme=dark&view=s3&condition=…`) restores state on reload; reload button refetches. Record the result.

- [ ] **Step 5: Commit**
```bash
git add -A
git commit -m "polish(web): frontend-design pass, drop legacy stylesheet, a11y/responsive"
```

---

## Self-Review

**Spec coverage:**
- Blueprint.js + light/dark tokens → T1, T2, T3, tokens.css throughout. ✓
- App shell + left filter rail + views → T7 (shell), T8 (rail), T9 (nav), T10–T13 (views). ✓
- Global cross-filter + per-view override (§3 single-select) → T4 (`effectiveSel`/`setOverrideSingle`), T8 (global rail), T13 (override). ✓
- URL deep-linking of report/view/theme/filter → T5, T6. ✓
- Salvaged modules unchanged → charts/data/api consumed in T10–T13; only `echartsTheme.ts` refactored (T2) and `EChart` (T3). ✓
- ECharts re-themed for light/dark → T2 (themes), T3 (re-init), threaded via `themeMode` in every view. ✓
- Backend out of scope → no `web/api` task. ✓
- Overview as a new view → T10. ✓
- Testing strategy (role/text, pure logic kept, new context/url/view tests) → T4–T13 tests; T15/T16 sweep. ✓
- Definition of done (green suite, build, manual smoke both themes) → T16. ✓

**Placeholder scan:** No "TBD/TODO". T2 Step 4, T14 Steps 2–3, and T16 Step 1 reference reading the current file / applying frontend-design rather than inlining final CSS — these are intentional (logic-preserving restyles + the aesthetic pass the spec mandates), each with concrete acceptance criteria (tests stay green; props/labels preserved), not deferred work.

**Type consistency:** `UiState`/`GlobalFilter`/`SectionSel`/`ViewKey`/`ThemeMode` defined in T4 `types.ts` and used identically in T5/T6/T8/T10–T13. `effectiveSel`→`{condition,rep,agent}` matches `scopeRuns`/`scopeTurns` (`data/filters.ts`) signatures. `useFilter().effective/effectiveTask/setOverrideSingle/toggle/clear` names match between T6 (definition) and T8/T10–T13 (use). `EChart` `themeMode` prop name matches T3 (definition) and all view call sites. `reportThemeName`/`registerReportThemes`/`REPORT_LIGHT`/`REPORT_DARK` match between T2 and T3.
