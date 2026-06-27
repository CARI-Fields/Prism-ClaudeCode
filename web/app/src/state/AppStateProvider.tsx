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
  // Double optional chain: guard against jsdom (no matchMedia) AND undefined result
  return window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ? 'dark' : 'light';
}

function bootstrap(manifest: Manifest): UiState {
  const url = parseHash(window.location.hash);
  const report = url.report && manifest.variants.some((v) => v.key === url.report) ? url.report : manifest.variants[0]?.key ?? '';
  const s = R.initUiState(report, initialTheme(url.theme), url.view ?? 'overview', url.filter);
  return url.s3Condition.length ? { ...s, overrides: { s3: { condition: url.s3Condition } } } : s;
}

interface Ctx { state: UiState; setState: React.Dispatch<React.SetStateAction<UiState>>; }
const StateCtx = createContext<Ctx | null>(null);
function useCtx(): Ctx { const v = useContext(StateCtx); if (!v) throw new Error('AppStateProvider missing'); return v; }

export function AppStateProvider({ manifest, children }: { manifest: Manifest; children: ReactNode }) {
  const [state, setState] = useState<UiState>(() => bootstrap(manifest));

  useEffect(() => {
    const next = toHash({ report: state.report, theme: state.theme, view: state.view, filter: state.filter, s3Condition: state.overrides.s3?.condition ?? [] });
    if (next !== window.location.hash) window.history.replaceState(null, '', next || window.location.pathname);
    localStorage.setItem(THEME_KEY, state.theme);
  }, [state.report, state.theme, state.view, state.filter, state.overrides]);

  const value = useMemo(() => ({ state, setState }), [state]);
  return <StateCtx.Provider value={value}><div className={`app-root${state.theme === 'dark' ? ' bp5-dark' : ''}`}>{children}</div></StateCtx.Provider>;
}

// Read-only state accessor; mutation flows through useTheme/useView/useReport/useFilter (no public dispatch by design).
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
