function finite(v: number | null | undefined): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}
export function fmt(value: number | null | undefined, digits = 1): string {
  if (!finite(value)) return 'n/a';
  const a = Math.abs(value);
  if (a >= 1e6) return `${(value / 1e6).toFixed(digits)}M`;
  if (a >= 1e3) return `${(value / 1e3).toFixed(digits)}k`;
  return value.toFixed(digits);
}
export function fmtUsd(value: number | null | undefined): string {
  if (!finite(value)) return 'n/a';
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}
export function fmtAxis(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(0)}k`;
  return String(v);
}
export function pct(value: number | null | undefined, digits = 0): string {
  if (!finite(value)) return 'n/a';
  return `${(value * 100).toFixed(digits)}%`;
}
export function fmtMetric(value: number | null | undefined, metric: string): string {
  if (metric.includes('cost_usd')) return fmtUsd(value);
  if (metric.includes('ratio') || metric.includes('rate')) return pct(value);
  return fmt(value);
}
