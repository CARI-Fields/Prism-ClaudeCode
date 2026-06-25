# Report Frontend SPA — Plan 2a (App Shell) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Vite + React + TypeScript SPA shell that authenticates against the backend API, loads all report data, and renders the masthead, report switcher, sidebar filters, and §0 band with deep-linkable URL state — no charts yet.

**Architecture:** A greenfield `web/` app (Vite 5, React 18, TS, Vitest). Pure-logic modules (API client, URL-hash state, filter derivation) are unit-tested with TDD; React components are tested with React Testing Library. A `DataProvider` loads `manifest/runs/turns/components/token-rates` once on mount and exposes a `loading | ready | need-token | error` state machine; a `TokenGate` captures the shared token on 401. App-level `Selection` state (report + task/condition/rep/agent) is the single source of truth, mirrored to the URL hash. Charts are deliberately out of scope (Plans 2b/2c).

**Tech Stack:** Vite ^5.4, React ^18.3, TypeScript ^5.5, Vitest ^2.1, @testing-library/react ^16, jsdom ^25, echarts ^5.5 (installed now, used in 2b). Package manager: npm. Node 18.

**Spec:** `docs/superpowers/specs/2026-06-25-report-frontend-backend-split-design.md`
**Backend API contract (Plan 1):** `serve/app.py` — `GET /healthz`; token-gated `GET /api/{manifest,runs,turns,components,component-texts,token-rates}`.
**Source of behavioral truth (what to mirror):** `analysis/echarts_report.py` (the current single-file report) + `analysis/report_variants.py` (the two variants).

## Global Constraints

- **App lives in `web/`** at the repo root; Vercel's project root will be set to `web/`. Node 18 — do NOT use Vite 6/7 or any dep that requires Node 20+.
- **TypeScript strict mode on.** No `any` in committed code except an explicit, commented escape hatch.
- **API base** comes from `import.meta.env.VITE_API_BASE` (empty string default → same-origin/relative). The **token** is entered at runtime and stored in `localStorage` under key `cc_report_token` — never hard-coded, never in a committed `.env`.
- **P2 split:** the frontend owns all derivation. This plan ports only the *shell* derivations: URL state, filtering, present-agent-types. Chart data-shaping (condition metrics, cache accumulation, component→bucket mapping) is Plans 2b/2c.
- **Two reports** come from `manifest.variants` (`multi_agent`, `long_horizon`); switching resets filters to that variant's defaults (first task, all of its conditions). Do not hard-code variant copy — read it from the manifest.
- **URL hash format** (mirror the existing report, raw commas): `#report=<key>&task=a,b&condition=a,b&rep=r1,r2&agent=a,b`. Empty list ⇒ key omitted ⇒ "all".
- **rep tokens are `r<N>`** in the URL/filters; `runs.rep`/`turns.rep` are integers — convert with `` `r${rep}` ``.
- Tests run with `npm test` (`vitest run`); every task ends green with pristine output.

## File Structure

| File | Responsibility |
|---|---|
| `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/tsconfig.node.json`, `web/index.html` | Scaffold + Vitest config |
| `web/src/main.tsx`, `web/src/index.css` | Entry point + base styles |
| `web/src/test/setup.ts` | Vitest + jsdom + jest-dom setup |
| `web/src/types.ts` | Shared TS interfaces (Run/Turn/Component/ComponentText/Manifest/Variant/Selection) |
| `web/src/api/token.ts` | localStorage token get/set/clear |
| `web/src/api/client.ts` | `apiGet` + per-endpoint fetchers + `ApiError` |
| `web/src/state/urlState.ts` | `parseHash` / `toHash` pure functions |
| `web/src/data/filters.ts` | `filteredRuns` / `filteredTurns` / `presentAgentTypes` |
| `web/src/data/DataContext.tsx` | `DataProvider` + `useData` (load state machine) |
| `web/src/components/TokenGate.tsx` | Token input on 401 |
| `web/src/components/Masthead.tsx` | Eyebrow/title/lede + report switcher tabs |
| `web/src/components/Section0.tsx` | Task briefs + strategy legend |
| `web/src/components/Sidebar.tsx` | task/condition/rep/agent chips + reset |
| `web/src/theme.ts` | Condition/status color maps, fonts |
| `web/src/App.tsx` | Composition + `Selection` state + URL sync |
| `web/README.md` | Run-against-local-backend + env vars + Vercel root |
| `web/.gitignore` (or root) | `node_modules`, `dist`, `.vercel` |

---

### Task 1: Scaffold the Vite + React + TS app

**Files:** Create `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/tsconfig.node.json`, `web/index.html`, `web/src/main.tsx`, `web/src/index.css`, `web/src/App.tsx`, `web/src/test/setup.ts`, `web/.gitignore`, `web/src/smoke.test.ts`.

