import { describe, expect, it } from 'vitest';
import type { Turn } from '../types';
import { cacheByAgent } from './cacheTimeline';
import { cacheOption, latencyOption } from './section2Options';

const turns = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent', request_index: 0, input_tokens: 0, cache_read: 100, cache_creation_5m: 0, cache_creation_1h: 0, total_s: 1, ttft_s: 0.5 },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2, request_type: 'task-subagent', request_index: 0, input_tokens: 0, cache_read: 50, cache_creation_5m: 50, cache_creation_1h: 0, total_s: 2, ttft_s: 0.4 },
] as unknown as Turn[];
const conds = ['single_agent', 'subagents'];

describe('section2 option builders', () => {
  it('cacheOption: one line series per run\xd7agent, name=condition, rep line-style', () => {
    const opt = cacheOption(cacheByAgent(turns), conds, 'all') as any;
    expect(opt.series).toHaveLength(2);
    expect(opt.series.every((s: any) => s.type === 'line')).toBe(true);
    const sa = opt.series.find((s: any) => s.name === 'single_agent');
    expect(sa.lineStyle.type).toBe('solid'); // rep 1
    expect(sa.symbol).toBe('circle'); // main-agent
    expect(sa.data[0].value[1]).toBeCloseTo(100); // hit rate % = 100*100/100
  });
  it('latencyOption: scatter series per condition; y = 100*cache_read/prompt_tokens', () => {
    const opt = latencyOption(turns, conds) as any;
    const sub = opt.series.find((s: any) => s.name === 'subagents');
    expect(sub.type).toBe('scatter');
    // prompt_tokens = 0+50+50+0 = 100; hit = 100*50/100 = 50
    expect(sub.data[0].value[0]).toBe(100);
    expect(sub.data[0].value[1]).toBeCloseTo(50);
  });
  it('latencyOption: skips zero-context turns', () => {
    const z = [{ ...turns[0], cache_read: 0, input_tokens: 0, cache_creation_5m: 0, cache_creation_1h: 0 }] as unknown as Turn[];
    const opt = latencyOption(z, ['single_agent']) as any;
    expect(opt.series[0].data).toHaveLength(0);
  });
});
