import { useMemo, useState } from 'react';
import { Card, Elevation, HTMLSelect } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { inVariantRuns, scopeRuns } from '../data/filters';
import { EChart } from '../components/EChart';
import { matrixOption, conditionOption, overheadOption, efficiencyOption } from '../charts/section1Options';
import { conditionMetrics, conditionOverheads } from '../charts/conditionMetrics';
import { matrixData } from '../charts/matrix';
import { STATUS_COLORS, STATUS_GLYPHS } from '../charts/echartsTheme';

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

export function Section1View() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const [metric, setMetric] = useState('mean_completion_time_s');
  const [overhead, setOverhead] = useState('num_requests_factor');
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  const sel = effective('s1');
  const selTask = effectiveTask('s1');
  const scopedRuns = useMemo(
    () => (variant ? scopeRuns(inVariantRuns(data?.runs ?? [], variant), selTask, sel) : []),
    [data, variant, selTask, sel],
  );
  if (!variant) return null;

  const hasBaseline = variant.conditions.includes('single_agent');
  const conds = sel.condition.length ? sel.condition : variant.conditions;
  const tasks = selTask.length ? selTask : variant.tasks;
  const reps = Array.from(new Set(scopedRuns.map((r) => r.rep))).sort((a, b) => a - b);
  const metrics = conditionMetrics(scopedRuns, tasks, variant.conditions);
  const overheads = conditionOverheads(metrics, tasks, variant.conditions);
  const matrix = matrixData(scopedRuns, tasks, reps, conds);
  const metricLabel = METRICS.find(([v]) => v === metric)?.[1] ?? metric;
  const overheadLabel = OVERHEADS.find(([v]) => v === overhead)?.[1] ?? overhead;

  return (
    <div className="view view-grid">
      <Card elevation={Elevation.ZERO} className="panel-card">
        <h2 className="panel-title">Experiment matrix</h2>
        <EChart className="chart" themeMode={mode} option={matrixOption(matrix)} />
        <div className="status-key">{KEY_ORDER.map((i) => (
          <span key={i} className="status-swatch"><span style={{ background: STATUS_COLORS[i] }}>{STATUS_GLYPHS[i]}</span>{STATUS_LABELS[i]}</span>))}</div>
      </Card>
      <Card elevation={Elevation.ZERO} className="panel-card">
        <div className="panel-head"><h2 className="panel-title">Condition comparison</h2>
          <HTMLSelect value={metric} onChange={(e) => setMetric(e.currentTarget.value)} aria-label="metric">
            {METRICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</HTMLSelect></div>
        <EChart className="chart" themeMode={mode} option={conditionOption(metrics, conds, tasks, metric, metricLabel)} />
      </Card>
      {hasBaseline && (
        <Card elevation={Elevation.ZERO} className="panel-card">
          <div className="panel-head"><h2 className="panel-title">Overhead vs single agent</h2>
            <HTMLSelect value={overhead} onChange={(e) => setOverhead(e.currentTarget.value)} aria-label="resource">
              {OVERHEADS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</HTMLSelect></div>
          <EChart className="chart" themeMode={mode} option={overheadOption(overheads, conds, tasks, overhead, overheadLabel)} />
        </Card>
      )}
      <Card elevation={Elevation.ZERO} className="panel-card">
        <h2 className="panel-title">Quality vs cost map</h2>
        <EChart className="chart" themeMode={mode} option={efficiencyOption(metrics, conds, tasks[0] ?? '')} />
      </Card>
    </div>
  );
}
