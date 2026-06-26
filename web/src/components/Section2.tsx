import type { AppState, Turn, Variant } from '../types';
import { FilterChunk } from './FilterChunk';
import { conditionColor } from '../theme';
import { EChart } from './EChart';
import { cacheByAgent } from '../charts/cacheTimeline';
import { cacheOption, latencyOption } from '../charts/section2Options';

interface Props {
  variant: Variant; state: AppState; turns: Turn[]; reps: string[]; agentTypes: string[];
  onToggle: (dim: 'condition' | 'rep' | 'agent', token: string) => void;
  onClear: (dim: 'condition' | 'rep' | 'agent') => void;
}
export function Section2({ variant, state, turns, reps, agentTypes, onToggle, onClear }: Props) {
  const conds = state.s2.condition.length ? state.s2.condition : variant.conditions;
  const tasks = state.task.length ? state.task : variant.tasks;
  const singleAgent = state.s2.agent.length === 1 ? state.s2.agent[0] : 'all';
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
          <div id="cache-panels">
            {tasks.map((task) => (
              <div key={task}>
                <h3 className="cache-sub">{task}</h3>
                <EChart className="chart short" option={cacheOption(cacheByAgent(turns.filter((t) => t.task === task)), conds, singleAgent)} />
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Prefix cache hit rate vs context length</h2></div>
          <EChart className="chart" option={latencyOption(turns, conds)} />
        </article>
      </div>
    </section>
  );
}
