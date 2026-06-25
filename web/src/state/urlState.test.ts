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
