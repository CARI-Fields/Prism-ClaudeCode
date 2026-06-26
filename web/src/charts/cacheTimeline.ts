import type { Turn } from '../types';

export interface CacheRow {
  run_id: string; task: string; condition: string; rep: number;
  request_type: string; request_index: number; ordinal: number;
  accumulated_cache_hit_rate: number | null;
  cum_cache_read: number; cum_context_tokens: number;
}
const n = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

export function promptTokens(t: Turn): number {
  return n(t.input_tokens) + n(t.cache_read) + n(t.cache_creation_5m) + n(t.cache_creation_1h);
}

export function cacheByAgent(turns: Turn[]): CacheRow[] {
  const groups = new Map<string, Turn[]>();
  for (const t of turns) {
    if (!t.run_id) continue;
    const type = String(t.request_type ?? 'main-agent');
    const key = `${t.run_id} ${type}`;
    let arr = groups.get(key);
    if (!arr) { arr = []; groups.set(key, arr); }
    arr.push(t);
  }
  const rows: CacheRow[] = [];
  for (const group of groups.values()) {
    let cumRead = 0, cumWrite = 0, cumInput = 0, ordinal = 0;
    const sorted = group.slice().sort((a, b) => n(a.request_index) - n(b.request_index));
    for (const t of sorted) {
      cumRead += n(t.cache_read);
      cumWrite += n(t.cache_creation_5m) + n(t.cache_creation_1h);
      cumInput += n(t.input_tokens);
      const denom = cumRead + cumWrite + cumInput;
      ordinal += 1;
      rows.push({
        run_id: t.run_id, task: t.task, condition: t.condition, rep: t.rep,
        request_type: String(t.request_type ?? 'main-agent'),
        request_index: t.request_index, ordinal,
        accumulated_cache_hit_rate: denom ? cumRead / denom : null,
        cum_cache_read: cumRead, cum_context_tokens: denom,
      });
    }
  }
  return rows;
}
