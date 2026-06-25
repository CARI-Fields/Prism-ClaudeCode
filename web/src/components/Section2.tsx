import type { AppState, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';

interface Props {
  variant: Variant; state: AppState; reps: string[]; agentTypes: string[];
  onToggle: (dim: 'condition' | 'rep' | 'agent', token: string) => void;
  onClear: (dim: 'condition' | 'rep' | 'agent') => void;
}
export function Section2({ variant, state, reps, agentTypes, onToggle, onClear }: Props) {
  return (
    <section className="band band-dist">
      <div className="band-head">
        <div className="band-label"><span className="band-no">§2</span>Across all runs</div>
        <div className="band-scope">Each line or dot is a single run · scoped by this section</div>
      </div>
      <div className="fstrip">
        <FilterChunk tag="Feature" items={variant.conditions} active={state.s2.condition}
          onToggle={(t) => onToggle('condition', t)} onClear={() => onClear('condition')} dotFor={conditionColor} />
        <FilterChunk tag="Rollout" items={reps} active={state.s2.rep}
          onToggle={(t) => onToggle('rep', t)} onClear={() => onClear('rep')} />
        <FilterChunk tag="Agent" items={agentTypes} active={state.s2.agent}
          onToggle={(t) => onToggle('agent', t)} onClear={() => onClear('agent')} />
      </div>
      <div className="stack">
        <article className="panel">
          <div className="panel-head"><h2>Prefix Cache Hit Rate (accumulated)</h2></div>
          <div id="cache-panels" />
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Prefix cache hit rate vs context length</h2></div>
          <div id="latency-chart" className="chart" />
        </article>
      </div>
    </section>
  );
}
