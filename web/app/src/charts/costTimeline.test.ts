import { describe, expect, it } from 'vitest';
import type { Turn } from '../types';
import { orderedRequests } from './ordered';
import { AGENT_TYPE_ORDER } from './agentSymbols';
import { costTimelineOption } from './costTimeline';

const rows = [
  {
    request_index: 0,
    request_type: 'main-agent',
    input_tokens: 10,
    cache_read: 5,
    cache_creation_5m: 2,
    cache_creation_1h: 1,
    output_tokens: 3,
    ttft_s: 0.5,
    total_s: 1,
  },
  {
    request_index: 1,
    request_type: 'main-agent',
    input_tokens: 0,
    cache_read: 20,
    cache_creation_5m: 0,
    cache_creation_1h: 0,
    output_tokens: 4,
    ttft_s: 0.4,
    total_s: 2,
  },
] as unknown as Turn[];
const o = orderedRequests(
  new Map(rows.map((_, i) => [i, rows[i].request_type as string])),
  rows.map((_, i) => i),
  'all',
  'none',
  AGENT_TYPE_ORDER,
);

describe('costTimelineOption', () => {
  it('has 5 stacked bars + 2 latency lines, dual y-axis', () => {
    const opt = costTimelineOption(rows, o, 30) as any;
    const bars = opt.series.filter((s: any) => s.type === 'bar');
    const lines = opt.series.filter((s: any) => s.type === 'line');
    expect(bars).toHaveLength(5);
    expect(lines).toHaveLength(2);
    expect(Array.isArray(opt.yAxis) && opt.yAxis).toHaveLength(2);
    expect(lines.every((l: any) => l.yAxisIndex === 1)).toBe(true);
    const input = bars.find((b: any) => b.name === 'input');
    expect(input.data).toEqual([10, 0]); // in o.indexes (raw) order
    expect(input.itemStyle.color).toBe('#3b5bdb');
  });
});
