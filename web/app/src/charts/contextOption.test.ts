import { describe, expect, it } from 'vitest';
import type { Turn } from '../types';
import { breakdownData, COMPOSE_MODES, hitRateData } from './contextBreakdown';
import { orderedRequests } from './ordered';
import { AGENT_TYPE_ORDER } from './agentSymbols';
import { contextOption } from './contextOption';

const rows = [
  {
    request_index: 0,
    request_type: 'main-agent',
    input_tokens: 10,
    cache_read: 30,
    cache_creation_5m: 0,
    cache_creation_1h: 0,
  },
] as unknown as Turn[];
const o = orderedRequests(new Map([[0, 'main-agent']]), [0], 'all', 'none', AGENT_TYPE_ORDER);

describe('contextOption', () => {
  it('stacked bars per bucket; adds hit overlay + inverted axis when showHit', () => {
    const bd = breakdownData(COMPOSE_MODES.token, rows, []);
    const noHit = contextOption(bd, o, false, []) as any;
    expect(noHit.series.every((s: any) => s.type === 'bar' && s.stack === 'context')).toBe(true);
    expect(Array.isArray(noHit.yAxis) ? noHit.yAxis.length : 1).toBe(1);

    const withHit = contextOption(bd, o, true, hitRateData(rows, o)) as any;
    const hit = withHit.series.find((s: any) => s.name === 'cache hit');
    expect(hit.type).toBe('line');
    expect(hit.yAxisIndex).toBe(1);
    expect(withHit.yAxis[1].inverse).toBe(true);
  });

  it('propagates bar density (width + category gap) to every bar series', () => {
    const bd = breakdownData(COMPOSE_MODES.token, rows, []);
    const opt = contextOption(bd, o, false, [], 42, '12%') as any;
    const bars = opt.series.filter((s: any) => s.type === 'bar');
    expect(bars.length).toBeGreaterThan(0);
    expect(bars.every((s: any) => s.barMaxWidth === 42 && s.barCategoryGap === '12%')).toBe(true);
  });

  it('stacks the context head on top: head bucket is the first bar series (inverse axis)', () => {
    const bd = breakdownData(COMPOSE_MODES.token, rows, []);
    const bars = (contextOption(bd, o, false, []) as any).series.filter(
      (s: any) => s.type === 'bar',
    );
    // bd.buckets is head→tail; the token axis is inverse, so ECharts draws the
    // first series at the TOP — head bucket first, tail bucket last.
    expect(bars[0].name).toBe(bd.buckets[0]);
    expect(bars[bars.length - 1].name).toBe(bd.buckets[bd.buckets.length - 1]);
  });
});
