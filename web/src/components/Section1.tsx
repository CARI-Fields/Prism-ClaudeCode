import { useMemo, useState } from 'react';
import type { AppState, Run, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';
import { EChart } from './EChart';
import { matrixOption, conditionOption, overheadOption, efficiencyOption } from '../charts/section1Options';
import { conditionMetrics, conditionOverheads } from '../charts/conditionMetrics';
import { matrixData } from '../charts/matrix';
import { STATUS_COLORS, STATUS_GLYPHS } from '../charts/echartsTheme';

interface Props {
  variant: Variant; state: AppState; runs: Run[];
  onToggle: (dim: 'condition', token: string) => void; onClear: (dim: 'condition') => void;
}

const METRICS = [
  ['mean_completion_time_s', 'Mean completion time (s)'], ['mean_num_requests', 'Mean requests'],
  ['mean_total_cost_usd', 'Mean total cost ($)'], ['mean_quality_score', 'Mean quality score'],
  ['mean_cost_efficiency_score', 'Mean cost efficiency'], ['mean_speedup', 'Mean coding speedup'],
  ['mean_research_rubric_score', 'Mean research rubric score'], ['mean_peak_prompt_tokens', 'Mean peak prompt tokens'],
  ['mean_total_cache_read', 'Mean cache read tokens'], ['mean_cache_hit_ratio', 'Mean cache hit ratio'],
  ['success_rate', 'Success rate'],
] as const;

const OVERHEADS = [
  ['num_requests_factor', 'Requests'], ['completion_time_factor', 'Completion time'],
  ['total_cost_factor', 'Total cost'], ['peak_prompt_tokens_factor', 'Peak prompt tokens'],
  ['total_cache_read_factor', 'Cache reads'], ['output_tokens_factor', 'Output tokens'],
] as const;

const KEY_ORDER = [2, 1, 3, 0] as const;
const STATUS_LABELS = ['missing', 'failed', 'success', 'skipped'] as const;

export function Section1({ variant, state, runs, onToggle, onClear }: Props) {
  const [metric, setMetric] = useState('mean_completion_time_s');
  const [overhead, setOverhead] = useState('num_requests_factor');

  const hasBaseline = variant.conditions.includes('single_agent');

  const conds = state.s1.condition.length ? state.s1.condition : variant.conditions;
  const tasks = state.task.length ? state.task : variant.tasks;
  const reps = useMemo(
    () => Array.from(new Set(runs.map((r) => r.rep))).sort((a, b) => a - b),
    [runs],
  );

  const metrics = useMemo(() => conditionMetrics(runs, tasks, variant.conditions), [runs, tasks, variant.conditions]);
  const overheads = useMemo(() => conditionOverheads(metrics, tasks, variant.conditions), [metrics, tasks, variant.conditions]);
  const matrix = useMemo(() => matrixData(runs, tasks, reps, conds), [runs, tasks, reps, conds]);

  const metricLabel = METRICS.find(([v]) => v === metric)?.[1] ?? metric;
  const overheadLabel = OVERHEADS.find(([v]) => v === overhead)?.[1] ?? overhead;

  return (
    <section className="band band-agg">
      <div className="band-head">
        <div className="band-label"><span className="band-no">§1</span>Averages across conditions</div>
        <div className="band-scope">Mean across rollouts · the Experiment matrix shows every rollout</div>
      </div>
      <div className="fstrip">
        <FilterChunk tag="Feature" items={variant.conditions} active={state.s1.condition}
          onToggle={(t) => onToggle('condition', t)} onClear={() => onClear('condition')} dotFor={conditionColor} />
      </div>
      <div className="grid">
        <article className="panel">
          <div className="panel-head"><h2>Experiment matrix</h2></div>
          <EChart className="chart" option={matrixOption(matrix)} />
          <div className="status-key" id="matrix-key">
            {KEY_ORDER.map((i) => (
              <span key={i} className="status-swatch">
                <span style={{ background: STATUS_COLORS[i] }}>{STATUS_GLYPHS[i]}</span>
                {STATUS_LABELS[i]}
              </span>
            ))}
          </div>
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Condition comparison</h2>
            <div className="control-group">
              <label className="control inline">metric
                <select value={metric} onChange={(e) => setMetric(e.target.value)}>
                  {METRICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            </div>
          </div>
          <EChart className="chart" option={conditionOption(metrics, conds, tasks, metric, metricLabel)} />
        </article>
        {hasBaseline && (
          <article className="panel" id="overhead-panel">
            <div className="panel-head"><h2>Overhead vs single agent</h2>
              <div className="control-group">
                <label className="control inline">resource
                  <select value={overhead} onChange={(e) => setOverhead(e.target.value)}>
                    {OVERHEADS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </label>
              </div>
            </div>
            <EChart className="chart" option={overheadOption(overheads, conds, tasks, overhead, overheadLabel)} />
          </article>
        )}
        <article className="panel">
          <div className="panel-head"><h2>Quality vs cost map</h2></div>
          <EChart className="chart" option={efficiencyOption(metrics, conds, tasks[0] ?? '')} />
        </article>
      </div>
    </section>
  );
}
