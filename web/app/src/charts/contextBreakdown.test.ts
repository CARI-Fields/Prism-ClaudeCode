import { describe, expect, it } from 'vitest';
import type { Component, Turn } from '../types';
import { breakdownData, COMPOSE_MODES, hitRateData } from './contextBreakdown';
import { orderedRequests } from './ordered';
import { AGENT_TYPE_ORDER } from './agentSymbols';

const rows = [
  {
    request_index: 0,
    request_type: 'main-agent',
    input_tokens: 10,
    cache_read: 30,
    cache_creation_5m: 5,
    cache_creation_1h: 5,
  },
  {
    request_index: 1,
    request_type: 'main-agent',
    input_tokens: 0,
    cache_read: 50,
    cache_creation_5m: 0,
    cache_creation_1h: 0,
  },
] as unknown as Turn[];
const comps = [
  { run_id: 'a', request_index: 0, component: 'base system prompt', est_tokens: 100 },
  { run_id: 'a', request_index: 0, component: 'user input', est_tokens: 20 },
  { run_id: 'a', request_index: 1, component: 'builtin tool definitions', est_tokens: 40 },
] as unknown as Component[];

describe('breakdownData', () => {
  it('context mode buckets components by /context map, keyed by position', () => {
    const bd = breakdownData(COMPOSE_MODES.context, rows, comps);
    expect(bd.byKey.get('0:System prompt')).toBe(100); // base system prompt
    expect(bd.byKey.get('0:Messages')).toBe(20); // user input -> Messages
    expect(bd.byKey.get('1:System tools')).toBe(40); // builtin tool definitions
    expect(bd.buckets).toEqual(['System prompt', 'System tools', 'Messages']); // present, in order
  });
  it('token mode reads turns: input/cache read/cache write', () => {
    const bd = breakdownData(COMPOSE_MODES.token, rows, []);
    expect(bd.byKey.get('0:input')).toBe(10);
    expect(bd.byKey.get('0:cache read')).toBe(30);
    expect(bd.byKey.get('0:cache write')).toBe(10); // 5m + 1h
  });
});

describe('hitRateData', () => {
  it('computes 100*cache_read/promptTokens per position', () => {
    const o = orderedRequests(
      new Map(rows.map((_, i) => [i, 'main-agent'])),
      rows.map((_, i) => i),
      'all',
      'none',
      AGENT_TYPE_ORDER,
    );
    const h = hitRateData(rows, o);
    expect(h[0]).toBeCloseTo(60); // 100*30/(10+30+5+5)=60
    expect(h[1]).toBeCloseTo(100); // 100*50/50
  });
});
