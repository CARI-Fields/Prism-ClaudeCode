import type { GlobalFilter, ThemeMode, ViewKey } from '../types';

export interface UrlState {
  report: string | null;
  theme: ThemeMode | null;
  view: ViewKey | null;
  filter: GlobalFilter;
}

const DIMS = ['task', 'condition', 'rep', 'agent'] as const;

export function parseHash(hash: string): UrlState {
  const h = hash.replace(/^#/, '');
  const map = new Map<string, string>();
  for (const seg of h.split('&')) {
    if (!seg) continue;
    const eq = seg.indexOf('=');
    if (eq !== -1) map.set(seg.slice(0, eq), seg.slice(eq + 1));
  }
  const list = (k: string): string[] => { const v = map.get(k); return v ? v.split(',').filter(Boolean) : []; };
  const theme = map.get('theme'); const view = map.get('view');
  return {
    report: map.get('report') ?? null,
    theme: theme === 'light' || theme === 'dark' ? theme : null,
    view: ['overview', 's1', 's2', 's3'].includes(view ?? '') ? (view as ViewKey) : null,
    filter: { task: list('task'), condition: list('condition'), rep: list('rep'), agent: list('agent') },
  };
}

export function toHash(u: UrlState): string {
  const parts: string[] = [];
  if (u.report) parts.push(`report=${u.report}`);
  if (u.theme) parts.push(`theme=${u.theme}`);
  if (u.view) parts.push(`view=${u.view}`);
  for (const d of DIMS) if (u.filter[d as keyof GlobalFilter].length) parts.push(`${d}=${u.filter[d as keyof GlobalFilter].join(',')}`);
  return parts.length ? `#${parts.join('&')}` : '';
}
