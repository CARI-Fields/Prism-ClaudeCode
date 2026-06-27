# Web report — Palantir-style redesign (design)

Date: 2026-06-26
Status: approved (pending spec review)
Scope: `web/app` frontend only

## 1. Context

`web/app` is a Vite + React 18 + TypeScript SPA that renders the Claude Code
orchestration experiment report. It loads raw rows from the read-only FastAPI +
DuckDB backend (`web/api`), filters them client-side, and draws ECharts charts.

Today the app is a **single long scrolling report**:

- `Masthead` with a variant switcher and a tri-color top border
- `GlobalTaskStrip` (task selector)
- `BriefBand` (task/strategy orientation) + `KpiBand`
- three stacked bands: **§1 aggregate**, **§2 distribution**, **§3 single-run drilldown**
- styling is hand-written CSS (`src/styles.css`) ported verbatim from
  `analysis/reports/report.html`; each section keeps its **own independent**
  filter state (`s1` / `s2` / `s3` in `state/appState.ts`).

The look is already dense and analytical (IBM Plex Sans/Mono, restrained
accents), which is adjacent to the Palantir family but not deliberately built on
a design system, lacks dark mode, and the per-section filter model fragments the
exploration experience.

## 2. Goals

Comprehensive redesign of the frontend toward a Palantir (Blueprint / Foundry /
Workshop) idiom, on three axes at once:

1. **Re-theme** to a real design-token system with **light + dark**, toggleable.
2. **Rework interaction / information architecture** into an app-shell with a
   persistent global filter rail and switchable views.
3. **Clean up component architecture** — clear, single-purpose units behind
   well-defined interfaces, built on Palantir's actual design system.

## 3. Decisions (locked)

| Axis | Decision |
| --- | --- |
| Effort | Comprehensive (re-theme + IA rework + architecture cleanup) |
| Design system | **Blueprint.js** (`@blueprintjs/core`), Palantir's own React kit |
| Color mode | **Light + dark**, token-driven, user toggle (persisted) |
| Layout / IA | **App shell**: top bar + persistent left **filter rail** + switchable **views** (Overview / §1 / §2 / §3) |
| Filter model | **Global cross-filter + per-view overrides** |
| Migration | **Big-bang rewrite** of `web/app/src/` in the new structure, in an isolated worktree |
| Charts | Keep **ECharts**; re-theme for light/dark |

## 4. Non-goals / scope boundary

- **Backend is out of scope.** `web/api` already serves
  manifest / runs / turns / components / token-rates; we consume it unchanged.
  We touch it only if a view genuinely needs data not already exposed (not
  expected).
- No change to **what** the report measures — same metrics, same charts'
  semantics. This is presentation + interaction + architecture, not new analysis.
- No backend auth/deploy change beyond what the new build output requires
  (Vercel root dir stays `web`; the token gate is preserved, restyled).

## 5. Target architecture (frontend)

