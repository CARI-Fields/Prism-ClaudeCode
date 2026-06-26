import type { Run } from '../types';

export interface MetricRow {
  task: string; condition: string; runs: number;
  success_rate: number | null;
  mean_completion_time_s: number | null; mean_num_requests: number | null;
  mean_cache_hit_ratio: number | null; mean_total_cache_read: number | null;
  mean_peak_prompt_tokens: number | null; mean_output_tokens_total: number | null;
  mean_total_cost_usd: number | null; mean_quality_score: number | null;
  mean_cost_efficiency_score: number | null; mean_speedup: number | null;
  mean_research_rubric_score: number | null;
}
type MeanKey = Exclude<keyof MetricRow, 'task' | 'condition' | 'runs' | 'success_rate'>;

const COLUMN_OF: Record<MeanKey, string> = {
  mean_completion_time_s: 'completion_time_s', mean_num_requests: 'num_requests',
  mean_cache_hit_ratio: 'cache_hit_ratio', mean_total_cache_read: 'total_cache_read',
  mean_peak_prompt_tokens: 'peak_prompt_tokens', mean_output_tokens_total: 'output_tokens_total',
  mean_total_cost_usd: 'total_cost_usd', mean_quality_score: 'quality_score',
  mean_cost_efficiency_score: 'cost_efficiency_score', mean_speedup: 'speedup',
  mean_research_rubric_score: 'research_rubric_score',
};

function num(v: unknown): number | null {
  if (typeof v === 'boolean') return v ? 1 : 0;
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}
function mean(runs: Run[], column: string): number | null {
  const xs: number[] = [];
  for (const r of runs) { const n = num(r[column]); if (n !== null) xs.push(n); }
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
}
function metricRow(task: string, condition: string, runs: Run[]): MetricRow {
  const row = { task, condition, runs: runs.length, success_rate: mean(runs, 'success') } as MetricRow;
  for (const key of Object.keys(COLUMN_OF) as MeanKey[]) row[key] = mean(runs, COLUMN_OF[key]);
  return row;
}
export function conditionMetrics(runs: Run[], tasks: string[], conditions: string[]): MetricRow[] {
  const out: MetricRow[] = [];
  for (const task of ['all', ...tasks]) {
    const taskRuns = task === 'all' ? runs : runs.filter((r) => r.task === task);
    for (const condition of conditions) {
      out.push(metricRow(task, condition, taskRuns.filter((r) => r.condition === condition)));
    }
  }
  return out;
}

export interface OverheadRow {
  task: string; condition: string;
  num_requests_factor: number | null; completion_time_factor: number | null;
  total_cost_factor: number | null; peak_prompt_tokens_factor: number | null;
  total_cache_read_factor: number | null; output_tokens_factor: number | null;
}
function safeFactor(v: number | null, b: number | null): number | null {
  if (v == null || b == null || !Number.isFinite(v) || !Number.isFinite(b) || b === 0) return null;
  return v / b;
}
export function conditionOverheads(metrics: MetricRow[], tasks: string[], conditions: string[]): OverheadRow[] {
  const out: OverheadRow[] = [];
  for (const task of ['all', ...tasks]) {
    const rows = metrics.filter((m) => m.task === task);
    const base = rows.find((m) => m.condition === 'single_agent');
    for (const condition of conditions) {
      const row = rows.find((m) => m.condition === condition);
      const f = (k: MeanKey) => safeFactor(row ? row[k] : null, base ? base[k] : null);
      out.push({
        task, condition,
        completion_time_factor: f('mean_completion_time_s'),
        num_requests_factor: f('mean_num_requests'),
        total_cost_factor: f('mean_total_cost_usd'),
        peak_prompt_tokens_factor: f('mean_peak_prompt_tokens'),
        total_cache_read_factor: f('mean_total_cache_read'),
        output_tokens_factor: f('mean_output_tokens_total'),
      });
    }
  }
  return out;
}
