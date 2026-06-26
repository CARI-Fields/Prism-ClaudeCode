import { useState } from 'react';
import type { AppState, Component, Run, Turn, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';
import { EChart } from './EChart';
import { orderedRequests } from '../charts/ordered';
import { AGENT_TYPE_ORDER } from '../charts/agentSymbols';
import { costTimelineOption } from '../charts/costTimeline';
import { breakdownData, hitRateData, COMPOSE_MODES } from '../charts/contextBreakdown';
import { contextOption } from '../charts/contextOption';
import { ContextTextPanel } from './ContextTextPanel';
import type { CtxSelection } from './ContextTextPanel';

interface Props {
  variant: Variant; state: AppState; runs: Run[]; turns: Turn[]; reps: string[]; agentTypes: string[];
  components: Component[];
  onToggle: (dim: 'condition' | 'rep' | 'agent', token: string) => void;
  onClear: (dim: 'condition' | 'rep' | 'agent') => void;
}
export function Section3({ variant, state, runs, turns, reps, agentTypes, components, onToggle, onClear }: Props) {
  const [compose, setCompose] = useState('context');
  const [group, setGroup] = useState('agent');
  const [hitrate, setHitrate] = useState(true);
  const [density, setDensity] = useState(100);
  const [sel, setSel] = useState<Record<string, CtxSelection | null>>({});

  const singleAgent = state.s3.agent.length === 1 ? state.s3.agent[0] : 'all';
  const mode = COMPOSE_MODES[compose as 'context' | 'source' | 'token'] ?? COMPOSE_MODES.context;
  const showHit = hitrate;

  return (
    <section className="band band-run">
      <div className="band-head">
        <div className="band-label"><span className="band-no">§3</span>Single run drilldown</div>
      </div>
      <div className="fstrip">
        <FilterChunk tag="Feature" items={variant.conditions} active={state.s3.condition}
          onToggle={(t) => onToggle('condition', t)} onClear={() => onClear('condition')} dotFor={conditionColor} />
        <FilterChunk tag="Rollout" items={reps} active={state.s3.rep}
          onToggle={(t) => onToggle('rep', t)} onClear={() => onClear('rep')} />
        <FilterChunk tag="Agent" items={agentTypes} active={state.s3.agent}
          onToggle={(t) => onToggle('agent', t)} onClear={() => onClear('agent')} />
        <div className="control-group">
          <label className="control inline">bar density
            <input type="range" min={0} max={100} value={density} onChange={(e) => setDensity(Number(e.target.value))} />
          </label>
          <label className="control inline">compose by
            <select value={compose} onChange={(e) => setCompose(e.target.value)}>
              <option value="context">/context</option>
              <option value="source">source (detailed)</option>
              <option value="token">token type</option>
            </select>
          </label>
          <label className="control inline">group
            <select value={group} onChange={(e) => setGroup(e.target.value)}>
              <option value="agent">agent type</option>
              <option value="none">none</option>
            </select>
          </label>
          <label className="control inline check">
            <input type="checkbox" checked={hitrate} onChange={(e) => setHitrate(e.target.checked)} />cache hit rate
          </label>
        </div>
      </div>
      <div className="band-scope row">One block per run in this section's Feature × Rollout.</div>
      <div id="drilldown-runs" className="drilldown-runs">
        {runs.map((run) => {
          const rowsForRun = turns.filter((t) => t.run_id === run.run_id)
            .sort((a, b) => a.request_index - b.request_index);
          const typeByIndex = new Map<number, string>(rowsForRun.map((t, i) => [i, t.request_type ?? 'main-agent']));
          const ordered = orderedRequests(typeByIndex, rowsForRun.map((_, i) => i), singleAgent, group, AGENT_TYPE_ORDER);
          const barMaxWidth = Math.max(6, Math.round(6 + 40 * (density / 100)));
          const componentsForRun = components.filter((c) => c.run_id === run.run_id);
          const bd = breakdownData(mode, rowsForRun, componentsForRun);
          const hitData = showHit ? hitRateData(rowsForRun, ordered) : [];
          return (
            <article className="panel drilldown-run" key={run.run_id}>
              <div className="panel-head"><h2>{run.task} / {run.condition} / r{run.rep}</h2><span className="run-tag">{run.run_id}</span></div>
              <h3 className="drill-sub">Per-Run Request Cost Timeline</h3>
              <EChart className="chart" option={costTimelineOption(rowsForRun, ordered, barMaxWidth)} />
              <h3 className="drill-sub">Context Source Breakdown</h3>
              <EChart
                className="chart tall"
                option={contextOption(bd, ordered, showHit, hitData)}
                onClick={mode.clickable ? (p) => {
                  const pos = ordered.indexes[p.dataIndex];
                  const row = rowsForRun[pos];
                  if (!row) return;
                  setSel((s) => ({ ...s, [run.run_id]: { component: p.seriesName, requestIndex: row.request_index, type: String(row.request_type ?? 'main-agent'), tokens: bd.byKey.get(`${pos}:${p.seriesName}`) ?? 0 } }));
                } : undefined}
              />
              <ContextTextPanel runId={run.run_id} selection={sel[run.run_id] ?? null} />
            </article>
          );
        })}
      </div>
    </section>
  );
}
