import type { Run } from '../types';
import { computeKpis } from '../data/kpis';

function fmt(v: number | null, digits = 2, unit = ''): string {
  if (v == null) return '—';
  return `${v.toFixed(digits)}${unit}`;
}
export function KpiBand({ runs }: { runs: Run[] }) {
  const k = computeKpis(runs);
  const cards: { label: string; value: string }[] = [
    { label: 'Runs', value: String(k.runs) },
    { label: 'Mean requests', value: fmt(k.meanRequests, 1) },
    { label: 'Mean total cost', value: k.meanCost == null ? '—' : `$${k.meanCost.toFixed(3)}` },
    { label: 'Mean quality', value: fmt(k.meanQuality, 2) },
    { label: 'Mean cache hit', value: k.meanCacheHit == null ? '—' : `${(k.meanCacheHit * 100).toFixed(0)}%` },
  ];
  return (
    <section className="band band-agg">
      <div className="scope-tag">Aggregate · current selection</div>
      <div className="kpis">
        {cards.map((c) => (
          <div className="kpi" key={c.label}>
            <div className="label">{c.label}</div>
            <div className="value">{c.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
