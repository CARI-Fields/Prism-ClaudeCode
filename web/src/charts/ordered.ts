import { catAxis } from './echartsTheme';

export interface Ordered {
  indexes: number[];
  bands: { type: string; startPos: number; endPos: number }[];
  ordinal: number[];
  annotate: boolean;
  grouped: boolean;
  xLabels: string[];
  showLabel: boolean[];
  groupAxisLabels: string[];
}

export function orderedRequests(
  typeByIndex: Map<number, string>, rawIndexes: number[], at: string, groupMode: string, typeOrder: string[],
): Ordered {
  const indexes = rawIndexes.slice();
  const grouped = groupMode === 'agent' && at === 'all';
  const rank = (t: string | undefined) => { const k = typeOrder.indexOf(t ?? ''); return k < 0 ? 999 : k; };
  if (grouped) indexes.sort((a, b) => rank(typeByIndex.get(a)) - rank(typeByIndex.get(b)) || a - b);

  const bands: Ordered['bands'] = [];
  indexes.forEach((i, pos) => {
    const t = typeByIndex.get(i) ?? 'main-agent';
    const last = bands[bands.length - 1];
    if (last && last.type === t) last.endPos = pos;
    else bands.push({ type: t, startPos: pos, endPos: pos });
  });

  const ordinal = new Array<number>(indexes.length);
  for (const g of bands) { let n = 1; for (let p = g.startPos; p <= g.endPos; p++) ordinal[p] = n++; }

  const annotate = grouped || at !== 'all';
  const xLabels = new Array<string>(indexes.length).fill('');
  const showLabel = new Array<boolean>(indexes.length).fill(false);
  if (annotate) {
    for (const g of bands) {
      const mid = Math.floor((g.startPos + g.endPos) / 2);
      xLabels[mid] = `${g.endPos - g.startPos + 1}`;
      showLabel[mid] = true;
    }
  } else {
    indexes.forEach((i, pos) => { xLabels[pos] = `#${i + 1}\n${typeByIndex.get(i) ?? 'main-agent'}`; });
    if (indexes.length) { showLabel[0] = true; showLabel[indexes.length - 1] = true; }
  }
  const groupAxisLabels = new Array<string>(indexes.length).fill('');
  if (annotate) for (const g of bands) groupAxisLabels[Math.floor((g.startPos + g.endPos) / 2)] = g.type;

  return { indexes, bands, ordinal, annotate, grouped, xLabels, showLabel, groupAxisLabels };
}

export function groupedXAxis(o: Ordered): Record<string, unknown> {
  return catAxis({
    data: o.xLabels,
    axisLabel: {
      interval: (idx: number) => o.showLabel[idx],
      fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      fontSize: 10,
      color: '#5c6675',
      formatter: (v: string) => v,
    },
  });
}
