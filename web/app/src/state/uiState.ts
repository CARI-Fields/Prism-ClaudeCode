import type { FilterDim, GlobalFilter, SectionSel, ThemeMode, UiState, ViewKey } from '../types';

export type { SectionSel };

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
