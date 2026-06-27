import { useMemo } from 'react';
import { Card, Elevation } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { inVariantTurns, scopeTurns } from '../data/filters';
import { EChart } from '../components/EChart';
import { cacheByAgent } from '../charts/cacheTimeline';
import { cacheOption, latencyOption } from '../charts/section2Options';

export function Section2View() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  const sel = effective('s2');
  const selTask = effectiveTask('s2');
  const turns = useMemo(
    () => (variant ? scopeTurns(inVariantTurns(data?.turns ?? [], variant), selTask, sel) : []),
    [data, variant, selTask, sel],
  );
  if (!variant) return null;
  const conds = sel.condition.length ? sel.condition : variant.conditions;
  const tasks = selTask.length ? selTask : variant.tasks;
  const singleAgent = sel.agent.length === 1 ? sel.agent[0] : 'all';
  return (
    <div className="view view-stack">
      <Card elevation={Elevation.ZERO} className="panel-card">
        <h2 className="panel-title">Prefix Cache Hit Rate (accumulated)</h2>
        {tasks.map((task) => (
          <div key={task}>
            <h3 className="cache-sub">{task}</h3>
            <EChart className="chart short" themeMode={mode} option={cacheOption(cacheByAgent(turns.filter((t) => t.task === task)), conds, singleAgent)} />
          </div>
        ))}
      </Card>
      <Card elevation={Elevation.ZERO} className="panel-card">
        <h2 className="panel-title">Prefix cache hit rate vs context length</h2>
        <EChart className="chart" themeMode={mode} option={latencyOption(turns, conds)} />
      </Card>
    </div>
  );
}
