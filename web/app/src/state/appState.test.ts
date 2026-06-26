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
