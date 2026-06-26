import type { Run } from '../types';

const CODE = { missing: 0, failed: 1, success: 2, skipped: 3 } as const;
type Status = keyof typeof CODE;

export interface MatrixCell {
  task: string; condition: string; rep: number; row: string;
  status: Status; status_code: (typeof CODE)[Status];
  run_id?: string; num_requests?: number | null; total_cost_usd?: number | null;
  quality_score?: number | null; completion_time_s?: number | null;
}

export function matrixData(runs: Run[], tasks: string[], reps: number[], conditions: string[]) {
  const rows: string[] = [];
  for (const task of tasks) for (const rep of reps) rows.push(`${task} r${rep}`);
  const cols = [...conditions];
  const cells: MatrixCell[] = [];
  for (const task of tasks) for (const rep of reps) for (const condition of conditions) {
    const match = runs.filter((r) => r.task === task && r.condition === condition && r.rep === rep);
    const row = `${task} r${rep}`;
    if (match.length === 0) {
      cells.push({ task, condition, rep, row, status: 'missing', status_code: CODE.missing });
      continue;
    }
    const sorted = match.slice().sort((a, b) => String(a.run_id).localeCompare(String(b.run_id)));
    const latest = sorted[sorted.length - 1]!;
    const skipped = String((latest as { status?: unknown }).status ?? '').toLowerCase() === 'skipped';
    const status: Status = skipped ? 'skipped' : latest.success ? 'success' : 'failed';
    cells.push({
      task, condition, rep, row, status, status_code: CODE[status],
      run_id: latest.run_id,
      num_requests: (latest.num_requests as number | null) ?? null,
      total_cost_usd: (latest.total_cost_usd as number | null) ?? null,
      quality_score: (latest.quality_score as number | null) ?? null,
      completion_time_s: (latest.completion_time_s as number | null) ?? null,
    });
  }
  return { rows, cols, cells };
}
