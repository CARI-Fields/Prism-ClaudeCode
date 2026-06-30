import { useMemo, useState } from 'react';
import { Card, Elevation, HTMLSelect } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { inVariantRuns, scopeRuns } from '../data/filters';
import { EChart } from '../components/EChart';
import { conditionOption, overheadOption, efficiencyOption } from '../charts/section1Options';
import { conditionMetrics, conditionOverheads } from '../charts/conditionMetrics';
import { computeKpis } from '../data/kpis';

const METRICS = [
  ['mean_completion_time_s', 'Mean completion time (s)'],
  ['mean_num_requests', 'Mean requests'],
  ['mean_total_cost_usd', 'Mean total cost ($)'],
  ['mean_quality_score', 'Mean quality score'],
  ['mean_cost_efficiency_score', 'Mean cost efficiency'],
  ['mean_speedup', 'Mean coding speedup'],
  ['mean_research_rubric_score', 'Mean research rubric score'],
  ['mean_peak_prompt_tokens', 'Mean peak prompt tokens'],
  ['mean_total_cache_read', 'Mean cache read tokens'],
  ['mean_cache_hit_ratio', 'Mean cache hit ratio'],
  ['success_rate', 'Success rate'],
] as const;
const OVERHEADS = [
  ['num_requests_factor', 'Requests'],
  ['completion_time_factor', 'Completion time'],
  ['total_cost_factor', 'Total cost'],
  ['peak_prompt_tokens_factor', 'Peak prompt tokens'],
  ['total_cache_read_factor', 'Cache reads'],
  ['output_tokens_factor', 'Output tokens'],
] as const;
export function Section1View() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const [metric, setMetric] = useState('mean_completion_time_s');
  const [overhead, setOverhead] = useState('num_requests_factor');
  const variant =
    data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
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
  const metrics = conditionMetrics(scopedRuns, tasks, variant.conditions);
  const overheads = conditionOverheads(metrics, tasks, variant.conditions);
  const metricLabel = METRICS.find(([v]) => v === metric)?.[1] ?? metric;
  const overheadLabel = OVERHEADS.find(([v]) => v === overhead)?.[1] ?? overhead;

  // The KPI strip leads §1 (the at-a-glance read for the current scope); the
  // overhead panel only makes sense against the single_agent baseline and with a
  // second feature to compare, and never draws the baseline's own redundant 1.0× bar.
  const k = computeKpis(scopedRuns);
  const kfmt = (v: number | null, d = 2) => (v == null ? '—' : v.toFixed(d));
  const kpis = [
    { label: 'Runs', value: String(k.runs), sub: 'in scope' },
    { label: 'Mean requests', value: kfmt(k.meanRequests, 1), sub: 'per run' },
    {
      label: 'Mean total cost',
      value: k.meanCost == null ? '—' : `$${k.meanCost.toFixed(3)}`,
      sub: 'per run',
    },
    { label: 'Mean quality', value: kfmt(k.meanQuality, 2), sub: '0–1 score' },
    {
      label: 'Mean cache hit',
      value: k.meanCacheHit == null ? '—' : `${(k.meanCacheHit * 100).toFixed(0)}%`,
      sub: 'of input tokens',
    },
  ];
  const showOverhead = hasBaseline && conds.length > 1;
  const overheadConds = conds.filter((c) => c !== 'single_agent');

  return (
    <div className="view">
      <div className="kpi-row">
        {kpis.map((c) => (
          <Card key={c.label} elevation={Elevation.ZERO} className="kpi-card">
            <div className="kpi-label">{c.label}</div>
            <div className="kpi-value">{c.value}</div>
            <div className="kpi-sub">{c.sub}</div>
          </Card>
        ))}
      </div>
      <div className="view-grid">
        <Card elevation={Elevation.ZERO} className="panel-card">
          <div className="panel-head">
            <h2 className="panel-title">Condition comparison</h2>
            <HTMLSelect
              value={metric}
              onChange={(e) => setMetric(e.currentTarget.value)}
              aria-label="metric"
            >
              {METRICS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </HTMLSelect>
          </div>
          <p className="panel-sub">
            Mean of the selected metric for each feature, one bar series per task.
          </p>
          <EChart
            className="chart"
            themeMode={mode}
            option={conditionOption(metrics, conds, tasks, metric, metricLabel)}
          />
        </Card>
        {showOverhead && (
          <Card elevation={Elevation.ZERO} className="panel-card">
            <div className="panel-head">
              <h2 className="panel-title">Overhead vs single agent</h2>
              <HTMLSelect
                value={overhead}
                onChange={(e) => setOverhead(e.currentTarget.value)}
                aria-label="resource"
              >
                {OVERHEADS.map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </HTMLSelect>
            </div>
            <p className="panel-sub">
              Each feature's resource use as a multiple of the single-agent baseline (the 1× line).
            </p>
            <EChart
              className="chart"
              themeMode={mode}
              option={overheadOption(overheads, overheadConds, tasks, overhead, overheadLabel)}
            />
          </Card>
        )}
        <Card elevation={Elevation.ZERO} className="panel-card">
          <h2 className="panel-title">Quality vs cost map</h2>
          <p className="panel-sub">
            Each point is one feature's mean on the first task in scope; bubble size is request
            count. Up = higher quality, left = cheaper — the top-left is the sweet spot.
          </p>
          <EChart
            className="chart"
            themeMode={mode}
            option={efficiencyOption(metrics, conds, tasks[0] ?? '')}
          />
        </Card>
      </div>
    </div>
  );
}
