import { describe, expect, it } from 'vitest';
import type { Run } from '../types';
import { conditionMetrics, conditionOverheads } from './conditionMetrics';

const runs = [
  {
    task: 'coding',
    condition: 'single_agent',
    rep: 1,
    success: true,
    num_requests: 4,
    total_cost_usd: 0.1,
    quality_score: 2,
  },
  {
    task: 'coding',
    condition: 'single_agent',
    rep: 2,
    success: false,
    num_requests: 6,
    total_cost_usd: 0.3,
    quality_score: null,
  },
  {
    task: 'coding',
    condition: 'subagents',
    rep: 1,
    success: true,
    num_requests: 8,
    total_cost_usd: 0.5,
    quality_score: 3,
  },
] as unknown as Run[];

describe('conditionMetrics', () => {
  it('means skip nulls; success averaged as 1/0; runs counted', () => {
    const m = conditionMetrics(runs, ['coding'], ['single_agent', 'subagents']);
    const sa = m.find((r) => r.task === 'coding' && r.condition === 'single_agent')!;
    expect(sa.runs).toBe(2);
    expect(sa.mean_num_requests).toBeCloseTo(5);
    expect(sa.success_rate).toBeCloseTo(0.5);
    expect(sa.mean_quality_score).toBeCloseTo(2); // one null skipped
  });
  it('emits an "all" scope aggregating across tasks', () => {
    const m = conditionMetrics(runs, ['coding'], ['single_agent']);
    expect(m.some((r) => r.task === 'all' && r.condition === 'single_agent')).toBe(true);
  });
});

describe('conditionOverheads', () => {
  it('factor = condition mean / single_agent mean; null when no baseline', () => {
    const m = conditionMetrics(runs, ['coding'], ['single_agent', 'subagents']);
    const o = conditionOverheads(m, ['coding'], ['single_agent', 'subagents']);
    const sub = o.find((r) => r.task === 'coding' && r.condition === 'subagents')!;
    expect(sub.num_requests_factor).toBeCloseTo(8 / 5); // 1.6
    const sa = o.find((r) => r.task === 'coding' && r.condition === 'single_agent')!;
    expect(sa.num_requests_factor).toBeCloseTo(1);
    const noBase = conditionOverheads(
      conditionMetrics(runs, ['coding'], ['subagents']),
      ['coding'],
      ['subagents'],
    );
    expect(noBase[0].num_requests_factor).toBeNull();
  });
});
