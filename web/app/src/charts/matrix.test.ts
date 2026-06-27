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
  it('labels long-horizon rows by their bare domain (cell.row matches the axis row)', () => {
    const lh = [{ run_id: 'c1', task: 'coding_longhorizon', condition: 'goal', rep: 1, success: true }] as unknown as Run[];
    const { rows, cells } = matrixData(lh, ['coding_longhorizon'], [1], ['goal']);
    expect(rows).toEqual(['coding r1']);          // axis label is the bare domain…
    expect(cells[0].row).toBe('coding r1');         // …and the cell joins on the same label
    expect(cells[0].task).toBe('coding_longhorizon'); // raw key preserved for data ops
  });
});
