import type { AppState, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';

interface Props {
  variant: Variant; state: AppState;
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

export function Section1({ variant, state, onToggle, onClear }: Props) {
  const hasBaseline = variant.conditions.includes('single_agent');
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
          <div id="matrix-chart" className="chart" />
          <div className="status-key" id="matrix-key" />
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Condition comparison</h2>
            <div className="control-group">
              <label className="control inline">metric
                <select defaultValue="mean_completion_time_s">
                  {METRICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            </div>
          </div>
          <div id="condition-chart" className="chart" />
        </article>
        {hasBaseline && (
          <article className="panel" id="overhead-panel">
            <div className="panel-head"><h2>Overhead vs single agent</h2>
              <div className="control-group">
                <label className="control inline">resource
                  <select defaultValue="num_requests_factor">
                    {OVERHEADS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </label>
              </div>
            </div>
            <div id="overhead-chart" className="chart" />
          </article>
        )}
        <article className="panel">
          <div className="panel-head"><h2>Quality vs cost map</h2></div>
          <div id="efficiency-chart" className="chart" />
        </article>
      </div>
    </section>
  );
}
