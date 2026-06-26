import { describe, expect, it } from 'vitest';
import type { Run } from '../types';
import { matrixData } from './matrix';

const runs = [
  { run_id: 'a1', task: 'coding', condition: 'single_agent', rep: 1, success: true },
  { run_id: 'a2', task: 'coding', condition: 'single_agent', rep: 1, success: false }, // later run_id wins
  { run_id: 'b1', task: 'coding', condition: 'subagents', rep: 1, success: true },
] as unknown as Run[];

describe('matrixData', () => {
  it('builds rows/cols and resolves status from the latest run', () => {
    const { rows, cols, cells } = matrixData(runs, ['coding'], [1], ['single_agent', 'subagents']);
    expect(rows).toEqual(['coding r1']);
    expect(cols).toEqual(['single_agent', 'subagents']);
    const sa = cells.find((c) => c.condition === 'single_agent' && c.rep === 1)!;
    expect(sa.status).toBe('failed'); // a2 (later) has success=false
    expect(sa.status_code).toBe(1);
  });
  it('marks absent cells missing (code 0)', () => {
    const { cells } = matrixData(runs, ['coding'], [2], ['single_agent']);
    expect(cells[0].status).toBe('missing');
    expect(cells[0].status_code).toBe(0);
  });
});
