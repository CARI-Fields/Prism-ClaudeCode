import { describe, expect, it } from 'vitest';
import type { Run } from '../types';
import { computeKpis } from './kpis';

const runs = [
  { num_requests: 5, total_cost_usd: 0.1, quality_score: 2, cache_hit_ratio: 0.9 },
  { num_requests: 7, total_cost_usd: 0.3, quality_score: null, cache_hit_ratio: 0.7 },
] as unknown as Run[];

describe('computeKpis', () => {
  it('counts runs and means non-null values', () => {
    const k = computeKpis(runs);
    expect(k.runs).toBe(2);
    expect(k.meanRequests).toBeCloseTo(6);
    expect(k.meanCost).toBeCloseTo(0.2);
    expect(k.meanQuality).toBeCloseTo(2); // only one non-null
    expect(k.meanCacheHit).toBeCloseTo(0.8);
  });
  it('returns nulls for empty input', () => {
    expect(computeKpis([])).toEqual({ runs: 0, meanRequests: null, meanCost: null, meanQuality: null, meanCacheHit: null });
  });
});
