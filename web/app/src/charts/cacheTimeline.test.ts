import { describe, expect, it } from 'vitest';
import type { Turn } from '../types';
import { cacheByAgent, promptTokens } from './cacheTimeline';

const turns = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent', request_index: 0, input_tokens: 100, cache_read: 0, cache_creation_5m: 100, cache_creation_1h: 0 },
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent', request_index: 1, input_tokens: 0, cache_read: 200, cache_creation_5m: 0, cache_creation_1h: 0 },
] as unknown as Turn[];

describe('cacheByAgent', () => {
  it('accumulates per stream with 1-based ordinal and hit rate', () => {
    const rows = cacheByAgent(turns);
    expect(rows.map((r) => r.ordinal)).toEqual([1, 2]);
    // turn 0: read 0 / (0+100+100) = 0
    expect(rows[0].accumulated_cache_hit_rate).toBeCloseTo(0);
    // turn 1: cum read 200 / (200 + 100 + 100) = 0.5
    expect(rows[1].accumulated_cache_hit_rate).toBeCloseTo(0.5);
    expect(rows[1].cum_cache_read).toBe(200);
    expect(rows[1].cum_context_tokens).toBe(400);
  });
  it('separates streams by (run, request_type)', () => {
    const mixed = [...turns, { ...turns[0], request_type: 'task-subagent', request_index: 0 }] as Turn[];
    const rows = cacheByAgent(mixed);
    expect(new Set(rows.map((r) => r.request_type))).toEqual(new Set(['main-agent', 'task-subagent']));
  });
});

describe('promptTokens', () => {
  it('sums input + cache_read + both cache_creation buckets', () => {
    expect(promptTokens({ input_tokens: 10, cache_read: 20, cache_creation_5m: 5, cache_creation_1h: 3 } as unknown as Turn)).toBe(38);
  });
});
