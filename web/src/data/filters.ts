import type { Run, SectionSel, Turn } from '../types';

const inSel = (values: string[], v: string): boolean => values.length === 0 || values.includes(v);

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
