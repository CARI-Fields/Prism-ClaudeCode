export interface UrlState { report: string | null; task: string[]; }

export function parseHash(hash: string): UrlState {
  const h = hash.replace(/^#/, '');
  const get = (key: string): string | null => {
    for (const seg of h.split('&')) {
      if (!seg) continue;
      const eq = seg.indexOf('=');
      if (eq !== -1 && seg.slice(0, eq) === key) return seg.slice(eq + 1);
    }
    return null;
  };
  const task = get('task');
  return { report: get('report'), task: task ? task.split(',').filter(Boolean) : [] };
}

export function toHash(u: UrlState): string {
  const parts: string[] = [];
  if (u.report) parts.push(`report=${u.report}`);
  if (u.task.length) parts.push(`task=${u.task.join(',')}`);
  return parts.length ? `#${parts.join('&')}` : '';
}
