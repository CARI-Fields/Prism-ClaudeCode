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
