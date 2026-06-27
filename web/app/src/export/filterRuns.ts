import { scopeRuns } from '../data/filters';
import type { Run } from '../types';

export interface RunFilter {
  task: string[];
  condition: string[];
  rep: string[];
  query: string;
}

export function filterRuns(runs: Run[], f: RunFilter): Run[] {
  const scoped = scopeRuns(runs, f.task, { condition: f.condition, rep: f.rep, agent: [] });
  const q = f.query.trim().toLowerCase();
  if (!q) return scoped;
  return scoped.filter((r) =>
    `${r.task} ${r.condition} r${r.rep} ${r.run_id}`.toLowerCase().includes(q),
  );
}
