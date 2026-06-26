# Report Frontend SPA — Plan 2a (App Shell) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Vite + React + TypeScript SPA shell that **reproduces the exact layout (版式) of the current `reports/report.html`** — single centered column, sticky global Task strip, masthead with report switcher, §0 brief band, KPI band, and the §1/§2/§3 band scaffolds with their per-section filter strips and selectors — authenticating against the backend API and loading all data. Charts go inside the (already-present) panels in Plans 2b/2c.

**Architecture:** A greenfield `web/` app (Vite 5, React 18, TS, Vitest). The **real stylesheet is ported verbatim** from `reports/report.html` and components emit the **same class names / DOM structure** the report uses (`.masthead`, `.fstrip`, `.band`, `.panel`, `.chart`, `.kpi`, `.brief`, …). State is **scoped per section** to mirror the report: a global `task` plus independent `condition/rep/agent` selections for §1/§2/§3. Pure logic (API client, URL state, state toggles, filter derivation, KPI compute) is TDD'd; components are tested with React Testing Library. Charts and §3 internals are out of scope (Plans 2b/2c).

**Tech Stack:** Vite ^5.4, React ^18.3, TypeScript ^5.5, Vitest ^2.1, @testing-library/react ^16, jsdom ^25, **echarts ^6.0** (installed now, used in 2b). npm. Node 18.

**Layout source of truth:** `reports/report.html` (the rendered report). **Behavioral truth:** `analysis/echarts_report.py`. **Variants/copy:** `analysis/report_variants.py`. **API contract (Plan 1):** `serve/app.py`.

## Global Constraints

