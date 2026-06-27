import { useMemo } from 'react';
import { Card, Elevation } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { computeKpis } from '../data/kpis';
import { inVariantRuns, scopeRuns } from '../data/filters';
import { conditionColor } from '../theme';
import { EChart } from '../components/EChart';
import { matrixData } from '../charts/matrix';
import { matrixOption } from '../charts/section1Options';

export function OverviewView() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const variant =
    data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  const runs = data?.runs ?? [];
  const sel = effective('overview');
  const selTask = effectiveTask('overview');
  const scoped = useMemo(
    () => (variant ? scopeRuns(inVariantRuns(runs, variant), selTask, sel) : []),
    [runs, variant, selTask, sel],
  );
  if (!variant || !data) return null;

  const k = computeKpis(scoped);
  const fmt = (v: number | null, d = 2, u = '') => (v == null ? '—' : `${v.toFixed(d)}${u}`);
  const cards = [
    { label: 'Runs', value: String(k.runs) },
    { label: 'Mean requests', value: fmt(k.meanRequests, 1) },
    { label: 'Mean total cost', value: k.meanCost == null ? '—' : `$${k.meanCost.toFixed(3)}` },
    { label: 'Mean quality', value: fmt(k.meanQuality, 2) },
    {
      label: 'Mean cache hit',
      value: k.meanCacheHit == null ? '—' : `${(k.meanCacheHit * 100).toFixed(0)}%`,
    },
  ];
  const tasks = selTask.length ? selTask : variant.tasks;
  const reps = Array.from(new Set(scoped.map((r) => r.rep))).sort((a, b) => a - b);
  const matrix = matrixData(scoped, tasks, reps, variant.conditions);

  return (
    <div className="view view-overview">
      <div className="kpi-row">
        {cards.map((c) => (
          <Card key={c.label} elevation={Elevation.ZERO} className="kpi-card">
            <div className="kpi-label">{c.label}</div>
            <div className="kpi-value">{c.value}</div>
          </Card>
        ))}
      </div>
      <div className="overview-grid">
        <Card elevation={Elevation.ZERO} className="panel-card">
          <h2 className="panel-title">
            {data.manifest.task_meta[tasks[0]]?.title ?? variant.title}
          </h2>
          <p className="panel-lede" dangerouslySetInnerHTML={{ __html: variant.lede }} />
          <ul className="strategy-legend">
            {variant.conditions.map((c) => (
              <li key={c}>
                <span className="rail-dot" style={{ background: conditionColor(c) }} />
                <b>{c}</b> — <span>{data.manifest.strategy_desc[c] ?? ''}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card elevation={Elevation.ZERO} className="panel-card">
          <h2 className="panel-title">Experiment matrix</h2>
          <EChart className="chart" themeMode={mode} option={matrixOption(matrix)} />
        </Card>
      </div>
    </div>
  );
}