**Interfaces:**
- Produces: a buildable app; `npm test`, `npm run build` succeed. `App` is a default export React component.

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
    "echarts": "^5.5.1",
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
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: false,
  },
});
```

- [ ] **Step 3: Create `web/tsconfig.json` and `web/tsconfig.node.json`**

`web/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
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
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create `web/index.html`, `web/src/main.tsx`, `web/src/index.css`, `web/src/App.tsx`**

`web/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CC Orchestration Report</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`web/src/main.tsx`:
```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

`web/src/index.css`:
```css
:root {
  --sans: 'IBM Plex Sans', system-ui, sans-serif;
  --mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, monospace;
  --ink: #10151d; --muted: #5c6675; --line: #dde2e9; --paper: #eceef2; --panel: #fff;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: var(--sans); color: var(--ink); background: var(--paper); }
```

`web/src/App.tsx` (placeholder — replaced in Task 6):
```tsx
export default function App() {
  return <main>CC Orchestration Report</main>;
}
```

- [ ] **Step 5: Create `web/src/test/setup.ts` and a smoke test**

`web/src/test/setup.ts`:
```ts
import '@testing-library/jest-dom/vitest';
```

`web/src/smoke.test.ts`:
```ts
import { describe, expect, it } from 'vitest';

describe('toolchain', () => {
  it('runs vitest', () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 6: Create `web/.gitignore`**

```
node_modules
dist
.vercel
*.local
```

- [ ] **Step 7: Install and verify**

Run:
```bash
cd web && npm install && npm test && npm run build
```
Expected: `npm test` → `1 passed`; `npm run build` → succeeds (writes `web/dist/`). If `npm install` warns about peer deps, that's fine as long as test+build pass.

- [ ] **Step 8: Commit**

```bash
git add web/package.json web/package-lock.json web/vite.config.ts web/tsconfig.json web/tsconfig.node.json web/index.html web/src/main.tsx web/src/index.css web/src/App.tsx web/src/test/setup.ts web/src/smoke.test.ts web/.gitignore
git commit -m "feat(web): scaffold vite+react+ts+vitest app shell"
```

---

### Task 2: Types, token store, and API client

**Files:** Create `web/src/types.ts`, `web/src/api/token.ts`, `web/src/api/client.ts`, `web/src/api/client.test.ts`.

**Interfaces:**
- Produces:
  - `types.ts`: `Run`, `Turn`, `Component`, `ComponentText`, `Variant`, `Manifest`, `Selection`.
  - `token.ts`: `getToken(): string`, `setToken(t: string): void`, `clearToken(): void`.
  - `client.ts`: `class ApiError extends Error { status: number }`; `apiBase(): string`; `apiGet<T>(path: string): Promise<T>`; `getManifest`, `getRuns`, `getTurns`, `getComponents`, `getTokenRates`, `getComponentTexts(runId, requestIndex?)`.

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
export interface Selection {
  report: string | null;
  task: string[]; condition: string[]; rep: string[]; agent: string[];
}
```

- [ ] **Step 2: Create `web/src/api/token.ts`**

```ts
const KEY = 'cc_report_token';
export function getToken(): string { return localStorage.getItem(KEY) ?? ''; }
export function setToken(t: string): void { localStorage.setItem(KEY, t); }
export function clearToken(): void { localStorage.removeItem(KEY); }
```

- [ ] **Step 3: Write the failing test for the client**

`web/src/api/client.test.ts`:
```ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiGet, getManifest } from './client';
import { setToken } from './token';

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  });
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
    vi.stubGlobal('fetch', mockFetch(401, { detail: 'nope' }));
    await expect(getManifest()).rejects.toMatchObject({ name: 'ApiError', status: 401 });
  });

  it('throws ApiError on other non-ok status', async () => {
    vi.stubGlobal('fetch', mockFetch(500, {}));
    await expect(apiGet('/api/runs')).rejects.toBeInstanceOf(ApiError);
  });
});
```

- [ ] **Step 4: Run it to verify it fails**

Run: `cd web && npx vitest run src/api/client.test.ts`
Expected: FAIL — cannot resolve `./client`.

- [ ] **Step 5: Create `web/src/api/client.ts`**

```ts
import type { Component, ComponentText, Manifest, Run, Turn } from '../types';
import { getToken } from './token';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function apiBase(): string {
  return (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
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

- [ ] **Step 6: Run it to verify it passes**

Run: `cd web && npx vitest run src/api/client.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add web/src/types.ts web/src/api/token.ts web/src/api/client.ts web/src/api/client.test.ts
git commit -m "feat(web): types, token store, and API client"
```

---

### Task 3: URL-hash state

**Files:** Create `web/src/state/urlState.ts`, `web/src/state/urlState.test.ts`.

**Interfaces:**
- Consumes: `Selection` from `types.ts`.
- Produces: `parseHash(hash: string): Selection`; `toHash(sel: Selection): string`. Round-trip stable; raw commas preserved; empty lists omitted.

- [ ] **Step 1: Write the failing tests**

`web/src/state/urlState.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import type { Selection } from '../types';
import { parseHash, toHash } from './urlState';

