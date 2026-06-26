import { describe, expect, it } from 'vitest';
import { fmt, fmtAxis, fmtMetric, fmtUsd, pct } from './format';

describe('format', () => {
  it('fmt: n/a, k, M, and digits', () => {
    expect(fmt(null)).toBe('n/a');
    expect(fmt(NaN)).toBe('n/a');
    expect(fmt(1500)).toBe('1.5k');
    expect(fmt(2_300_000)).toBe('2.3M');
    expect(fmt(3.14159, 2)).toBe('3.14');
  });
  it('fmtUsd: variable precision', () => {
    expect(fmtUsd(0.005)).toBe('$0.0050');
    expect(fmtUsd(0.5)).toBe('$0.500');
    expect(fmtUsd(12.3)).toBe('$12.30');
    expect(fmtUsd(null)).toBe('n/a');
  });
  it('pct and fmtAxis', () => {
    expect(pct(0.873)).toBe('87%');
    expect(pct(0.873, 1)).toBe('87.3%');
    expect(fmtAxis(2400)).toBe('2k'); // 2.4 → "2", unambiguous
    expect(fmtAxis(42)).toBe('42');
  });
  it('fmtMetric routes by metric name', () => {
    expect(fmtMetric(0.5, 'mean_total_cost_usd')).toBe('$0.500');
    expect(fmtMetric(0.81, 'mean_cache_hit_ratio')).toBe('81%');
    expect(fmtMetric(0.81, 'success_rate')).toBe('81%');
    expect(fmtMetric(5.2, 'mean_num_requests')).toBe('5.2');
  });
});
