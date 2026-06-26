import { describe, expect, it } from 'vitest';
import { conditionMetrics, conditionOverheads } from './conditionMetrics';
import { matrixData } from './matrix';
import { conditionOption, efficiencyOption, matrixOption, overheadOption } from './section1Options';
import type { Run } from '../types';

const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, success: true, num_requests: 4, total_cost_usd: 0.1, quality_score: 2, speedup: 1.5 },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 1, success: true, num_requests: 8, total_cost_usd: 0.5, quality_score: 3, speedup: 2.0 },
] as unknown as Run[];
const conds = ['single_agent', 'subagents'];

describe('section1 option builders', () => {
  it('matrixOption is a heatmap with status-coded cells + STATUS_COLORS visualMap', () => {
    const opt = matrixOption(matrixData(runs, ['coding'], [1], conds)) as any;
    expect(opt.series[0].type).toBe('heatmap');
    expect(opt.visualMap.inRange.color).toEqual(['#eef1f5', '#e03131', '#2f9e44', '#adb5bd']);
    expect(opt.series[0].data).toHaveLength(2); // 1 row × 2 conds
  });
  it('conditionOption single-task: one bar series, value per condition', () => {
    const m = conditionMetrics(runs, ['coding'], conds);
    const opt = conditionOption(m, conds, ['coding'], 'mean_num_requests', 'Mean requests') as any;
    expect(opt.series).toHaveLength(1);
    expect(opt.series[0].type).toBe('bar');
    expect(opt.series[0].data).toEqual([4, 8]);
  });
  it('overheadOption has a baseline markLine on the first series', () => {
    const m = conditionMetrics(runs, ['coding'], conds);
    const o = conditionOverheads(m, ['coding'], conds);
    const opt = overheadOption(o, conds, ['coding'], 'num_requests_factor', 'Requests') as any;
    expect(opt.series[0].markLine.data[0].yAxis).toBe(1);
  });
  it('efficiencyOption: scatter, coding quality = speedup', () => {
    const m = conditionMetrics(runs, ['coding'], conds);
    const opt = efficiencyOption(m, conds, 'coding') as any;
    expect(opt.series[0].type).toBe('scatter');
    const sub = opt.series.find((s: any) => s.name === 'subagents');
    expect(sub.data[0][1]).toBeCloseTo(2.0); // y = mean_speedup for coding
  });
});