const sel: Selection = {
  report: 'multi_agent', task: ['coding'],
  condition: ['single_agent', 'subagents'], rep: ['r1', 'r2'], agent: [],
};

describe('urlState', () => {
  it('serializes with raw commas, omits empty lists', () => {
    expect(toHash(sel)).toBe('#report=multi_agent&task=coding&condition=single_agent,subagents&rep=r1,r2');
  });

  it('round-trips', () => {
    expect(parseHash(toHash(sel))).toEqual(sel);
  });

  it('parses empty hash to all-empty selection', () => {
    expect(parseHash('')).toEqual({ report: null, task: [], condition: [], rep: [], agent: [] });
  });

  it('tolerates a leading # and missing keys', () => {
    expect(parseHash('#report=long_horizon')).toEqual({
      report: 'long_horizon', task: [], condition: [], rep: [], agent: [],
    });
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run src/state/urlState.test.ts`
Expected: FAIL — cannot resolve `./urlState`.

- [ ] **Step 3: Create `web/src/state/urlState.ts`**

```ts
import type { Selection } from '../types';

const LIST_KEYS = ['task', 'condition', 'rep', 'agent'] as const;

export function parseHash(hash: string): Selection {
  const h = hash.replace(/^#/, '');
  const get = (key: string): string | null => {
    for (const seg of h.split('&')) {
      if (!seg) continue;
      const eq = seg.indexOf('=');
      if (eq === -1) continue;
      if (seg.slice(0, eq) === key) return seg.slice(eq + 1);
    }
    return null;
  };
  const list = (key: string): string[] => {
    const v = get(key);
    return v ? v.split(',').filter(Boolean) : [];
  };
  return {
    report: get('report'),
    task: list('task'), condition: list('condition'),
    rep: list('rep'), agent: list('agent'),
  };
}

export function toHash(sel: Selection): string {
  const parts: string[] = [];
  if (sel.report) parts.push(`report=${sel.report}`);
  for (const key of LIST_KEYS) {
    const arr = sel[key];
    if (arr.length) parts.push(`${key}=${arr.join(',')}`);
  }
  return parts.length ? `#${parts.join('&')}` : '';
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run src/state/urlState.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/state/urlState.ts web/src/state/urlState.test.ts
git commit -m "feat(web): deep-linkable URL-hash state"
```

---

### Task 4: Filter derivation

**Files:** Create `web/src/data/filters.ts`, `web/src/data/filters.test.ts`.

**Interfaces:**
- Consumes: `Run`, `Turn`, `Selection`.
- Produces: `filteredRuns(runs, sel): Run[]`; `filteredTurns(turns, sel): Turn[]`; `presentAgentTypes(turns): string[]`. An empty list in a `Selection` dimension means "all" for that dimension. `rep` matches via `` `r${rep}` ``. `filteredTurns` additionally filters by `agent` (against `request_type`).

- [ ] **Step 1: Write the failing tests**

`web/src/data/filters.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import type { Run, Selection, Turn } from '../types';
import { filteredRuns, filteredTurns, presentAgentTypes } from './filters';

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

const sel = (over: Partial<Selection>): Selection => ({
  report: null, task: [], condition: [], rep: [], agent: [], ...over,
});

describe('filters', () => {
  it('empty selection returns everything', () => {
    expect(filteredRuns(runs, sel({}))).toHaveLength(3);
  });
  it('filters runs by task + condition + rep (r-prefixed)', () => {
    const out = filteredRuns(runs, sel({ task: ['coding'], rep: ['r1'] }));
    expect(out.map(r => r.run_id)).toEqual(['a']);
  });
  it('filters turns by agent against request_type, dropping nulls when agent set', () => {
    const out = filteredTurns(turns, sel({ agent: ['task-subagent'] }));
    expect(out.map(t => t.run_id)).toEqual(['b']);
    expect(out).toHaveLength(1);
  });
  it('presentAgentTypes returns sorted distinct non-null types', () => {
    expect(presentAgentTypes(turns)).toEqual(['main-agent', 'task-subagent']);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run src/data/filters.test.ts`
Expected: FAIL — cannot resolve `./filters`.

- [ ] **Step 3: Create `web/src/data/filters.ts`**

```ts
import type { Run, Selection, Turn } from '../types';

const inSel = (values: string[], v: string): boolean => values.length === 0 || values.includes(v);

export function filteredRuns(runs: Run[], sel: Selection): Run[] {
  return runs.filter(
    (r) =>
      inSel(sel.task, r.task) &&
      inSel(sel.condition, r.condition) &&
      inSel(sel.rep, `r${r.rep}`),
  );
}

export function filteredTurns(turns: Turn[], sel: Selection): Turn[] {
  return turns.filter(
    (t) =>
      inSel(sel.task, t.task) &&
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

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run src/data/filters.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/data/filters.ts web/src/data/filters.test.ts
git commit -m "feat(web): filter derivation (runs/turns/agent-types)"
```

---

### Task 5: Data provider + token gate

**Files:** Create `web/src/data/DataContext.tsx`, `web/src/components/TokenGate.tsx`, `web/src/data/DataContext.test.tsx`.

**Interfaces:**
- Consumes: `getManifest/getRuns/getTurns/getComponents/getTokenRates`, `ApiError`, `setToken`.
- Produces:
  - `DataStatus = 'loading' | 'ready' | 'need-token' | 'error'`.
  - `DataBundle { manifest, runs, turns, components, tokenRates }`.
  - `DataProvider({ children })`; `useData(): { status, data: DataBundle | null, error: string | null, reload(): void }`.
  - `TokenGate()` — renders a password input; on submit stores the token and calls `reload()`.

- [ ] **Step 1: Write the failing test**

`web/src/data/DataContext.test.tsx`:
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

const ok = {
  manifest: { variants: [], strategy_desc: {}, task_meta: {}, available: [] },
  runs: [{ run_id: 'r1' }], turns: [], components: [], tokenRates: {},
};

function stubAll(impl: () => Promise<unknown>) {
  for (const fn of ['getManifest', 'getRuns', 'getTurns', 'getComponents', 'getTokenRates'] as const) {
    vi.spyOn(client, fn).mockImplementation(impl as never);
  }
}

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

describe('DataProvider', () => {
  it('loads and exposes ready data', async () => {
    vi.spyOn(client, 'getManifest').mockResolvedValue(ok.manifest as never);
    vi.spyOn(client, 'getRuns').mockResolvedValue(ok.runs as never);
    vi.spyOn(client, 'getTurns').mockResolvedValue([] as never);
    vi.spyOn(client, 'getComponents').mockResolvedValue([] as never);
    vi.spyOn(client, 'getTokenRates').mockResolvedValue({} as never);
    render(<DataProvider><Probe /></DataProvider>);
    await waitFor(() => expect(screen.getByText(/status:ready/)).toBeInTheDocument());
    expect(screen.getByText(/runs:1/)).toBeInTheDocument();
  });

  it('enters need-token on 401 and recovers after the gate submits a token', async () => {
    stubAll(() => Promise.reject(new client.ApiError(401, 'unauthorized')));
    render(<DataProvider><TokenGate /><Probe /></DataProvider>);
    await waitFor(() => expect(screen.getByText(/status:need-token/)).toBeInTheDocument());

    // Now the API succeeds; submitting the token should reload to ready.
    stubAll(() => Promise.resolve([] as never));
    vi.spyOn(client, 'getManifest').mockResolvedValue(ok.manifest as never);
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
import {
  ApiError, getComponents, getManifest, getRuns, getTokenRates, getTurns,
} from '../api/client';
import type { Component, Manifest, Run, Turn } from '../types';

export type DataStatus = 'loading' | 'ready' | 'need-token' | 'error';

export interface DataBundle {
  manifest: Manifest; runs: Run[]; turns: Turn[];
  components: Component[]; tokenRates: Record<string, number>;
}

interface DataState {
  status: DataStatus; data: DataBundle | null; error: string | null; reload: () => void;
}

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
    setStatus('loading');
    setError(null);
    try {
      const [manifest, runs, turns, components, tokenRates] = await Promise.all([
        getManifest(), getRuns(), getTurns(), getComponents(), getTokenRates(),
      ]);
      setData({ manifest, runs, turns, components, tokenRates });
      setStatus('ready');
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setStatus('need-token');
      } else {
        setError(e instanceof Error ? e.message : String(e));
        setStatus('error');
      }
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
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setToken(value.trim());
    reload();
  };
  return (
    <form onSubmit={submit} className="token-gate" style={{ padding: 24, maxWidth: 360 }}>
      <p>This dashboard is private. Enter the access token to continue.</p>
      <label>
        Access token
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          style={{ display: 'block', width: '100%', margin: '8px 0', fontFamily: 'var(--mono)' }}
        />
      </label>
      <button type="submit">Enter</button>
    </form>
  );
}
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd web && npx vitest run src/data/DataContext.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add web/src/data/DataContext.tsx web/src/components/TokenGate.tsx web/src/data/DataContext.test.tsx
git commit -m "feat(web): data provider state machine + token gate"
```

---

### Task 6: App shell — masthead, switcher, URL sync

**Files:** Create `web/src/theme.ts`, `web/src/components/Masthead.tsx`, `web/src/components/Masthead.test.tsx`; replace `web/src/App.tsx`.

**Interfaces:**
- Consumes: `useData`, `DataProvider`, `TokenGate`, `parseHash`/`toHash`, `Manifest`/`Variant`/`Selection`.
- Produces:
  - `theme.ts`: `CONDITION_COLORS: Record<string, string>`, `STATUS_COLORS`, fallback `PALETTE: string[]`.
  - `Masthead({ manifest, activeKey, onSwitch })` — renders the active variant's eyebrow/title/lede and a switcher tab per variant (hidden when only one); clicking a tab calls `onSwitch(key)`.
  - `App` — wraps everything in `DataProvider`; renders loading/error/`TokenGate`/ready; owns `Selection` state synced to the URL hash; computes the active variant; switching a report resets task→first variant task, condition→all variant conditions, rep/agent→empty.

- [ ] **Step 1: Create `web/src/theme.ts`**

```ts
// Mirrors analysis/echarts_report.py condition/status palettes.
export const CONDITION_COLORS: Record<string, string> = {
  single_agent: '#3b5bdb',
  goal: '#2f9e44',
  subagents: '#0c8599',
  ralph_loop: '#e8590c',
  dynamic_workflow: '#7048e8',
  loop_dynamic: '#c2255c',
};
export const STATUS_COLORS = {
  missing: '#eef1f5', failed: '#e03131', success: '#2f9e44', skipped: '#adb5bd',
};
export const PALETTE = ['#3b5bdb', '#0c8599', '#e8590c', '#7048e8', '#c2255c', '#1098ad', '#f59f00'];
export function conditionColor(condition: string, fallbackIndex = 0): string {
  return CONDITION_COLORS[condition] ?? PALETTE[fallbackIndex % PALETTE.length];
}
```

- [ ] **Step 2: Write the failing test for Masthead**

`web/src/components/Masthead.test.tsx`:
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
  it('renders the active variant title + lede and a tab per variant', () => {
    render(<Masthead manifest={manifest} activeKey="multi_agent" onSwitch={() => {}} />);
    expect(screen.getByRole('heading', { name: 'Multi-agent orchestration' })).toBeInTheDocument();
    expect(screen.getByText('lede A')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Long-horizon persistence' })).toBeInTheDocument();
  });

  it('calls onSwitch with the clicked variant key', async () => {
    const onSwitch = vi.fn();
    render(<Masthead manifest={manifest} activeKey="multi_agent" onSwitch={onSwitch} />);
    await userEvent.click(screen.getByRole('button', { name: 'Long-horizon persistence' }));
    expect(onSwitch).toHaveBeenCalledWith('long_horizon');
  });
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd web && npx vitest run src/components/Masthead.test.tsx`
Expected: FAIL — cannot resolve `./Masthead`.

- [ ] **Step 4: Create `web/src/components/Masthead.tsx`**

```tsx
import type { Manifest } from '../types';

interface Props {
  manifest: Manifest;
  activeKey: string;
  onSwitch: (key: string) => void;
}

export function Masthead({ manifest, activeKey, onSwitch }: Props) {
  const active = manifest.variants.find((v) => v.key === activeKey) ?? manifest.variants[0];
  if (!active) return null;
  return (
    <header style={{ padding: '20px 24px', borderBottom: '1px solid var(--line)', background: 'var(--panel)' }}>
      {manifest.variants.length > 1 && (
        <nav style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          {manifest.variants.map((v) => (
            <button
              key={v.key}
              onClick={() => onSwitch(v.key)}
              aria-pressed={v.key === activeKey}
              style={{
                fontFamily: 'var(--mono)', fontSize: 12, padding: '4px 10px', borderRadius: 6,
                border: '1px solid var(--line)',
                background: v.key === activeKey ? 'var(--ink)' : 'transparent',
                color: v.key === activeKey ? '#fff' : 'var(--muted)', cursor: 'pointer',
              }}
            >
              {v.title}
            </button>
          ))}
        </nav>
      )}
      <div style={{ fontFamily: 'var(--mono)', fontSize: 11.5, textTransform: 'uppercase', color: 'var(--muted)' }}>
        {active.eyebrow}
      </div>
      <h1 style={{ fontSize: 27, letterSpacing: '-0.01em', margin: '4px 0' }}>{active.title}</h1>
      <p style={{ color: 'var(--muted)', maxWidth: 780, margin: 0 }} dangerouslySetInnerHTML={{ __html: active.lede }} />
    </header>
  );
}
```
Note: `lede` may contain HTML entities (e.g. `&mdash;`) from `report_variants.py`, so it is rendered via `dangerouslySetInnerHTML` — the source is our own trusted manifest, not user input.

- [ ] **Step 5: Replace `web/src/App.tsx`**

```tsx
import { useCallback, useEffect, useMemo, useState } from 'react';
import { DataProvider, useData } from './data/DataContext';
import { TokenGate } from './components/TokenGate';
import { Masthead } from './components/Masthead';
import { parseHash, toHash } from './state/urlState';
import type { Manifest, Selection, Variant } from './types';

function defaultsForVariant(v: Variant): Pick<Selection, 'task' | 'condition' | 'rep' | 'agent'> {
  return { task: v.tasks.slice(0, 1), condition: [...v.conditions], rep: [], agent: [] };
}

function activeVariant(manifest: Manifest, key: string | null): Variant {
  return manifest.variants.find((v) => v.key === key) ?? manifest.variants[0];
}

function Dashboard({ manifest }: { manifest: Manifest }) {
  const [sel, setSel] = useState<Selection>(() => {
    const fromUrl = parseHash(window.location.hash);
    const variant = activeVariant(manifest, fromUrl.report);
    const base = fromUrl.report ? fromUrl : { ...fromUrl, report: variant?.key ?? null, ...defaultsForVariant(variant) };
    return base;
  });

  useEffect(() => {
    const next = toHash(sel);
    if (next !== window.location.hash) window.history.replaceState(null, '', next || window.location.pathname);
  }, [sel]);

  useEffect(() => {
    const onHash = () => setSel(parseHash(window.location.hash));
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const onSwitch = useCallback((key: string) => {
    const variant = activeVariant(manifest, key);
    setSel({ report: key, ...defaultsForVariant(variant) });
  }, [manifest]);

  const variant = useMemo(() => activeVariant(manifest, sel.report), [manifest, sel.report]);

  return (
    <>
      <Masthead manifest={manifest} activeKey={variant?.key ?? ''} onSwitch={onSwitch} />
      {/* Sidebar + §0 band wired in Task 7; charts in Plans 2b/2c. */}
      <main style={{ padding: 24, color: 'var(--muted)' }}>
        Showing <strong>{variant?.title}</strong> — filters: {JSON.stringify({ task: sel.task, condition: sel.condition, rep: sel.rep, agent: sel.agent })}
      </main>
    </>
  );
}

function Gate() {
  const { status, data, error } = useData();
  if (status === 'loading') return <main style={{ padding: 24 }}>Loading…</main>;
  if (status === 'need-token') return <TokenGate />;
  if (status === 'error') return <main style={{ padding: 24 }}>Failed to load: {error}</main>;
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

- [ ] **Step 6: Run the focused test + full suite + build**

Run: `cd web && npx vitest run src/components/Masthead.test.tsx && npm test && npm run build`
Expected: Masthead tests PASS; full suite all PASS; `tsc -b && vite build` succeeds.

- [ ] **Step 7: Commit**

```bash
git add web/src/theme.ts web/src/components/Masthead.tsx web/src/components/Masthead.test.tsx web/src/App.tsx
git commit -m "feat(web): app shell with masthead, report switcher, URL sync"
```

---

### Task 7: Sidebar filters + §0 band + docs

**Files:** Create `web/src/components/Sidebar.tsx`, `web/src/components/Section0.tsx`, `web/src/components/Sidebar.test.tsx`, `web/README.md`; modify `web/src/App.tsx` to mount them.

**Interfaces:**
- Consumes: `Selection`, `Variant`, `Manifest`, `presentAgentTypes`, `filteredTurns`, `conditionColor`.
- Produces:
  - `Sidebar({ variant, selection, agentTypes, onToggle, onReset })` — chip groups for task (variant.tasks), condition (variant.conditions), rep (`r1..r3` from runs present — passed in as `reps: string[]`), agent (`agentTypes`); clicking a chip calls `onToggle(dimension, token)`; reset calls `onReset()`. A dimension with an empty selection renders all chips inactive (="all").
  - `Section0({ variant, manifest })` — renders, per `variant.tasks`, the `task_meta[task]` title + measures, and a strategy legend from `variant.conditions` + `manifest.strategy_desc`.

- [ ] **Step 1: Write the failing test for Sidebar**

`web/src/components/Sidebar.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { Selection, Variant } from '../types';
import { Sidebar } from './Sidebar';

const variant: Variant = {
  key: 'multi_agent', eyebrow: '', title: '', lede: '',
  conditions: ['single_agent', 'subagents'], tasks: ['coding', 'research'],
};
const sel: Selection = { report: 'multi_agent', task: ['coding'], condition: [], rep: [], agent: [] };

describe('Sidebar', () => {
  it('marks the active task chip pressed and others not', () => {
    render(<Sidebar variant={variant} selection={sel} reps={['r1', 'r2']} agentTypes={['main-agent']} onToggle={() => {}} onReset={() => {}} />);
    expect(screen.getByRole('button', { name: 'coding' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'research' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('calls onToggle(dimension, token) when a chip is clicked', async () => {
    const onToggle = vi.fn();
    render(<Sidebar variant={variant} selection={sel} reps={['r1', 'r2']} agentTypes={['main-agent']} onToggle={onToggle} onReset={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: 'subagents' }));
    expect(onToggle).toHaveBeenCalledWith('condition', 'subagents');
  });

  it('calls onReset when reset clicked', async () => {
    const onReset = vi.fn();
    render(<Sidebar variant={variant} selection={sel} reps={['r1']} agentTypes={[]} onToggle={() => {}} onReset={onReset} />);
    await userEvent.click(screen.getByRole('button', { name: /reset/i }));
    expect(onReset).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run src/components/Sidebar.test.tsx`
Expected: FAIL — cannot resolve `./Sidebar`.

- [ ] **Step 3: Create `web/src/components/Sidebar.tsx`**

```tsx
import type { ReactNode } from 'react';
import type { Selection, Variant } from '../types';
import { conditionColor } from '../theme';

export type Dimension = 'task' | 'condition' | 'rep' | 'agent';

interface Props {
  variant: Variant;
  selection: Selection;
  reps: string[];
  agentTypes: string[];
  onToggle: (dimension: Dimension, token: string) => void;
  onReset: () => void;
}

function Chip({ label, active, dot, onClick }: { label: string; active: boolean; dot?: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 9px', margin: 3,
        borderRadius: 999, border: '1px solid var(--line)', cursor: 'pointer',
        fontFamily: 'var(--mono)', fontSize: 12,
        background: active ? 'var(--ink)' : 'transparent', color: active ? '#fff' : 'var(--muted)',
      }}
    >
      {dot && <span style={{ width: 8, height: 8, borderRadius: 999, background: dot }} />}
      {label}
    </button>
  );
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 11, textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 4 }}>{title}</div>
      <div>{children}</div>
    </div>
  );
}

export function Sidebar({ variant, selection, reps, agentTypes, onToggle, onReset }: Props) {
  const isActive = (dim: Dimension, token: string) => selection[dim].includes(token);
  return (
    <aside style={{ padding: 16, borderRight: '1px solid var(--line)', minWidth: 220, background: 'var(--panel)' }}>
      <Group title="Task">
        {variant.tasks.map((t) => (
          <Chip key={t} label={t} active={isActive('task', t)} onClick={() => onToggle('task', t)} />
        ))}
      </Group>
      <Group title="Condition">
        {variant.conditions.map((c) => (
          <Chip key={c} label={c} active={isActive('condition', c)} dot={conditionColor(c)} onClick={() => onToggle('condition', c)} />
        ))}
      </Group>
      <Group title="Rollout">
        {reps.map((r) => (
          <Chip key={r} label={r} active={isActive('rep', r)} onClick={() => onToggle('rep', r)} />
        ))}
      </Group>
      <Group title="Agent type">
        {agentTypes.map((a) => (
          <Chip key={a} label={a} active={isActive('agent', a)} onClick={() => onToggle('agent', a)} />
        ))}
      </Group>
      <button onClick={onReset} style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>Reset</button>
    </aside>
  );
}
```

- [ ] **Step 4: Create `web/src/components/Section0.tsx`**

```tsx
import type { Manifest, Variant } from '../types';
import { conditionColor } from '../theme';

export function Section0({ variant, manifest }: { variant: Variant; manifest: Manifest }) {
  return (
    <section style={{ padding: '16px 24px', borderBottom: '1px solid var(--line)' }}>
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Tasks</div>
          {variant.tasks.map((t) => {
            const meta = manifest.task_meta[t];
            return (
              <div key={t} style={{ marginBottom: 8, maxWidth: 420 }}>
                <div style={{ fontWeight: 600 }}>{meta?.title ?? t}</div>
                <div style={{ color: 'var(--muted)', fontSize: 14 }}>{meta?.measures ?? ''}</div>
              </div>
            );
          })}
        </div>
        <div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Strategies</div>
          {variant.conditions.map((c) => (
            <div key={c} style={{ display: 'flex', gap: 8, alignItems: 'baseline', marginBottom: 6, maxWidth: 420 }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: conditionColor(c), flex: '0 0 auto' }} />
              <div>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 13 }}>{c}</span>
                <span style={{ color: 'var(--muted)', fontSize: 14 }}> — {manifest.strategy_desc[c] ?? ''}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Wire Sidebar + Section0 into `web/src/App.tsx`**

Replace the `Dashboard` function body's `return (...)` block and add the toggle handler + derived data. The full updated `Dashboard` function:

```tsx
function Dashboard({ manifest, runs, turns }: { manifest: Manifest; runs: Run[]; turns: Turn[] }) {
  const [sel, setSel] = useState<Selection>(() => {
    const fromUrl = parseHash(window.location.hash);
    const variant = activeVariant(manifest, fromUrl.report);
    return fromUrl.report ? fromUrl : { ...fromUrl, report: variant?.key ?? null, ...defaultsForVariant(variant) };
  });

  useEffect(() => {
    const next = toHash(sel);
    if (next !== window.location.hash) window.history.replaceState(null, '', next || window.location.pathname);
  }, [sel]);
  useEffect(() => {
    const onHash = () => setSel(parseHash(window.location.hash));
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const variant = useMemo(() => activeVariant(manifest, sel.report), [manifest, sel.report]);

  const onSwitch = useCallback((key: string) => {
    setSel({ report: key, ...defaultsForVariant(activeVariant(manifest, key)) });
  }, [manifest]);

  const onToggle = useCallback((dim: Dimension, token: string) => {
    setSel((s) => {
      const cur = s[dim];
      const next = cur.includes(token) ? cur.filter((x) => x !== token) : [...cur, token];
      return { ...s, [dim]: next };
    });
  }, []);

  const onReset = useCallback(() => onSwitch(variant?.key ?? ''), [onSwitch, variant]);

  const variantRuns = useMemo(
    () => runs.filter((r) => variant?.tasks.includes(r.task) && variant?.conditions.includes(r.condition)),
    [runs, variant],
  );
  const reps = useMemo(
    () => Array.from(new Set(variantRuns.map((r) => `r${r.rep}`))).sort(),
    [variantRuns],
  );
  const agentTypes = useMemo(() => presentAgentTypes(filteredTurns(turns, sel)), [turns, sel]);

  if (!variant) return null;
  return (
    <>
      <Masthead manifest={manifest} activeKey={variant.key} onSwitch={onSwitch} />
      <Section0 variant={variant} manifest={manifest} />
      <div style={{ display: 'flex', alignItems: 'flex-start' }}>
        <Sidebar variant={variant} selection={sel} reps={reps} agentTypes={agentTypes} onToggle={onToggle} onReset={onReset} />
        <main style={{ padding: 24, color: 'var(--muted)', flex: 1 }}>
          Charts land in Plans 2b/2c. Active filters: {JSON.stringify({ task: sel.task, condition: sel.condition, rep: sel.rep, agent: sel.agent })}
        </main>
      </div>
    </>
  );
}
```

Also update the imports at the top of `App.tsx`: **replace** the Task 6 line `import type { Manifest, Selection, Variant } from './types';` with the wider set, and add the new component/data imports:
```tsx
import { Sidebar } from './components/Sidebar';
import type { Dimension } from './components/Sidebar';
import { Section0 } from './components/Section0';
import { presentAgentTypes, filteredTurns } from './data/filters';
import type { Manifest, Run, Selection, Turn, Variant } from './types';
```
And update the `ready` branch in `Gate` to pass the data through:
```tsx
if (status === 'ready' && data) return <Dashboard manifest={data.manifest} runs={data.runs} turns={data.turns} />;
```

- [ ] **Step 6: Create `web/README.md`**

```markdown
# CC Orchestration Report — frontend (SPA)

Vite + React + TypeScript SPA for the experiment report. Fetches raw rows from the
backend API (`serve/`) and renders the report client-side (Plan 2a = shell; charts in 2b/2c).

## Develop against a local backend

```bash
# terminal 1 — run the API from the repo root
make serve            # uvicorn on :8799, DATA_DIR=data/processed (run `make analyze` first)

# terminal 2 — run the SPA
cd web
echo 'VITE_API_BASE=http://localhost:8799' > .env.local   # not committed
npm install
npm run dev           # http://localhost:5173
```

On first load the app prompts for the **access token** (the backend's `API_TOKEN`; leave
the backend token unset for open local dev). It is stored in `localStorage` (`cc_report_token`).

## Build / deploy (Vercel)

- `npm run build` → `web/dist/`.
- In the Vercel project, set **Root Directory = `web`** and env var **`VITE_API_BASE`** to the
  Hugging Face Space URL. Add the Vercel production + preview origins to the backend's
  `ALLOWED_ORIGINS`.

## Test

`npm test` (Vitest). Pure logic (API client, URL state, filters) is unit-tested; components via React Testing Library.
```

- [ ] **Step 7: Run full suite + build**

Run: `cd web && npm test && npm run build`
Expected: all tests PASS (smoke + client + urlState + filters + DataContext + Masthead + Sidebar); build succeeds.

- [ ] **Step 8: Commit**

```bash
git add web/src/components/Sidebar.tsx web/src/components/Section0.tsx web/src/components/Sidebar.test.tsx web/src/App.tsx web/README.md
git commit -m "feat(web): sidebar filters, §0 band, and dev/deploy docs"
```

---

## Manual setup (one-time, outside this plan)

1. Create the Vercel project, set **Root Directory = `web`**, env `VITE_API_BASE` = the Space URL.
2. Add Vercel production + preview origins to the backend Space's `ALLOWED_ORIGINS` secret.

## Out of scope (this plan → Plans 2b / 2c)

- All charts (experiment matrix, condition comparison, overhead, quality-vs-cost, cache accumulation, hit-rate-vs-context, per-run cost timeline) and their data-shaping helpers — **Plan 2b**.
- §3 single-run drilldown + the context-source breakdown (compose/group modes, cache overlay, clickable text panel, component→`/context`-bucket mapping) — **Plan 2c**.
- Pixel-level styling parity, IBM Plex font loading, responsive breakpoints — refined alongside the charts.
