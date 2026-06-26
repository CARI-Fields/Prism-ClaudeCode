import { fmtAxis } from './format';

export const INK = '#10151d';
export const MUTED = '#5c6675';
export const LINE = '#dde2e9';
export const SANS = "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif";
export const MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";
export const STATUS_COLORS = ['#eef1f5', '#e03131', '#2f9e44', '#adb5bd'];
export const STATUS_GLYPHS = ['', '✗', '✓', '–'];
export const PALETTE = ['#3b5bdb', '#0c8599', '#e8590c', '#7048e8', '#c2255c', '#1098ad', '#f59f00'];

export function baseTextStyle() {
  return { fontFamily: SANS, color: INK };
}

export function axisLabelStyle() {
  return { fontFamily: MONO, fontSize: 11, color: MUTED };
}

export const TOOLTIP = {
  confine: true,
  backgroundColor: '#ffffff',
  borderColor: LINE,
  borderWidth: 1,
  padding: [8, 11] as [number, number],
  textStyle: { fontFamily: MONO, fontSize: 12, color: INK },
  extraCssText: 'box-shadow:0 6px 22px rgba(16,21,29,.12);border-radius:8px;',
};

export function valueAxis(extra: Record<string, unknown> = {}) {
  return {
    type: 'value',
    axisLabel: { ...axisLabelStyle(), formatter: fmtAxis },
    splitLine: { lineStyle: { color: LINE, type: 'dashed' } },
    ...extra,
  };
}

export function catAxis(extra: Record<string, unknown> = {}) {
  return {
    type: 'category',
    axisLabel: axisLabelStyle(),
    axisTick: { show: false },
    axisLine: { lineStyle: { color: LINE } },
    ...extra,
  };
}

export function xName(name: string, gap: number) {
  return {
    name,
    nameLocation: 'middle',
    nameGap: gap,
    nameTextStyle: { fontFamily: MONO, fontSize: 11, color: MUTED },
  };
}

export function yName(name: string, gap: number) {
  return {
    name,
    nameLocation: 'middle',
    nameGap: gap,
    nameRotate: 90,
    nameTextStyle: { fontFamily: MONO, fontSize: 11, color: MUTED },
  };
}

export function rightLegend(items: string[]) {
  return {
    type: 'scroll',
    orient: 'vertical',
    right: 6,
    top: 'middle',
    icon: 'roundRect',
    itemWidth: 14,
    itemHeight: 9,
    itemGap: 9,
    data: items,
    textStyle: { fontFamily: MONO, fontSize: 11, color: INK },
    pageTextStyle: { color: MUTED },
    pageIconColor: MUTED,
  };
}

export function bottomLegend(items: string[]) {
  return {
    type: 'scroll',
    bottom: 0,
    icon: 'roundRect',
    itemWidth: 14,
    itemHeight: 9,
    data: items,
    textStyle: { fontFamily: MONO, fontSize: 11, color: INK },
  };
}
