import { describe, expect, it } from 'vitest';
import { parseHash, toHash } from './urlState';

describe('urlState', () => {
  it('round-trips report/theme/view/filter', () => {
    const u = { report: 'r1', theme: 'dark' as const, view: 's2' as const,
      filter: { task: ['coding'], condition: ['goal', 'subagents'], rep: ['r1'], agent: [] },
      s3Condition: ['goal'] };
    expect(parseHash(toHash(u))).toEqual({
      report: 'r1', theme: 'dark', view: 's2',
      filter: { task: ['coding'], condition: ['goal', 'subagents'], rep: ['r1'], agent: [] },
      s3Condition: ['goal'],
    });
  });
  it('parses a minimal hash', () => {
    expect(parseHash('#report=r1')).toEqual({ report: 'r1', theme: null, view: null, filter: { task: [], condition: [], rep: [], agent: [] }, s3Condition: [] });
  });
  it('empty state → empty hash', () => {
    expect(toHash({ report: null, theme: null, view: null, filter: { task: [], condition: [], rep: [], agent: [] }, s3Condition: [] })).toBe('');
  });
  it('rejects invalid theme/view to null', () => {
    expect(parseHash('#theme=bogus').theme).toBe(null);
    expect(parseHash('#theme=DARK').theme).toBe(null);
    expect(parseHash('#view=dashboard').view).toBe(null);
    expect(parseHash('#view=S1').view).toBe(null);
  });
  it('parses s3cond from hash', () => {
    expect(parseHash('#s3cond=goal,subagents').s3Condition).toEqual(['goal', 'subagents']);
  });
});
