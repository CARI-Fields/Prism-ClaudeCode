import { Fragment } from 'react';
import { useData } from '../../data/DataContext';
import { useFilter, useReport, useView } from '../../state/AppStateProvider';
import { inVariantRuns, scopeRuns } from '../../data/filters';

// One mono line above §1–§3 summarizing the slice of data the canvas is showing
// (runs in scope · features · tasks · rollouts · agent), with a reset affordance
// when any filter is active. The Overview is a fixed orientation summary that the
// rail does not scope, so this is hidden there.
export function ScopeNote() {
  const { view } = useView();
  const { report } = useReport();
  const { data } = useData();
  const { filter, effective, effectiveTask, clear } = useFilter();
  if (view === 'overview' || !data) return null;
  const variant = data.manifest.variants.find((v) => v.key === report) ?? data.manifest.variants[0];
  if (!variant) return null;

  const sel = effective(view);
  const selTask = effectiveTask(view);
  const scoped = scopeRuns(inVariantRuns(data.runs, variant), selTask, sel);
  const conds = sel.condition.length ? sel.condition : variant.conditions;
  const tasks = selTask.length ? selTask : variant.tasks;
  const repTxt = sel.rep.length ? sel.rep.slice().sort().join(', ') : 'all rollouts';

  const parts = [
    `${scoped.length} runs`,
    `${conds.length} ${conds.length === 1 ? 'feature' : 'features'}`,
    `${tasks.length} ${tasks.length === 1 ? 'task' : 'tasks'}`,
    repTxt,
  ];
  if (sel.agent.length === 1) parts.push(`${sel.agent[0]} only`);

  const anyActive = Boolean(filter.task.length || filter.condition.length || filter.rep.length || filter.agent.length);
  const resetAll = () => { clear('task'); clear('condition'); clear('rep'); clear('agent'); };

  return (
    <div className="scope-note">
      {parts.map((p, i) => (
        <Fragment key={i}>
          <span className={i === 0 ? 'scope-strong' : undefined}>{p}</span>
          {i < parts.length - 1 && <span className="scope-sep">·</span>}
        </Fragment>
      ))}
      {anyActive && (
        <>
          <span className="scope-sep">·</span>
          <span
            className="scope-reset"
            role="button"
            tabIndex={0}
            onClick={resetAll}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); resetAll(); } }}
          >
            reset
          </span>
        </>
      )}
    </div>
  );
}
