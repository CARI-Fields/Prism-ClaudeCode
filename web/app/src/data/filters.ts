import type { Run, SectionSel, Turn, Variant } from '../types';

const inSel = (values: string[], v: string): boolean => values.length === 0 || values.includes(v);

// Restrict rows to the report variant currently in view. The two variants share
// a condition ("dynamic_workflow"), so filtering by user selection alone leaks
// the other variant's runs into a view (e.g. multi-agent runs in long-horizon).
type VariantScope = Pick<Variant, 'tasks' | 'conditions'>;
export function inVariantRuns(runs: Run[], v: VariantScope): Run[] {
  return runs.filter((r) => v.tasks.includes(r.task) && v.conditions.includes(r.condition));
}
export function inVariantTurns(turns: Turn[], v: VariantScope): Turn[] {
  return turns.filter((t) => v.tasks.includes(t.task) && v.conditions.includes(t.condition));
}

export function scopeRuns(runs: Run[], task: string[], sel: SectionSel): Run[] {
  return runs.filter(
    (r) => inSel(task, r.task) && inSel(sel.condition, r.condition) && inSel(sel.rep, `r${r.rep}`),
  );
}
export function scopeTurns(turns: Turn[], task: string[], sel: SectionSel): Turn[] {
  return turns.filter(
    (t) =>
      inSel(task, t.task) &&
      inSel(sel.condition, t.condition) &&
      inSel(sel.rep, `r${t.rep}`) &&
      (sel.agent.length === 0 || (t.request_type != null && sel.agent.includes(t.request_type))),
  );
}
export function presentAgentTypes(turns: Turn[]): string[] {
  const set = new Set<string>();
  for (const t of turns) if (t.request_type != null) set.add(t.request_type);
  return Array.from(set).sort();
}