- **App lives in `web/`** (repo root); Vercel project root = `web/`. **Node 18** — do NOT use Vite 6/7 or any dep requiring Node 20+.
- **Reproduce the report layout exactly.** Port the stylesheet from `reports/report.html` verbatim into `web/src/styles.css`; components must emit the same class names and DOM nesting the report uses. Do NOT invent new styling.
- **TypeScript strict mode.** No `any` except a commented escape hatch.
- **API base** = `import.meta.env.VITE_API_BASE` (default `''`). **Token** entered at runtime, stored in `localStorage` key `cc_report_token`; never hard-coded.
- **Scoped state (mirror the report's `SEL`):** global `task: string[]`; per-section `s1/s2/s3` each `{condition, rep, agent}` (§1 uses only `condition`). Empty array in any dimension = "all".
- **URL hash persists ONLY `report` + `task`:** `#report=<key>&task=a,b` (raw commas; empty omitted). Section filters are NOT persisted.
- **rep tokens are `r<N>`** in chips; `rep` columns are ints — convert with `` `r${rep}` ``.
- **Two reports** from `manifest.variants` (`multi_agent`, `long_horizon`); switching resets the active report and its section filters to empty.
- Tests run via `npm test` (`vitest run`); every task ends green with pristine output.
- **Out of scope (Plans 2b/2c):** all ECharts charts and their data-shaping; the §3 context-source breakdown internals (compose/group/density/cache-overlay/clickable text); the §0 prompt **text** wiring (needs a backend `page` field — see Task 7 note). 2a renders the panels/controls as the shell; charts and prompt-text content come later.

## File Structure

| File | Responsibility |
|---|---|
| `web/package.json`, `web/vite.config.ts`, `web/tsconfig*.json`, `web/index.html` | Scaffold + Vitest config + font links |
| `web/src/main.tsx`, `web/src/styles.css` | Entry + **ported report stylesheet** |
| `web/src/test/setup.ts` | Vitest/jsdom/jest-dom setup |
| `web/src/types.ts` | Run/Turn/Component/ComponentText/Variant/Manifest + `AppState`/`SectionSel`/`Dimension`/`ScopeKey` |
| `web/src/api/token.ts`, `web/src/api/client.ts` | Token store; `apiGet` + fetchers + `ApiError` |
| `web/src/state/urlState.ts` | `parseHash`/`toHash` (report + task only) |
| `web/src/state/appState.ts` | `initState`, `toggleTask`, `toggleSection`, `clearTask`, `clearSection`, `setReport` |
| `web/src/data/filters.ts` | `scopeRuns`, `scopeTurns`, `presentAgentTypes` |
| `web/src/data/kpis.ts` | `computeKpis(runs)` |
| `web/src/data/DataContext.tsx` | `DataProvider` + `useData` (load state machine) |
| `web/src/components/TokenGate.tsx` | Token input on 401 |
| `web/src/components/Chip.tsx`, `web/src/components/FilterChunk.tsx` | Reusable `.chip` + `.fchunk` (tag + "all" + chips) |
| `web/src/components/Masthead.tsx` | `.masthead` gradient + `.switcher` tabs |
| `web/src/components/GlobalTaskStrip.tsx` | sticky `.fstrip.fstrip-global` with the Task chunk |
| `web/src/components/BriefBand.tsx` | §0 `.band-brief` briefs + `.strat-legend` |
| `web/src/components/KpiBand.tsx` | `.kpis` 5-card band |
| `web/src/components/Section1.tsx`, `Section2.tsx`, `Section3.tsx` | band scaffolds + filter strips + selectors + empty chart panels |
| `web/src/theme.ts` | `CONDITION_COLORS`, `SOURCE_COLORS`, helpers |
| `web/src/App.tsx` | Composition + `AppState` + URL sync |
| `web/README.md`, `web/.gitignore` | docs + ignores |

---

### Task 1: Scaffold + ported stylesheet + fonts

**Files:** Create `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/tsconfig.node.json`, `web/index.html`, `web/src/main.tsx`, `web/src/styles.css`, `web/src/App.tsx`, `web/src/test/setup.ts`, `web/.gitignore`, `web/src/smoke.test.ts`.

**Interfaces:** Produces a buildable app; `npm test`, `npm run build` succeed. `App` is a default-export React component. `styles.css` is the report's stylesheet verbatim.

- [ ] **Step 1: Create `web/package.json`**

```json
{
  "name": "cc-report-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "echarts": "^6.0.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.8",
    "@testing-library/react": "^16.0.1",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^25.0.0",
    "typescript": "^5.5.4",
    "vite": "^5.4.2",
    "vitest": "^2.1.1"
  }
}
```

- [ ] **Step 2: Create `web/vite.config.ts`**

```ts
/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', globals: true, setupFiles: './src/test/setup.ts', css: false },
});
```

- [ ] **Step 3: Create `web/tsconfig.json` and `web/tsconfig.node.json`**

`web/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020", "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"], "module": "ESNext",
    "skipLibCheck": true, "moduleResolution": "bundler",
    "allowImportingTsExtensions": true, "resolveJsonModule": true,
    "isolatedModules": true, "noEmit": true, "jsx": "react-jsx",
    "strict": true, "noUnusedLocals": true, "noUnusedParameters": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```
`web/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true, "skipLibCheck": true, "module": "ESNext",
    "moduleResolution": "bundler", "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create `web/index.html`** (IBM Plex font links copied from `reports/report.html` lines 7–9; ECharts comes from npm, not the CDN)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Claude Code · Orchestration Telemetry</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Port the report stylesheet verbatim into `web/src/styles.css`**

From the **repo root**, extract the contents of the report's `<style>` block (everything between `<style>` and `</style>`):
```bash
sed -n '/^  <style>/,/^  <\/style>/p' reports/report.html | sed '1d;$d' > web/src/styles.css
```
Verify it starts with `:root {` and ends with the `@media (prefers-reduced-motion...)` block:
```bash
head -1 web/src/styles.css && tail -3 web/src/styles.css
```
Expected: first line `    :root {`; last lines the closing `}` of the reduced-motion media query. (This is the report's exact CSS — the SPA's visual parity comes from this file.)

- [ ] **Step 6: Create `web/src/main.tsx` and a placeholder `web/src/App.tsx`**

`web/src/main.tsx`:
```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```
`web/src/App.tsx` (replaced in Task 6):
```tsx
export default function App() {
  return <main>Claude Code · Orchestration Telemetry</main>;
}
```

- [ ] **Step 7: Create `web/src/test/setup.ts`, `web/src/smoke.test.ts`, `web/.gitignore`**

`web/src/test/setup.ts`:
```ts
import '@testing-library/jest-dom/vitest';
```
`web/src/smoke.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
describe('toolchain', () => {
  it('runs vitest', () => { expect(1 + 1).toBe(2); });
});
```
`web/.gitignore`:
```
node_modules
dist
.vercel
*.local
```

- [ ] **Step 8: Install and verify**

Run: `cd web && npm install && npm test && npm run build`
Expected: `1 passed`; build writes `web/dist/`. Peer-dep warnings are fine if test+build pass.

- [ ] **Step 9: Commit**

```bash
git add web/package.json web/package-lock.json web/vite.config.ts web/tsconfig.json web/tsconfig.node.json web/index.html web/src/main.tsx web/src/styles.css web/src/App.tsx web/src/test/setup.ts web/src/smoke.test.ts web/.gitignore
git commit -m "feat(web): scaffold vite+react+ts app with report stylesheet ported verbatim"
```

---

### Task 2: Types, token store, API client

**Files:** Create `web/src/types.ts`, `web/src/api/token.ts`, `web/src/api/client.ts`, `web/src/api/client.test.ts`.

**Interfaces:**
- `types.ts`: `Run`, `Turn`, `Component`, `ComponentText`, `Variant`, `Manifest`, plus `Dimension = 'condition'|'rep'|'agent'`, `SectionSel { condition; rep; agent }`, `ScopeKey = 's1'|'s2'|'s3'`, `AppState { report; task; s1; s2; s3 }`.
- `token.ts`: `getToken()`, `setToken(t)`, `clearToken()`.
- `client.ts`: `class ApiError extends Error { status }`; `apiBase()`; `apiGet<T>(path)`; `getManifest/getRuns/getTurns/getComponents/getTokenRates/getComponentTexts(runId, requestIndex?)`.

- [ ] **Step 1: Create `web/src/types.ts`**

```ts
export interface Run {
  run_id: string; task: string; condition: string; rep: number;
  success: boolean; speedup: number | null; total_cost_usd: number | null;
  num_requests: number | null; cache_hit_ratio: number | null;
  quality_score: number | null; research_rubric_score: number | null;
  [key: string]: unknown;
}
export interface Turn {
  run_id: string; task: string; condition: string; rep: number;
  request_index: number; request_type: string | null;
  input_tokens: number; output_tokens: number; cache_read: number;
  cache_creation_5m: number; cache_creation_1h: number;
  ttft_s: number | null; total_s: number | null;
  [key: string]: unknown;
}
export interface Component {
  run_id: string; task: string; condition: string; rep: number;
  request_index: number; request_type: string | null;
  component: string; est_tokens: number; bytes: number;
}
export interface ComponentText {
  run_id: string; request_index: number; component: string;
  request_type: string | null; text: string; truncated: boolean;
  bytes: number; stable: boolean;
}
export interface Variant {
  key: string; eyebrow: string; title: string; lede: string;
  conditions: string[]; tasks: string[];
}
export interface Manifest {
  variants: Variant[];
  strategy_desc: Record<string, string>;
  task_meta: Record<string, { title: string; measures: string }>;
  available: { task: string; condition: string; runs: number }[];
}

export type Dimension = 'condition' | 'rep' | 'agent';
export type ScopeKey = 's1' | 's2' | 's3';
export interface SectionSel { condition: string[]; rep: string[]; agent: string[]; }
export interface AppState {
  report: string;
  task: string[];
  s1: SectionSel; s2: SectionSel; s3: SectionSel;
}
```

- [ ] **Step 2: Create `web/src/api/token.ts`**

```ts
const KEY = 'cc_report_token';
export function getToken(): string { return localStorage.getItem(KEY) ?? ''; }
export function setToken(t: string): void { localStorage.setItem(KEY, t); }
export function clearToken(): void { localStorage.removeItem(KEY); }
```

- [ ] **Step 3: Write the failing test** — `web/src/api/client.test.ts`

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiGet, getManifest } from './client';
import { setToken } from './token';

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({ status, ok: status >= 200 && status < 300, json: async () => body });
}

describe('apiGet', () => {
  beforeEach(() => { localStorage.clear(); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('sends the bearer token and returns json', async () => {
    setToken('secret123');
    const fetchMock = mockFetch(200, [{ run_id: 'r1' }]);
    vi.stubGlobal('fetch', fetchMock);
    const data = await apiGet<{ run_id: string }[]>('/api/runs');
    expect(data).toEqual([{ run_id: 'r1' }]);
    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers.Authorization).toBe('Bearer secret123');
  });
  it('throws ApiError(401) on unauthorized', async () => {
    vi.stubGlobal('fetch', mockFetch(401, {}));
    await expect(getManifest()).rejects.toMatchObject({ name: 'ApiError', status: 401 });
  });
  it('throws ApiError on other non-ok status', async () => {
    vi.stubGlobal('fetch', mockFetch(500, {}));
    await expect(apiGet('/api/runs')).rejects.toBeInstanceOf(ApiError);
  });
});
```

- [ ] **Step 4: Run to verify it fails**

Run: `cd web && npx vitest run src/api/client.test.ts`
Expected: FAIL — cannot resolve `./client`.

- [ ] **Step 5: Create `web/src/api/client.ts`**

```ts
import type { Component, ComponentText, Manifest, Run, Turn } from '../types';
import { getToken } from './token';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message); this.name = 'ApiError'; this.status = status;
  }
}
export function apiBase(): string {
  return (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
}
export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (res.status === 401) throw new ApiError(401, 'unauthorized');
  if (!res.ok) throw new ApiError(res.status, `request failed: ${res.status}`);
  return (await res.json()) as T;
}
export const getManifest = () => apiGet<Manifest>('/api/manifest');
export const getRuns = () => apiGet<Run[]>('/api/runs');
export const getTurns = () => apiGet<Turn[]>('/api/turns');
export const getComponents = () => apiGet<Component[]>('/api/components');
export const getTokenRates = () => apiGet<Record<string, number>>('/api/token-rates');
export const getComponentTexts = (runId: string, requestIndex?: number) =>
  apiGet<ComponentText[]>(
    `/api/component-texts?run_id=${encodeURIComponent(runId)}` +
      (requestIndex != null ? `&request_index=${requestIndex}` : ''),
  );
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd web && npx vitest run src/api/client.test.ts`
Expected: PASS (3).

- [ ] **Step 7: Commit**

```bash
git add web/src/types.ts web/src/api/token.ts web/src/api/client.ts web/src/api/client.test.ts
git commit -m "feat(web): types, token store, and API client"
```

---

### Task 3: URL state (report + task)

**Files:** Create `web/src/state/urlState.ts`, `web/src/state/urlState.test.ts`.

**Interfaces:**
- `UrlState { report: string | null; task: string[] }`.
- `parseHash(hash: string): UrlState`; `toHash(u: UrlState): string` — only `report` + `task`; raw commas; empty task omitted.

- [ ] **Step 1: Write the failing tests** — `web/src/state/urlState.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import { parseHash, toHash } from './urlState';

describe('urlState', () => {
  it('serializes report + task with raw commas', () => {
    expect(toHash({ report: 'multi_agent', task: ['coding', 'research'] }))
      .toBe('#report=multi_agent&task=coding,research');
  });
  it('omits empty task', () => {
    expect(toHash({ report: 'long_horizon', task: [] })).toBe('#report=long_horizon');
  });
  it('round-trips', () => {
    const u = { report: 'multi_agent', task: ['coding'] };
    expect(parseHash(toHash(u))).toEqual(u);
  });
  it('parses empty hash', () => {
    expect(parseHash('')).toEqual({ report: null, task: [] });
  });
  it('tolerates leading # and missing keys', () => {
    expect(parseHash('#report=long_horizon')).toEqual({ report: 'long_horizon', task: [] });
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run src/state/urlState.test.ts`
Expected: FAIL — cannot resolve `./urlState`.

- [ ] **Step 3: Create `web/src/state/urlState.ts`**

```ts
export interface UrlState { report: string | null; task: string[]; }

export function parseHash(hash: string): UrlState {
  const h = hash.replace(/^#/, '');
  const get = (key: string): string | null => {
    for (const seg of h.split('&')) {
      if (!seg) continue;
      const eq = seg.indexOf('=');
      if (eq !== -1 && seg.slice(0, eq) === key) return seg.slice(eq + 1);
    }
    return null;
  };
  const task = get('task');
  return { report: get('report'), task: task ? task.split(',').filter(Boolean) : [] };
}

export function toHash(u: UrlState): string {
  const parts: string[] = [];
  if (u.report) parts.push(`report=${u.report}`);
  if (u.task.length) parts.push(`task=${u.task.join(',')}`);
  return parts.length ? `#${parts.join('&')}` : '';
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run src/state/urlState.test.ts`
Expected: PASS (5).

- [ ] **Step 5: Commit**

```bash
git add web/src/state/urlState.ts web/src/state/urlState.test.ts
git commit -m "feat(web): URL-hash state (report + task)"
```

---

### Task 4: App state model + filter derivation

**Files:** Create `web/src/state/appState.ts`, `web/src/data/filters.ts`, `web/src/state/appState.test.ts`, `web/src/data/filters.test.ts`.

**Interfaces:**
- `appState.ts`:
  - `emptySection(): SectionSel`
  - `initState(report: string, task: string[]): AppState` (sections empty)
  - `setReport(state, report): AppState` (resets task + all sections to empty)
  - `toggleTask(state, token): AppState`
  - `clearTask(state): AppState`
  - `toggleSection(state, scope: ScopeKey, dim: Dimension, token): AppState`
  - `clearSection(state, scope: ScopeKey, dim: Dimension): AppState`
- `filters.ts`:
  - `scopeRuns(runs, task: string[], sel: SectionSel): Run[]` (task + condition + rep)
  - `scopeTurns(turns, task: string[], sel: SectionSel): Turn[]` (+ agent)
  - `presentAgentTypes(turns): string[]`

- [ ] **Step 1: Write the failing tests for appState** — `web/src/state/appState.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import { clearSection, initState, setReport, toggleSection, toggleTask } from './appState';

describe('appState', () => {
  it('initializes with empty sections', () => {
    const s = initState('multi_agent', ['coding']);
    expect(s).toEqual({
      report: 'multi_agent', task: ['coding'],
      s1: { condition: [], rep: [], agent: [] },
      s2: { condition: [], rep: [], agent: [] },
      s3: { condition: [], rep: [], agent: [] },
    });
  });
  it('toggleTask adds then removes', () => {
    let s = initState('r', []);
    s = toggleTask(s, 'coding');
    expect(s.task).toEqual(['coding']);
    s = toggleTask(s, 'coding');
    expect(s.task).toEqual([]);
  });
  it('toggleSection only affects the named scope+dimension', () => {
    let s = initState('r', []);
    s = toggleSection(s, 's2', 'condition', 'subagents');
    expect(s.s2.condition).toEqual(['subagents']);
    expect(s.s1.condition).toEqual([]);
    expect(s.s3.condition).toEqual([]);
  });
  it('clearSection empties one dimension', () => {
    let s = toggleSection(initState('r', []), 's3', 'rep', 'r1');
    s = clearSection(s, 's3', 'rep');
    expect(s.s3.rep).toEqual([]);
  });
  it('setReport resets task and all sections', () => {
    let s = toggleSection(initState('a', ['coding']), 's2', 'agent', 'main-agent');
    s = setReport(s, 'b');
    expect(s).toEqual(initState('b', []));
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run src/state/appState.test.ts`
Expected: FAIL — cannot resolve `./appState`.

- [ ] **Step 3: Create `web/src/state/appState.ts`**

```ts
import type { AppState, Dimension, ScopeKey, SectionSel } from '../types';

export function emptySection(): SectionSel { return { condition: [], rep: [], agent: [] }; }

export function initState(report: string, task: string[]): AppState {
  return { report, task, s1: emptySection(), s2: emptySection(), s3: emptySection() };
}

export function setReport(_state: AppState, report: string): AppState {
  return initState(report, []); // switching reports resets task + all section filters
}

function toggleInList(list: string[], token: string): string[] {
  return list.includes(token) ? list.filter((x) => x !== token) : [...list, token];
}

export function toggleTask(state: AppState, token: string): AppState {
  return { ...state, task: toggleInList(state.task, token) };
}
export function clearTask(state: AppState): AppState {
  return { ...state, task: [] };
}
export function toggleSection(state: AppState, scope: ScopeKey, dim: Dimension, token: string): AppState {
  const sec = state[scope];
  return { ...state, [scope]: { ...sec, [dim]: toggleInList(sec[dim], token) } };
}
export function clearSection(state: AppState, scope: ScopeKey, dim: Dimension): AppState {
  return { ...state, [scope]: { ...state[scope], [dim]: [] } };
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run src/state/appState.test.ts`
Expected: PASS (5).

- [ ] **Step 5: Write the failing tests for filters** — `web/src/data/filters.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import type { Run, SectionSel, Turn } from '../types';
import { presentAgentTypes, scopeRuns, scopeTurns } from './filters';

const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1 },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2 },
  { run_id: 'c', task: 'research', condition: 'single_agent', rep: 1 },
] as unknown as Run[];
const turns = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent' },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2, request_type: 'task-subagent' },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2, request_type: null },
] as unknown as Turn[];
const sec = (o: Partial<SectionSel>): SectionSel => ({ condition: [], rep: [], agent: [], ...o });

describe('filters', () => {
  it('empty section + empty task returns all', () => {
    expect(scopeRuns(runs, [], sec({}))).toHaveLength(3);
  });
  it('global task + section condition narrow runs', () => {
    expect(scopeRuns(runs, ['coding'], sec({ condition: ['subagents'] })).map((r) => r.run_id)).toEqual(['b']);
  });
  it('rep matches r-prefixed token', () => {
    expect(scopeRuns(runs, [], sec({ rep: ['r1'] })).map((r) => r.run_id)).toEqual(['a', 'c']);
  });
  it('scopeTurns filters by agent and drops null when agent set', () => {
    expect(scopeTurns(turns, [], sec({ agent: ['task-subagent'] })).map((t) => t.run_id)).toEqual(['b']);
  });
  it('presentAgentTypes returns sorted distinct non-null', () => {
    expect(presentAgentTypes(turns)).toEqual(['main-agent', 'task-subagent']);
  });
});
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd web && npx vitest run src/data/filters.test.ts`
Expected: FAIL — cannot resolve `./filters`.

- [ ] **Step 7: Create `web/src/data/filters.ts`**

```ts
import type { Run, SectionSel, Turn } from '../types';

const inSel = (values: string[], v: string): boolean => values.length === 0 || values.includes(v);

export function scopeRuns(runs: Run[], task: string[], sel: SectionSel): Run[] {
  return runs.filter(
    (r) => inSel(task, r.task) && inSel(sel.condition, r.condition) && inSel(sel.rep, `r${r.rep}`),
  );
}
export function scopeTurns(turns: Turn[], task: string[], sel: SectionSel): Turn[] {
  return turns.filter(
    (t) =>
      inSel(task, t.task) &&
      inSel(sel.condition, t.condition) &&
      inSel(sel.rep, `r${t.rep}`) &&
      (sel.agent.length === 0 || (t.request_type != null && sel.agent.includes(t.request_type))),
  );
}
export function presentAgentTypes(turns: Turn[]): string[] {
  const set = new Set<string>();
  for (const t of turns) if (t.request_type != null) set.add(t.request_type);
  return Array.from(set).sort();
}
```

- [ ] **Step 8: Run to verify it passes**

Run: `cd web && npx vitest run src/data/filters.test.ts`
Expected: PASS (5).

- [ ] **Step 9: Commit**

```bash
git add web/src/state/appState.ts web/src/state/appState.test.ts web/src/data/filters.ts web/src/data/filters.test.ts
git commit -m "feat(web): scoped app-state model + filter derivation"
```

---

### Task 5: Data provider + token gate

**Files:** Create `web/src/data/DataContext.tsx`, `web/src/components/TokenGate.tsx`, `web/src/data/DataContext.test.tsx`.

**Interfaces:**
- `DataStatus = 'loading'|'ready'|'need-token'|'error'`; `DataBundle { manifest, runs, turns, components, tokenRates }`.
- `DataProvider({ children })`; `useData(): { status, data, error, reload }`.
- `TokenGate()` — password input; on submit stores token + `reload()`. Uses the report's `.token-gate`-style classes is NOT required (no such class exists); keep minimal inline structure.

- [ ] **Step 1: Write the failing test** — `web/src/data/DataContext.test.tsx`

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import * as client from '../api/client';
import { DataProvider, useData } from './DataContext';
import { TokenGate } from '../components/TokenGate';

function Probe() {
  const { status, data } = useData();
  return <div>status:{status} runs:{data ? data.runs.length : 0}</div>;
}
const manifest = { variants: [], strategy_desc: {}, task_meta: {}, available: [] };
function stubAll(impl: () => Promise<unknown>) {
  for (const fn of ['getManifest', 'getRuns', 'getTurns', 'getComponents', 'getTokenRates'] as const) {
    vi.spyOn(client, fn).mockImplementation(impl as never);
  }
}
afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

describe('DataProvider', () => {
  it('loads and exposes ready data', async () => {
    vi.spyOn(client, 'getManifest').mockResolvedValue(manifest as never);
    vi.spyOn(client, 'getRuns').mockResolvedValue([{ run_id: 'r1' }] as never);
    vi.spyOn(client, 'getTurns').mockResolvedValue([] as never);
    vi.spyOn(client, 'getComponents').mockResolvedValue([] as never);
    vi.spyOn(client, 'getTokenRates').mockResolvedValue({} as never);
    render(<DataProvider><Probe /></DataProvider>);
    await waitFor(() => expect(screen.getByText(/status:ready/)).toBeInTheDocument());
    expect(screen.getByText(/runs:1/)).toBeInTheDocument();
  });
  it('enters need-token on 401 and recovers after the gate submits', async () => {
    stubAll(() => Promise.reject(new client.ApiError(401, 'unauthorized')));
    render(<DataProvider><TokenGate /><Probe /></DataProvider>);
    await waitFor(() => expect(screen.getByText(/status:need-token/)).toBeInTheDocument());
    stubAll(() => Promise.resolve([] as never));
    vi.spyOn(client, 'getManifest').mockResolvedValue(manifest as never);
    await userEvent.type(screen.getByLabelText(/access token/i), 'secret123');
    await userEvent.click(screen.getByRole('button', { name: /enter/i }));
    await waitFor(() => expect(screen.getByText(/status:ready/)).toBeInTheDocument());
    expect(localStorage.getItem('cc_report_token')).toBe('secret123');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run src/data/DataContext.test.tsx`
Expected: FAIL — cannot resolve `./DataContext`.

- [ ] **Step 3: Create `web/src/data/DataContext.tsx`**

```tsx
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { ApiError, getComponents, getManifest, getRuns, getTokenRates, getTurns } from '../api/client';
import type { Component, Manifest, Run, Turn } from '../types';

export type DataStatus = 'loading' | 'ready' | 'need-token' | 'error';
export interface DataBundle {
  manifest: Manifest; runs: Run[]; turns: Turn[]; components: Component[]; tokenRates: Record<string, number>;
}
interface DataState { status: DataStatus; data: DataBundle | null; error: string | null; reload: () => void; }

const Ctx = createContext<DataState | null>(null);
export function useData(): DataState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useData must be used within a DataProvider');
  return v;
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<DataStatus>('loading');
  const [data, setData] = useState<DataBundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus('loading'); setError(null);
    try {
      const [manifest, runs, turns, components, tokenRates] = await Promise.all([
        getManifest(), getRuns(), getTurns(), getComponents(), getTokenRates(),
      ]);
      setData({ manifest, runs, turns, components, tokenRates });
      setStatus('ready');
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setStatus('need-token');
      else { setError(e instanceof Error ? e.message : String(e)); setStatus('error'); }
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  return <Ctx.Provider value={{ status, data, error, reload: () => void load() }}>{children}</Ctx.Provider>;
}
```

- [ ] **Step 4: Create `web/src/components/TokenGate.tsx`**

```tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { setToken } from '../api/token';
import { useData } from '../data/DataContext';

export function TokenGate() {
  const { reload } = useData();
  const [value, setValue] = useState('');
  const submit = (e: FormEvent) => { e.preventDefault(); setToken(value.trim()); reload(); };
  return (
    <main style={{ maxWidth: 'var(--maxw)', margin: '0 auto', padding: '40px 28px' }}>
      <form onSubmit={submit} style={{ maxWidth: 360 }}>
        <p>This dashboard is private. Enter the access token to continue.</p>
        <label className="control">access token
          <input type="password" value={value} onChange={(e) => setValue(e.target.value)} style={{ width: '100%' }} />
        </label>
        <button type="submit" className="sb-reset" style={{ marginTop: 10 }}>Enter</button>
      </form>
    </main>
  );
}
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd web && npx vitest run src/data/DataContext.test.tsx`
Expected: PASS (2).

- [ ] **Step 6: Commit**

```bash
git add web/src/data/DataContext.tsx web/src/components/TokenGate.tsx web/src/data/DataContext.test.tsx
git commit -m "feat(web): data provider state machine + token gate"
```

---

### Task 6: Masthead, reusable chips, sticky global Task strip, URL sync

**Files:** Create `web/src/theme.ts`, `web/src/components/Chip.tsx`, `web/src/components/FilterChunk.tsx`, `web/src/components/Masthead.tsx`, `web/src/components/GlobalTaskStrip.tsx`, `web/src/components/Masthead.test.tsx`, `web/src/components/FilterChunk.test.tsx`; replace `web/src/App.tsx`.

**Interfaces:**
- `theme.ts`: `CONDITION_COLORS`, `SOURCE_COLORS` (the report's maps), `conditionColor(c)`.
- `Chip({ label, active, dot?, onClick })` → `<button class="chip"[+" on"]>` with optional `.dot`.
- `FilterChunk({ tag, items, active, onToggle, onClear, dotFor? })` → `.fchunk` (tag + "all" `.ftoggle` + `.chips` of `Chip`).
- `Masthead({ manifest, activeKey, onSwitch })` → `.masthead` with `.switcher` tabs (hidden when one variant); active variant eyebrow/title/lede.
- `GlobalTaskStrip({ tasks, selected, onToggle, onClear })` → `.fstrip.fstrip-global` with one Task `.fchunk`.
- `App` — `DataProvider` → gate → `AppState` synced to URL (report+task), masthead + global task strip rendered; sections wired in Tasks 7–8.

- [ ] **Step 1: Create `web/src/theme.ts`**

```ts
// Mirrors analysis/echarts_report.py conditionColors / sourceColors.
export const CONDITION_COLORS: Record<string, string> = {
  single_agent: '#3b5bdb', goal: '#2f9e44', subagents: '#0c8599',
  ralph_loop: '#e8590c', dynamic_workflow: '#7048e8', loop_dynamic: '#c2255c',
};
export const SOURCE_COLORS: Record<string, string> = {
  'base system prompt': '#3b5bdb', 'builtin tool definitions': '#1098ad',
  'MCP / extension tool definitions': '#15aabf', 'custom agent definitions': '#f76707',
  'CLAUDE.md / project instructions': '#e8590c', 'skills listing': '#7048e8',
  'invoked skill bodies': '#9775fa', 'auto memory': '#2f9e44',
  'hooks / system reminders': '#f59f00', 'user input': '#c2255c',
  'assistant / conversation history': '#868e96', 'tool results / file reads': '#4263eb',
  'subagent summaries': '#a61e4d', 'uncategorized context': '#adb5bd',
};
const PALETTE = ['#3b5bdb', '#0c8599', '#e8590c', '#7048e8', '#c2255c', '#1098ad', '#f59f00'];
export function conditionColor(condition: string, fallbackIndex = 0): string {
  return CONDITION_COLORS[condition] ?? PALETTE[fallbackIndex % PALETTE.length];
}
```

- [ ] **Step 2: Create `web/src/components/Chip.tsx`**

```tsx
interface ChipProps { label: string; active: boolean; dot?: string; onClick: () => void; }
export function Chip({ label, active, dot, onClick }: ChipProps) {
  return (
    <button type="button" className={active ? 'chip on' : 'chip'} aria-pressed={active} onClick={onClick}>
      {dot && <span className="dot" style={{ background: dot }} />}
      {label}
    </button>
  );
}
```

- [ ] **Step 3: Write the failing test for FilterChunk** — `web/src/components/FilterChunk.test.tsx`

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { FilterChunk } from './FilterChunk';

describe('FilterChunk', () => {
  it('renders a tag, an "all" toggle, and a chip per item with active state', () => {
    render(<FilterChunk tag="Feature" items={['single_agent', 'subagents']} active={['subagents']} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getByText('Feature')).toBeInTheDocument();
    expect(screen.getByText('all')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'subagents' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'single_agent' })).toHaveAttribute('aria-pressed', 'false');
  });
  it('calls onToggle(item) and onClear()', async () => {
    const onToggle = vi.fn(); const onClear = vi.fn();
    render(<FilterChunk tag="Feature" items={['single_agent']} active={[]} onToggle={onToggle} onClear={onClear} />);
    await userEvent.click(screen.getByRole('button', { name: 'single_agent' }));
    expect(onToggle).toHaveBeenCalledWith('single_agent');
    await userEvent.click(screen.getByText('all'));
    expect(onClear).toHaveBeenCalled();
  });
});
```

- [ ] **Step 4: Run to verify it fails**

Run: `cd web && npx vitest run src/components/FilterChunk.test.tsx`
Expected: FAIL — cannot resolve `./FilterChunk`.

- [ ] **Step 5: Create `web/src/components/FilterChunk.tsx`**

```tsx
import { Chip } from './Chip';

interface Props {
  tag: string;
  items: string[];
  active: string[];
  onToggle: (item: string) => void;
  onClear: () => void;
  dotFor?: (item: string) => string | undefined;
}
export function FilterChunk({ tag, items, active, onToggle, onClear, dotFor }: Props) {
  return (
    <div className="fchunk">
      <span className="fchunk-tag">{tag}</span>
      <span className="ftoggle" role="button" tabIndex={0} onClick={onClear}>all</span>
      <div className="chips">
        {items.map((it) => (
          <Chip key={it} label={it} active={active.includes(it)} dot={dotFor?.(it)} onClick={() => onToggle(it)} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Write the failing test for Masthead** — `web/src/components/Masthead.test.tsx`

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { Manifest } from '../types';
import { Masthead } from './Masthead';

const manifest: Manifest = {
  variants: [
    { key: 'multi_agent', eyebrow: 'CC · exp', title: 'Multi-agent orchestration', lede: 'lede A', conditions: ['single_agent'], tasks: ['coding'] },
    { key: 'long_horizon', eyebrow: 'CC · exp', title: 'Long-horizon persistence', lede: 'lede B', conditions: ['goal'], tasks: ['coding_longhorizon'] },
  ],
  strategy_desc: {}, task_meta: {}, available: [],
};
describe('Masthead', () => {
  it('renders the active variant and a switcher tab per variant', () => {
    render(<Masthead manifest={manifest} activeKey="multi_agent" onSwitch={() => {}} />);
    expect(screen.getByRole('heading', { name: 'Multi-agent orchestration' })).toBeInTheDocument();
    expect(screen.getByText('lede A')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Long-horizon persistence' })).toBeInTheDocument();
  });
  it('marks the active tab and calls onSwitch on click', async () => {
    const onSwitch = vi.fn();
    render(<Masthead manifest={manifest} activeKey="multi_agent" onSwitch={onSwitch} />);
    expect(screen.getByRole('button', { name: 'Multi-agent orchestration' })).toHaveClass('switch-tab', 'on');
    await userEvent.click(screen.getByRole('button', { name: 'Long-horizon persistence' }));
    expect(onSwitch).toHaveBeenCalledWith('long_horizon');
  });
});
```

- [ ] **Step 7: Run to verify it fails**

Run: `cd web && npx vitest run src/components/Masthead.test.tsx`
Expected: FAIL — cannot resolve `./Masthead`.

- [ ] **Step 8: Create `web/src/components/Masthead.tsx`** (mirrors report.html lines 162–171)

```tsx
import type { Manifest } from '../types';

interface Props { manifest: Manifest; activeKey: string; onSwitch: (key: string) => void; }

export function Masthead({ manifest, activeKey, onSwitch }: Props) {
  const active = manifest.variants.find((v) => v.key === activeKey) ?? manifest.variants[0];
  if (!active) return null;
  return (
    <header className="masthead" id="masthead">
      <div className="masthead-inner">
        <div>
          <div className="eyebrow">{active.eyebrow}</div>
          <h1>{active.title}</h1>
          <p className="lede" dangerouslySetInnerHTML={{ __html: active.lede }} />
        </div>
        <nav className="switcher" hidden={manifest.variants.length <= 1}>
          {manifest.variants.map((v) => (
            <button
              key={v.key}
              type="button"
              className={v.key === activeKey ? 'switch-tab on' : 'switch-tab'}
              onClick={() => onSwitch(v.key)}
            >
              {v.title}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}
```
Note: `lede` carries HTML entities (e.g. `&mdash;`) from `report_variants.py`, so it is set via `dangerouslySetInnerHTML` — the source is our own trusted manifest.

- [ ] **Step 9: Create `web/src/components/GlobalTaskStrip.tsx`** (mirrors report.html lines 173–175)

```tsx
import { FilterChunk } from './FilterChunk';

interface Props { tasks: string[]; selected: string[]; onToggle: (t: string) => void; onClear: () => void; }
export function GlobalTaskStrip({ tasks, selected, onToggle, onClear }: Props) {
  return (
    <div className="fstrip fstrip-global">
      <FilterChunk tag="Task" items={tasks} active={selected} onToggle={onToggle} onClear={onClear} />
    </div>
  );
}
```

- [ ] **Step 10: Replace `web/src/App.tsx`** (sections added in Tasks 7–8)

```tsx
import { useCallback, useEffect, useMemo, useState } from 'react';
import { DataProvider, useData } from './data/DataContext';
import { TokenGate } from './components/TokenGate';
import { Masthead } from './components/Masthead';
import { GlobalTaskStrip } from './components/GlobalTaskStrip';
import { parseHash, toHash } from './state/urlState';
import { clearTask, initState, setReport, toggleTask } from './state/appState';
import type { AppState, Manifest } from './types';

function firstVariantKey(manifest: Manifest, fromUrl: string | null): string {
  if (fromUrl && manifest.variants.some((v) => v.key === fromUrl)) return fromUrl;
  return manifest.variants[0]?.key ?? '';
}

function Dashboard({ manifest }: { manifest: Manifest }) {
  const [state, setState] = useState<AppState>(() => {
    const url = parseHash(window.location.hash);
    return initState(firstVariantKey(manifest, url.report), url.task);
  });

  // Sync report + task to the URL hash.
  useEffect(() => {
    const next = toHash({ report: state.report, task: state.task });
    if (next !== window.location.hash) window.history.replaceState(null, '', next || window.location.pathname);
  }, [state.report, state.task]);

  useEffect(() => {
    const onHash = () => {
      const url = parseHash(window.location.hash);
      setState((s) => (url.report && url.report !== s.report ? initState(url.report, url.task) : { ...s, task: url.task }));
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const variant = useMemo(
    () => manifest.variants.find((v) => v.key === state.report) ?? manifest.variants[0],
    [manifest, state.report],
  );
  const onSwitch = useCallback((key: string) => setState((s) => setReport(s, key)), []);

  if (!variant) return null;
  return (
    <>
      <Masthead manifest={manifest} activeKey={variant.key} onSwitch={onSwitch} />
      <main>
        <GlobalTaskStrip
          tasks={variant.tasks}
          selected={state.task}
          onToggle={(t) => setState((s) => toggleTask(s, t))}
          onClear={() => setState((s) => clearTask(s))}
        />
        {/* §0 brief band + KPI band → Task 7; §1/§2/§3 → Task 8. */}
        <p className="note">Active report: {variant.title} · tasks {JSON.stringify(state.task)}</p>
      </main>
    </>
  );
}

function Gate() {
  const { status, data, error } = useData();
  if (status === 'loading') return <main><p className="note">Loading…</p></main>;
  if (status === 'need-token') return <TokenGate />;
  if (status === 'error') return <main><p className="note">Failed to load: {error}</p></main>;
  if (status === 'ready' && data) return <Dashboard manifest={data.manifest} />;
  return null;
}

export default function App() {
  return (
    <DataProvider>
      <Gate />
    </DataProvider>
  );
}
```

- [ ] **Step 11: Run focused tests + full suite + build**

Run: `cd web && npx vitest run src/components/FilterChunk.test.tsx src/components/Masthead.test.tsx && npm test && npm run build`
Expected: focused PASS; full suite PASS; build succeeds.

- [ ] **Step 12: Commit**

```bash
git add web/src/theme.ts web/src/components/Chip.tsx web/src/components/FilterChunk.tsx web/src/components/Masthead.tsx web/src/components/GlobalTaskStrip.tsx web/src/components/Masthead.test.tsx web/src/components/FilterChunk.test.tsx web/src/App.tsx
git commit -m "feat(web): masthead, chips, sticky global task strip, URL sync"
```

---

### Task 7: §0 brief band + KPI band

**Files:** Create `web/src/data/kpis.ts`, `web/src/components/BriefBand.tsx`, `web/src/components/KpiBand.tsx`, `web/src/data/kpis.test.ts`, `web/src/components/KpiBand.test.tsx`; modify `web/src/App.tsx`.

**Interfaces:**
- `kpis.ts`: `computeKpis(runs: Run[]): { runs: number; meanRequests: number | null; meanCost: number | null; meanQuality: number | null; meanCacheHit: number | null }` — mean over non-null values; `null` when no data.
- `BriefBand({ variant, manifest })` → `.band.band-brief` with `.brief-grid` of `.brief` cards (per `variant.tasks`, using `manifest.task_meta`) and a `.strat-legend` with `.strat-grid` of strategies (per `variant.conditions`, using `manifest.strategy_desc`; `single_agent` shows a `.strat-base` "baseline" tag).
- `KpiBand({ runs })` → `.band.band-agg` > `.scope-tag` + `.kpis` of five `.kpi` cards: Runs / Mean requests / Mean total cost / Mean quality / Mean cache hit.

**Note (deferred fidelity):** the report's `.brief` cards include a dark `.brief-prompt` terminal box showing each task's prompt text + a live/pending status badge. That text comes from `report_variants.build_page` (reads `tasks/<task>/` prompt files) and is **not** in the current `/api/manifest`. This task renders the brief cards from `task_meta` (title + measures) and the strategy legend; wiring the prompt text + data-status badge requires extending the backend manifest with a per-variant `page` payload (and shipping `tasks/` prompts to the Space) — tracked for a later increment, not built here.

- [ ] **Step 1: Write the failing test for kpis** — `web/src/data/kpis.test.ts`

```ts
import { describe, expect, it } from 'vitest';
import type { Run } from '../types';
import { computeKpis } from './kpis';

const runs = [
  { num_requests: 5, total_cost_usd: 0.1, quality_score: 2, cache_hit_ratio: 0.9 },
  { num_requests: 7, total_cost_usd: 0.3, quality_score: null, cache_hit_ratio: 0.7 },
] as unknown as Run[];

describe('computeKpis', () => {
  it('counts runs and means non-null values', () => {
    const k = computeKpis(runs);
    expect(k.runs).toBe(2);
    expect(k.meanRequests).toBeCloseTo(6);
    expect(k.meanCost).toBeCloseTo(0.2);
    expect(k.meanQuality).toBeCloseTo(2); // only one non-null
    expect(k.meanCacheHit).toBeCloseTo(0.8);
  });
  it('returns nulls for empty input', () => {
    expect(computeKpis([])).toEqual({ runs: 0, meanRequests: null, meanCost: null, meanQuality: null, meanCacheHit: null });
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run src/data/kpis.test.ts`
Expected: FAIL — cannot resolve `./kpis`.

- [ ] **Step 3: Create `web/src/data/kpis.ts`**

```ts
import type { Run } from '../types';

export interface Kpis {
  runs: number;
  meanRequests: number | null; meanCost: number | null;
  meanQuality: number | null; meanCacheHit: number | null;
}
function mean(values: Array<number | null | undefined>): number | null {
  const nums = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
}
export function computeKpis(runs: Run[]): Kpis {
  return {
    runs: runs.length,
    meanRequests: mean(runs.map((r) => r.num_requests)),
    meanCost: mean(runs.map((r) => r.total_cost_usd)),
    meanQuality: mean(runs.map((r) => r.quality_score)),
    meanCacheHit: mean(runs.map((r) => r.cache_hit_ratio)),
  };
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run src/data/kpis.test.ts`
Expected: PASS (2).

- [ ] **Step 5: Create `web/src/components/KpiBand.tsx`** (mirrors report.html lines 177–180 + `.kpi` markup)

```tsx
import type { Run } from '../types';
import { computeKpis } from '../data/kpis';

function fmt(v: number | null, digits = 2, unit = ''): string {
  if (v == null) return '—';
  return `${v.toFixed(digits)}${unit}`;
}
export function KpiBand({ runs }: { runs: Run[] }) {
  const k = computeKpis(runs);
  const cards: { label: string; value: string }[] = [
    { label: 'Runs', value: String(k.runs) },
    { label: 'Mean requests', value: fmt(k.meanRequests, 1) },
    { label: 'Mean total cost', value: k.meanCost == null ? '—' : `$${k.meanCost.toFixed(3)}` },
    { label: 'Mean quality', value: fmt(k.meanQuality, 2) },
    { label: 'Mean cache hit', value: k.meanCacheHit == null ? '—' : `${(k.meanCacheHit * 100).toFixed(0)}%` },
  ];
  return (
    <section className="band band-agg">
      <div className="scope-tag">Aggregate · current selection</div>
      <div className="kpis">
        {cards.map((c) => (
          <div className="kpi" key={c.label}>
            <div className="label">{c.label}</div>
            <div className="value">{c.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 6: Write the failing test for KpiBand** — `web/src/components/KpiBand.test.tsx`

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Run } from '../types';
import { KpiBand } from './KpiBand';

describe('KpiBand', () => {
  it('renders five labelled cards with computed run count', () => {
    const runs = [{ num_requests: 4, total_cost_usd: 0.2, quality_score: 2, cache_hit_ratio: 0.5 }] as unknown as Run[];
    render(<KpiBand runs={runs} />);
    expect(screen.getByText('Runs')).toBeInTheDocument();
    expect(screen.getByText('Mean cache hit')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(document.querySelectorAll('.kpi')).toHaveLength(5);
  });
});
```

- [ ] **Step 7: Run KpiBand test**

Run: `cd web && npx vitest run src/components/KpiBand.test.tsx`
Expected: PASS (1).

- [ ] **Step 8: Create `web/src/components/BriefBand.tsx`** (mirrors report.html `.band-brief` / `.brief-grid` / `.strat-legend`)

```tsx
import type { Manifest, Variant } from '../types';
import { conditionColor } from '../theme';

export function BriefBand({ variant, manifest }: { variant: Variant; manifest: Manifest }) {
  return (
    <section className="band band-brief">
      <div className="brief-grid">
        {variant.tasks.map((task, i) => {
          const meta = manifest.task_meta[task];
          return (
            <article className="brief" key={task}>
              <div className="brief-head">
                <span className="brief-no">{i + 1}</span>
                <div className="brief-title">
                  <span className="brief-task">{task}</span>
                  <h3>{meta?.title ?? task}</h3>
                </div>
              </div>
              <p className="brief-measures">{meta?.measures ?? ''}</p>
            </article>
          );
        })}
      </div>
      <div className="strat-legend">
        <div className="strat-legend-head">Strategies</div>
        <div className="strat-grid">
          {variant.conditions.map((c) => (
            <div className="strat" key={c}>
              <span className="strat-dot" style={{ background: conditionColor(c) }} />
              <div className="strat-text">
                <span className="strat-line">
                  <b>{c}</b>
                  {c === 'single_agent' && <span className="strat-base">baseline</span>}
                </span>
                <span>{manifest.strategy_desc[c] ?? ''}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 9: Mount BriefBand + KpiBand in `web/src/App.tsx`**

In `App.tsx`, add two component imports and a filters import, and **replace** the Task 6 types import line `import type { AppState, Manifest } from './types';` with the `Run`-widened one (do NOT add a second `./types` import — that is a duplicate-identifier error):
```tsx
import { BriefBand } from './components/BriefBand';
import { KpiBand } from './components/KpiBand';
import { scopeRuns } from './data/filters';
import type { AppState, Manifest, Run } from './types';  // replaces the Task 6 line
```
Change `Dashboard` to receive `runs` and render the bands. Replace the `Dashboard` signature and the `<main>` body:
```tsx
function Dashboard({ manifest, runs }: { manifest: Manifest; runs: Run[] }) {
```
…and inside `<main>`, after `<GlobalTaskStrip .../>`, replace the placeholder `<p className="note">…</p>` with:
```tsx
        <BriefBand variant={variant} manifest={manifest} />
        <KpiBand runs={scopeRuns(runs, state.task, { condition: [], rep: [], agent: [] })} />
        {/* §1/§2/§3 → Task 8 */}
```
And update `Gate`'s ready branch to pass runs:
```tsx
if (status === 'ready' && data) return <Dashboard manifest={data.manifest} runs={data.runs} />;
```
(`Turn` is intentionally not imported yet — Task 8 widens the types import to add it. Importing an unused `Turn` now fails the build's `noUnusedLocals`.)

- [ ] **Step 10: Full suite + build**

Run: `cd web && npm test && npm run build`
Expected: all PASS; build succeeds.

- [ ] **Step 11: Commit**

```bash
git add web/src/data/kpis.ts web/src/data/kpis.test.ts web/src/components/BriefBand.tsx web/src/components/KpiBand.tsx web/src/components/KpiBand.test.tsx web/src/App.tsx
git commit -m "feat(web): §0 brief band + KPI band"
```

---

### Task 8: §1/§2/§3 band scaffolds + section filter strips + selectors

**Files:** Create `web/src/components/Section1.tsx`, `web/src/components/Section2.tsx`, `web/src/components/Section3.tsx`, `web/src/components/Section2.test.tsx`, `web/README.md`; modify `web/src/App.tsx`.

**Interfaces:**
- Each `SectionN({ variant, state, agentTypes, onToggle, onClear })` renders its `.band.band-*` with `.band-head`, its `.fstrip` filter chunks (§1: condition; §2/§3: condition + rep + agent), the section's selectors (§1: metric + overhead; §3: bar density + compose + group + cache-hit), and the **empty chart panels** with the report's element ids (`matrix-chart`, `condition-chart`, `overhead-chart`, `efficiency-chart`, `cache-panels`, `latency-chart`, `drilldown-runs`). Selectors are local UI state only (no chart yet). `onToggle(scope, dim, token)` / `onClear(scope, dim)` thread to `toggleSection`/`clearSection`.
- `reps` (the `r1..rN` present for the variant) and `agentTypes` are passed from `App`.

**Reference markup:** `reports/report.html` §1 lines 182–244, §2 lines 246–268, §3 lines 270–300. Reproduce the panel/selector structure; leave each `.chart` div empty (charts are Plans 2b/2c).

- [ ] **Step 1: Create `web/src/components/Section1.tsx`** (report.html lines 182–244)

```tsx
import type { AppState, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';

interface Props {
  variant: Variant; state: AppState;
  onToggle: (dim: 'condition', token: string) => void; onClear: (dim: 'condition') => void;
}
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

export function Section1({ variant, state, onToggle, onClear }: Props) {
  const hasBaseline = variant.conditions.includes('single_agent');
  return (
    <section className="band band-agg">
      <div className="band-head">
        <div className="band-label"><span className="band-no">§1</span>Averages across conditions</div>
        <div className="band-scope">Mean across rollouts · the Experiment matrix shows every rollout</div>
      </div>
      <div className="fstrip">
        <FilterChunk tag="Feature" items={variant.conditions} active={state.s1.condition}
          onToggle={(t) => onToggle('condition', t)} onClear={() => onClear('condition')} dotFor={conditionColor} />
      </div>
      <div className="grid">
        <article className="panel">
          <div className="panel-head"><h2>Experiment matrix</h2></div>
          <div id="matrix-chart" className="chart" />
          <div className="status-key" id="matrix-key" />
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Condition comparison</h2>
            <div className="control-group">
              <label className="control inline">metric
                <select defaultValue="mean_completion_time_s">
                  {METRICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            </div>
          </div>
          <div id="condition-chart" className="chart" />
        </article>
        {hasBaseline && (
          <article className="panel" id="overhead-panel">
            <div className="panel-head"><h2>Overhead vs single agent</h2>
              <div className="control-group">
                <label className="control inline">resource
                  <select defaultValue="num_requests_factor">
                    {OVERHEADS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </label>
              </div>
            </div>
            <div id="overhead-chart" className="chart" />
          </article>
        )}
        <article className="panel">
          <div className="panel-head"><h2>Quality vs cost map</h2></div>
          <div id="efficiency-chart" className="chart" />
        </article>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Create `web/src/components/Section2.tsx`** (report.html lines 246–268)

```tsx
import type { AppState, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';

interface Props {
  variant: Variant; state: AppState; reps: string[]; agentTypes: string[];
  onToggle: (dim: 'condition' | 'rep' | 'agent', token: string) => void;
  onClear: (dim: 'condition' | 'rep' | 'agent') => void;
}
export function Section2({ variant, state, reps, agentTypes, onToggle, onClear }: Props) {
  return (
    <section className="band band-dist">
      <div className="band-head">
        <div className="band-label"><span className="band-no">§2</span>Across all runs</div>
        <div className="band-scope">Each line or dot is a single run · scoped by this section</div>
      </div>
      <div className="fstrip">
        <FilterChunk tag="Feature" items={variant.conditions} active={state.s2.condition}
          onToggle={(t) => onToggle('condition', t)} onClear={() => onClear('condition')} dotFor={conditionColor} />
        <FilterChunk tag="Rollout" items={reps} active={state.s2.rep}
          onToggle={(t) => onToggle('rep', t)} onClear={() => onClear('rep')} />
        <FilterChunk tag="Agent" items={agentTypes} active={state.s2.agent}
          onToggle={(t) => onToggle('agent', t)} onClear={() => onClear('agent')} />
      </div>
      <div className="stack">
        <article className="panel">
          <div className="panel-head"><h2>Prefix Cache Hit Rate (accumulated)</h2></div>
          <div id="cache-panels" />
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Prefix cache hit rate vs context length</h2></div>
          <div id="latency-chart" className="chart" />
        </article>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Create `web/src/components/Section3.tsx`** (report.html lines 270–300)

```tsx
import { useState } from 'react';
import type { AppState, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';

interface Props {
  variant: Variant; state: AppState; reps: string[]; agentTypes: string[];
  onToggle: (dim: 'condition' | 'rep' | 'agent', token: string) => void;
  onClear: (dim: 'condition' | 'rep' | 'agent') => void;
}
export function Section3({ variant, state, reps, agentTypes, onToggle, onClear }: Props) {
  const [compose, setCompose] = useState('context');
  const [group, setGroup] = useState('agent');
  const [hitrate, setHitrate] = useState(true);
  const [density, setDensity] = useState(100);
  return (
    <section className="band band-run">
      <div className="band-head">
        <div className="band-label"><span className="band-no">§3</span>Single run drilldown</div>
      </div>
      <div className="fstrip">
        <FilterChunk tag="Feature" items={variant.conditions} active={state.s3.condition}
          onToggle={(t) => onToggle('condition', t)} onClear={() => onClear('condition')} dotFor={conditionColor} />
        <FilterChunk tag="Rollout" items={reps} active={state.s3.rep}
          onToggle={(t) => onToggle('rep', t)} onClear={() => onClear('rep')} />
        <FilterChunk tag="Agent" items={agentTypes} active={state.s3.agent}
          onToggle={(t) => onToggle('agent', t)} onClear={() => onClear('agent')} />
        <div className="control-group">
          <label className="control inline">bar density
            <input type="range" min={0} max={100} value={density} onChange={(e) => setDensity(Number(e.target.value))} />
          </label>
          <label className="control inline">compose by
            <select value={compose} onChange={(e) => setCompose(e.target.value)}>
              <option value="context">/context</option>
              <option value="source">source (detailed)</option>
              <option value="token">token type</option>
            </select>
          </label>
          <label className="control inline">group
            <select value={group} onChange={(e) => setGroup(e.target.value)}>
              <option value="agent">agent type</option>
              <option value="none">none</option>
            </select>
          </label>
          <label className="control inline check">
            <input type="checkbox" checked={hitrate} onChange={(e) => setHitrate(e.target.checked)} />cache hit rate
          </label>
        </div>
      </div>
      <div className="band-scope row">One block per run in this section's Feature × Rollout.</div>
      <div id="drilldown-runs" className="drilldown-runs" />
    </section>
  );
}
```
(The selector/slider/checkbox state is local UI for now; Plan 2c reads it to drive the §3 charts.)

- [ ] **Step 4: Write the failing test for section scoping** — `web/src/components/Section2.test.tsx`

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { initState } from '../state/appState';
import { Section2 } from './Section2';

const variant = { key: 'multi_agent', eyebrow: '', title: '', lede: '', conditions: ['single_agent', 'subagents'], tasks: ['coding'] };

describe('Section2', () => {
  it('renders Feature/Rollout/Agent chunks and reports toggles with the dimension', async () => {
    const onToggle = vi.fn();
    render(<Section2 variant={variant} state={initState('multi_agent', [])} reps={['r1', 'r2']} agentTypes={['main-agent']} onToggle={onToggle} onClear={() => {}} />);
    expect(screen.getByText('Feature')).toBeInTheDocument();
    expect(screen.getByText('Rollout')).toBeInTheDocument();
    expect(screen.getByText('Agent')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'subagents' }));
    expect(onToggle).toHaveBeenCalledWith('condition', 'subagents');
    await userEvent.click(screen.getByRole('button', { name: 'r2' }));
    expect(onToggle).toHaveBeenCalledWith('rep', 'r2');
  });
});
```

- [ ] **Step 5: Run to verify it fails, then (after Step 6) passes**

Run: `cd web && npx vitest run src/components/Section2.test.tsx`
Expected: FAIL — cannot resolve `./Section2` (until Step 2 created it; if created, this passes — run after all three sections exist).

- [ ] **Step 6: Mount the sections in `web/src/App.tsx`**

Adjust the imports (avoid duplicate-identifier errors — **replace** the overlapping lines, don't add new ones):
- **Add** the three section imports: `import { Section1 } from './components/Section1';` (and `Section2`, `Section3`).
- **Replace** the Task 7 filters import with: `import { presentAgentTypes, scopeRuns, scopeTurns } from './data/filters';`
- **Extend** the existing `./state/appState` import to also include `clearSection` and `toggleSection`.
- **Replace** the types import with: `import type { AppState, Manifest, Run, Turn } from './types';`

Change `Dashboard` to also take `turns`, derive `reps` + per-section `agentTypes`, and render the sections. Update the signature:
```tsx
function Dashboard({ manifest, runs, turns }: { manifest: Manifest; runs: Run[]; turns: Turn[] }) {
```
Add, after `variant` is computed:
```tsx
  const variantRuns = useMemo(
    () => runs.filter((r) => variant && variant.tasks.includes(r.task) && variant.conditions.includes(r.condition)),
    [runs, variant],
  );
  const reps = useMemo(() => Array.from(new Set(variantRuns.map((r) => `r${r.rep}`))).sort(), [variantRuns]);
  // Agent chip lists ignore the section's own agent selection, so picking one agent
  // doesn't hide the others (matches the report's stable agent chips).
  const agents2 = useMemo(() => presentAgentTypes(scopeTurns(turns, state.task, { ...state.s2, agent: [] })), [turns, state.task, state.s2]);
  const agents3 = useMemo(() => presentAgentTypes(scopeTurns(turns, state.task, { ...state.s3, agent: [] })), [turns, state.task, state.s3]);
  const sectionToggle = useCallback(
    (scope: 's1' | 's2' | 's3') => (dim: 'condition' | 'rep' | 'agent', token: string) =>
      setState((s) => toggleSection(s, scope, dim, token)),
    [],
  );
  const sectionClear = useCallback(
    (scope: 's1' | 's2' | 's3') => (dim: 'condition' | 'rep' | 'agent') =>
      setState((s) => clearSection(s, scope, dim)),
    [],
  );
```
Render after `<KpiBand .../>`:
```tsx
        <Section1 variant={variant} state={state} onToggle={sectionToggle('s1')} onClear={sectionClear('s1')} />
        <Section2 variant={variant} state={state} reps={reps} agentTypes={agents2} onToggle={sectionToggle('s2')} onClear={sectionClear('s2')} />
        <Section3 variant={variant} state={state} reps={reps} agentTypes={agents3} onToggle={sectionToggle('s3')} onClear={sectionClear('s3')} />
```
And pass `turns` from `Gate`:
```tsx
if (status === 'ready' && data) return <Dashboard manifest={data.manifest} runs={data.runs} turns={data.turns} />;
```
Remove the Task-7 placeholder note line. Ensure every import is used (the build's `noUnusedLocals` will catch leftovers).

- [ ] **Step 7: Create `web/README.md`**

```markdown
# CC Orchestration Report — frontend (SPA)

Vite + React + TypeScript SPA that reproduces the layout of `reports/report.html`,
fetching raw rows from the backend API (`serve/`). Plan 2a = shell; charts in 2b/2c.

## Develop against a local backend

```bash
make serve            # repo root: uvicorn :8799 (run `make analyze` first)
cd web
echo 'VITE_API_BASE=http://localhost:8799' > .env.local   # not committed
npm install && npm run dev                                 # http://localhost:5173
```
First load prompts for the access token (the backend's `API_TOKEN`; leave it unset for open local dev). Stored in `localStorage` (`cc_report_token`).

## Build / deploy (Vercel)

- `npm run build` → `web/dist/`.
- Vercel: set **Root Directory = `web`** and env **`VITE_API_BASE`** = the HF Space URL; add the Vercel origins to the backend's `ALLOWED_ORIGINS`.

The stylesheet (`src/styles.css`) is ported verbatim from `reports/report.html`; components mirror its class names so the SPA matches the report's layout.

## Test

`npm test` (Vitest): pure logic unit-tested; components via React Testing Library.
```

- [ ] **Step 8: Run section test + full suite + build**

Run: `cd web && npx vitest run src/components/Section2.test.tsx && npm test && npm run build`
Expected: Section2 PASS; full suite PASS (smoke, client, urlState, appState, filters, DataContext, FilterChunk, Masthead, kpis, KpiBand, Section2); build succeeds.

- [ ] **Step 9: Commit**

```bash
git add web/src/components/Section1.tsx web/src/components/Section2.tsx web/src/components/Section3.tsx web/src/components/Section2.test.tsx web/src/App.tsx web/README.md
git commit -m "feat(web): §1/§2/§3 band scaffolds with scoped filter strips and selectors"
```

---

## Manual setup (one-time, outside this plan)

1. Vercel project: **Root Directory = `web`**, env `VITE_API_BASE` = the Space URL.
2. Add Vercel production + preview origins to the backend Space's `ALLOWED_ORIGINS`.

## Out of scope (this plan → Plans 2b / 2c)

- **Plan 2b** — the charts inside the §1/§2 panels (experiment matrix heatmap, condition-comparison bar w/ live metric selector, overhead bar, quality-vs-cost scatter, per-task cache-accumulation lines, hit-rate-vs-context scatter) + their data-shaping helpers (condition metrics, overheads, cache accumulation). echarts ^6.
- **Plan 2c** — the §3 per-run drilldown (per-run cost timeline) and the context-source breakdown: the 3 compose modes (`/context`/`source`/`token`) + the component→bucket maps, 2 group modes, bar-density rescale, cache-hit inverted overlay, and the clickable context-text panel (`/api/component-texts`).
- The §0 prompt **terminal box** content + data-status badge (needs a backend manifest `page` field + `tasks/` prompts in the Space).
- Pixel polish beyond the ported stylesheet (e.g. the `rise` entrance animation already comes with the CSS).
