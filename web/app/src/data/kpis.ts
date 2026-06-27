import type { Run } from '../types';

export interface Kpis {
  runs: number;
  meanRequests: number | null;
  meanCost: number | null;
  meanQuality: number | null;
  meanCacheHit: number | null;
}
function mean(values: Array<number | null | undefined>): number | null {
  const nums = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
}
export function computeKpis(runs: Run[]): Kpis {
  return {
    runs: runs.length,
    meanRequests: mean(runs.map((r) => r.num_requests)),
    meanCost: mean(runs.map((r) => r.total_cost_usd)),
    meanQuality: mean(runs.map((r) => r.quality_score)),
    meanCacheHit: mean(runs.map((r) => r.cache_hit_ratio)),
  };
}
