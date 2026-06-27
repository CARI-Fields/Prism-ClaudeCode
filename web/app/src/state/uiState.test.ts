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
  it('a cleared §3 override falls back to the global filter (no shadowing)', () => {
    let s = toggleFilter(base, 'condition', 'goal');            // global condition = ['goal']
    s = setOverrideSingle(s, 's3', 'condition', 'subagents');   // §3 pinned to ['subagents']
    expect(effectiveSel(s, 's3').condition).toEqual(['subagents']);
    s = setOverrideSingle(s, 's3', 'condition', 'subagents');   // re-click → clears to []
    expect(s.overrides.s3?.condition).toEqual([]);              // still stores []
    expect(effectiveSel(s, 's3').condition).toEqual(['goal']);  // but falls back to global
  });
});
