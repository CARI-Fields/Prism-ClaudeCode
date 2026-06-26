import { describe, expect, it } from 'vitest';
import { clearSection, initState, selectSectionSingle, setReport, toggleSection, toggleTask } from './appState';

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
  it('selectSectionSingle picks a single token, replacing any prior selection', () => {
    let s = initState('r', []);
    s = selectSectionSingle(s, 's3', 'condition', 'goal');
    expect(s.s3.condition).toEqual(['goal']);
    s = selectSectionSingle(s, 's3', 'condition', 'subagents');
    expect(s.s3.condition).toEqual(['subagents']); // replaces, never accumulates
  });
  it('selectSectionSingle collapses a prior multi-selection to one token', () => {
    let s = toggleSection(initState('r', []), 's3', 'condition', 'goal');
    s = toggleSection(s, 's3', 'condition', 'subagents');
    expect(s.s3.condition).toEqual(['goal', 'subagents']);
    s = selectSectionSingle(s, 's3', 'condition', 'loop_dynamic');
    expect(s.s3.condition).toEqual(['loop_dynamic']);
  });
  it('selectSectionSingle re-clicking the sole selected token clears to all (empty)', () => {
    let s = selectSectionSingle(initState('r', []), 's3', 'condition', 'goal');
    s = selectSectionSingle(s, 's3', 'condition', 'goal');
    expect(s.s3.condition).toEqual([]);
  });
  it('selectSectionSingle only affects the named scope+dimension', () => {
    let s = toggleSection(initState('r', []), 's3', 'rep', 'r1');
    s = selectSectionSingle(s, 's3', 'condition', 'goal');
    expect(s.s3.rep).toEqual(['r1']); // other dims untouched
    expect(s.s1.condition).toEqual([]);
    expect(s.s2.condition).toEqual([]);
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
