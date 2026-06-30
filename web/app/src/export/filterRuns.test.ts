import { describe, expect, it } from 'vitest';
import { filterRuns } from './filterRuns';
import type { Run } from '../types';

const runs = [
  { run_id: 'a1', task: 'coding', condition: 'goal', rep: 1 },
  { run_id: 'b2', task: 'research', condition: 'subagents', rep: 2 },
  { run_id: 'c3', task: 'coding', condition: 'subagents', rep: 1 },
] as unknown as Run[];
const EMPTY = { task: [], condition: [], rep: [], query: '' };
const ids = (rs: Run[]) => rs.map((r) => r.run_id);

describe('filterRuns', () => {
  it('returns all runs when the filter is empty', () => {
    expect(ids(filterRuns(runs, EMPTY))).toEqual(['a1', 'b2', 'c3']);
  });
  it('narrows by task / condition / rep chips', () => {
    expect(ids(filterRuns(runs, { ...EMPTY, task: ['coding'] }))).toEqual(['a1', 'c3']);
    expect(ids(filterRuns(runs, { ...EMPTY, condition: ['subagents'] }))).toEqual(['b2', 'c3']);
    expect(ids(filterRuns(runs, { ...EMPTY, rep: ['r2'] }))).toEqual(['b2']);
  });
  it('narrows by case-insensitive search over run_id/task/condition/rep', () => {
    expect(ids(filterRuns(runs, { ...EMPTY, query: 'goal' }))).toEqual(['a1']);
    expect(ids(filterRuns(runs, { ...EMPTY, query: 'A1' }))).toEqual(['a1']);
    expect(ids(filterRuns(runs, { ...EMPTY, query: 'research' }))).toEqual(['b2']);
  });
  it('combines chips and search', () => {
    expect(ids(filterRuns(runs, { ...EMPTY, task: ['coding'], query: 'subagents' }))).toEqual([
      'c3',
    ]);
  });
});
