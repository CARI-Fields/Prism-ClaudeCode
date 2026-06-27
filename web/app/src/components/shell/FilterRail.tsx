import { Button } from '@blueprintjs/core';
import { useMemo } from 'react';
import { RailFilterGroup } from './RailFilterGroup';
import { useFilter, useReport } from '../../state/AppStateProvider';
import { useData } from '../../data/DataContext';
import { conditionColor } from '../../theme';
import { presentAgentTypes } from '../../data/filters';

export function FilterRail() {
  const { report } = useReport();
  const { data } = useData();
  const { filter, toggle, clear } = useFilter();
  const variant = data?.manifest?.variants?.find((v) => v.key === report) ?? data?.manifest?.variants?.[0];
  const variantRuns = useMemo(() => (data?.runs ?? []).filter((r) => variant && variant.tasks.includes(r.task) && variant.conditions.includes(r.condition)), [data, variant]);
  const reps = useMemo(() => Array.from(new Set(variantRuns.map((r) => `r${r.rep}`))).sort(), [variantRuns]);
  const variantTurns = useMemo(() => (data?.turns ?? []).filter((t) => variant && variant.tasks.includes(t.task) && variant.conditions.includes(t.condition)), [data, variant]);
  const agents = useMemo(() => presentAgentTypes(variantTurns), [variantTurns]);
  if (!variant) return null;
  const anyActive = filter.task.length || filter.condition.length || filter.rep.length || filter.agent.length;
  return (
    <div className="rail">
      <div className="rail-top"><span className="rail-title">Filters</span>
        {anyActive ? <Button minimal small text="Reset all" onClick={() => { clear('task'); clear('condition'); clear('rep'); clear('agent'); }} /> : null}</div>
      <RailFilterGroup label="Task" items={variant.tasks} active={filter.task} onToggle={(t) => toggle('task', t)} onClear={() => clear('task')} />
      <RailFilterGroup label="Feature" items={variant.conditions} active={filter.condition} dotFor={conditionColor} onToggle={(t) => toggle('condition', t)} onClear={() => clear('condition')} />
      <RailFilterGroup label="Rollout" items={reps} active={filter.rep} onToggle={(t) => toggle('rep', t)} onClear={() => clear('rep')} />
      <RailFilterGroup label="Agent" items={agents} active={filter.agent} onToggle={(t) => toggle('agent', t)} onClear={() => clear('agent')} />
    </div>
  );
}