### 5.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ TopBar:  CC Report   [Variant switcher ▾]        [☀/☾]   [⟳]     │
├────────────┬────────────────────────────────────────────────────┤
│ FilterRail │  ViewCanvas                                         │
│ (global)   │   ┌──────────────────────────────────────────────┐ │
│  Task      │   │ ViewNav:  Overview · §1 Agg · §2 Dist · §3 Run│ │
│  Condition │   ├──────────────────────────────────────────────┤ │
│  Rep       │   │  active view — Blueprint panels + ECharts     │ │
│  Agent     │   │  (themed light/dark)                          │ │
│  [Reset]   │   └──────────────────────────────────────────────┘ │
└────────────┴────────────────────────────────────────────────────┘
```

### 5.2 Component tree (new)

- **`AppShell`** — Blueprint `Navbar` + two-pane (rail + canvas) layout; owns the
  theme-root element that carries the `.bp5-dark` class.
  - **`TopBar`** — title, `VariantSwitcher` (Blueprint `Tabs`/`Select`),
    `ThemeToggle` (Blueprint `Switch`), reload action.
  - **`FilterRail`** — the global filter UI: Task / Condition / Rep / Agent and a
    Reset; rendered with Blueprint controls. Reads/writes `FilterContext`.
  - **`ViewCanvas`** — `ViewNav` (Blueprint `Tabs`) + the active view.
- **Views** (presentational; consume filtered data + theme):
  `OverviewView`, `Section1View`, `Section2View`, `Section3View`.
- **Contexts**:
  - `ThemeContext` / `ThemeProvider` — `'light' | 'dark'`, persisted to
    `localStorage`, mirrored to the URL.
  - `FilterContext` / `FilterProvider` — the global filter + per-view overrides.
  - `DataContext` — **unchanged** (loads + holds the raw bundle).

### 5.3 Salvaged (kept, not rewritten)

These are pure and well-tested; the rewrite reuses them as-is (charts gain a
`theme` input only):

- `api/client.ts`, `api/token.ts`
- `data/filters.ts` (`scopeRuns` / `scopeTurns` / `presentAgentTypes`),
  `data/kpis.ts`, `data/DataContext.tsx`
- `charts/*` option builders + helpers (`echartsCore`, `echartsTheme`, `format`,
  `matrix`, `ordered`, `agentSymbols`, `section1Options`, `section2Options`,
  `contextBreakdown`, `contextOption`, `costTimeline`, `cacheTimeline`,
  `conditionMetrics`)
- `theme.ts` condition/source **hues** (neutrals move to tokens)
- `types.ts` data interfaces (`Run`/`Turn`/`Component`/`Variant`/`Manifest`)

### 5.4 Replaced / new

- `Masthead` → `TopBar`; `GlobalTaskStrip` + `Chip` + `FilterChunk` →
  `FilterRail`; `BriefBand` + `KpiBand` → folded into `OverviewView`;
  `Section1/2/3` → `Section1View/Section2View/Section3View`.
- `EChart` kept but made **theme-aware**; `ContextTextPanel` and `TokenGate`
  kept but restyled with Blueprint.
- New: `AppShell`, `TopBar`, `FilterRail`, `ViewCanvas`, `ViewNav`,
  `ThemeProvider`, `FilterProvider`, `OverviewView`, plus the ECharts
  light/dark themes and the token stylesheet.

## 6. Theme system

- **Tokens** as CSS custom properties layered over Blueprint's `--bp` variables,
  in two sets (light/dark). The shell root toggles `.bp5-dark`; tokens resolve
  per mode. Toggle persisted to `localStorage` and reflected in the URL.
- **ECharts**: register a `light` and a `dark` ECharts theme (transparent
  background; axis / grid / split-line / label colors from tokens). The
  `EChart` component reads `ThemeContext` and re-renders the option under the
  active theme. Condition/source **hues** stay constant across modes for
  recognizability; only neutrals swap.
- Respect `prefers-color-scheme` for the initial mode when no stored preference
  and no URL override exist.

## 7. Filter model & state

Replace `AppState { report, task, s1, s2, s3 }` with:

```ts
interface UiState {
  report: string;                 // variant key
  theme: 'light' | 'dark';
  view: 'overview' | 's1' | 's2' | 's3';
  filter: GlobalFilter;           // { task: string[]; condition: string[]; rep: string[]; agent: string[] }
  overrides: Partial<Record<ViewKey, Partial<GlobalFilter>>>; // per-view local semantics
}
```

- The **global** filter drives every view. A view that needs different semantics
  declares an **override** — notably **§3**, whose Feature (condition) selection
  is **single-select** for the single-run drilldown (preserving the behavior
  established by commit `73cd514`). Overrides are shallow-merged onto the global
  filter when scoping that view's data.
- Reducers stay **pure** (mirroring today's `appState.ts`): `setReport`,
  `setView`, `setTheme`, `toggleFilter`, `clearFilter`, `setOverrideSingle`, etc.
- The effective selection for a view = `merge(filter, overrides[view])`, fed to
  the salvaged `scopeRuns` / `scopeTurns`.

## 8. URL state

Extend `state/urlState.ts` to encode `report + view + theme + filter` (and any
active override) in the hash, so **any filtered view is deep-linkable and
shareable** — a core Palantir behavior. `parseHash`/`toHash` round-trip is unit
tested. Switching report resets filter + overrides (as today).

## 9. Views

- **OverviewView** (new): the at-a-glance summary — variant brief + strategy
  legend (from `BriefBand`) and the KPI band (from `KpiBand`) as Blueprint
  `Card`s, plus a compact §1 headline chart. Entry point / landing view.
- **Section1View** (§1 aggregate): the condition-level aggregate charts
  (`section1Options`), in Blueprint panels.
- **Section2View** (§2 distribution): per-turn distribution charts
  (`section2Options`, cache timeline, zoom) in Blueprint panels.
- **Section3View** (§3 single-run drilldown): per-run cost timeline +
  context-source breakdown + clickable text panel (`ContextTextPanel`), with the
  single-select Feature override.

## 10. Rebuild approach (big-bang) & internal order

The rewrite happens entirely in this worktree, so `master` is never red. To keep
the final state coherent and reviewable, build in this internal order (the
detailed plan is produced by `writing-plans`):

1. **Foundation** — add `@blueprintjs/core` (+ icons), the token stylesheet,
   `ThemeProvider`, and the light/dark ECharts themes. Make `EChart`
   theme-aware. Suite stays green for salvaged modules.
2. **Shell** — `AppShell`, `TopBar`, `FilterRail`, `ViewCanvas`, `ViewNav`,
   `FilterProvider`; wire URL state. New tests for shell + contexts.
3. **Views** — build `OverviewView`, then port §1, §2, §3 into views using the
   salvaged chart builders; apply per-view override for §3.
4. **Cleanup** — delete superseded components, restyle `TokenGate`/
   `ContextTextPanel`, a11y + responsive pass, full green suite, manual smoke.

## 11. Testing strategy

- **Pure-logic tests carry over unchanged**: `data/filters`, `data/kpis`,
  `charts/*`, the new reducers, `urlState` round-trip.
- **Component tests** move from class-name selectors (`.chip`, `.panel`) to
  **roles/text** (Blueprint renames classes to `.bp5-*`) — the more robust
  Testing-Library style.
- **New tests**: `ThemeProvider` (toggle + persistence + URL), `FilterProvider`
  (global + override merge), `AppShell`/`ViewNav` (view switching), URL
  round-trip with the extended state.
- **Definition of done**: full `npm test` green; manual smoke in both themes
  against a local backend; build (`npm run build`) succeeds.

## 12. Risks & mitigations

- **Big-bang red window** → contained to the worktree; salvage pure modules to
  shrink the rewrite; internal build order returns the suite to green in stages;
  final review gated by a full green run.
- **Blueprint bundle size / CSS namespace clash with ECharts** → import only
  `@blueprintjs/core` (+ icons) we use; keep ECharts containers outside
  Blueprint-styled text where needed; verify build size after foundation.
- **Behavior regressions in §3 drilldown** → preserve single-select Feature via
  explicit override + a dedicated test mirroring `73cd514`.
- **Deep-link/back-button regressions** → URL round-trip tests + manual check.

## 13. Open questions

- Default landing view — Overview (assumed) vs. last-viewed (URL) — Overview when
  no hash; URL wins when present.
- Whether to expose a "reset all" vs per-dimension clears in the rail (assume
  both: per-dimension clear + a global Reset).

## 14. Success criteria

- App-shell with persistent global filter rail and 4 switchable views.
- Working light/dark toggle across chrome **and** charts, persisted + shareable.
- Global cross-filtering with §3's single-run override intact.
- Clean component boundaries on Blueprint; full test suite green; build passes.
