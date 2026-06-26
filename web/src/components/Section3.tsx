import { useState } from 'react';
import type { AppState, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';

interface Props {
  variant: Variant; state: AppState; reps: string[]; agentTypes: string[];
  onToggle: (dim: 'condition' | 'rep' | 'agent', token: string) => void;
  onClear: (dim: 'condition' | 'rep' | 'agent') => void;
}
export function Section3({ variant, state, reps, agentTypes, onToggle, onClear }: Props) {
  const [compose, setCompose] = useState('context');
  const [group, setGroup] = useState('agent');
  const [hitrate, setHitrate] = useState(true);
  const [density, setDensity] = useState(100);
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
      <div id="drilldown-runs" className="drilldown-runs" />
    </section>
  );
}
