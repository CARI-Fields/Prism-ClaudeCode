import { fmtAxis } from './format';

export const STATUS_COLORS = ['#eef1f5', '#e03131', '#2f9e44', '#adb5bd'];
export const STATUS_GLYPHS = ['', '✗', '✓', '–'];
export const PALETTE = [
  '#3b5bdb',
  '#0c8599',
  '#e8590c',
  '#7048e8',
  '#c2255c',
  '#1098ad',
  '#f59f00',
];
const MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

export function baseTextStyle() {
  return { fontFamily: MONO };
}
export function axisLabelStyle() {
  return { fontFamily: MONO, fontSize: 11 };
}
// Per-option tooltips omit `extraCssText` so the registered theme's rounded
// corners + per-mode drop-shadow (see echartsThemes.ts) apply on every chart.
export const TOOLTIP = { confine: true, padding: [8, 11] as [number, number] };

export function valueAxis(extra: Record<string, unknown> = {}) {
  return { type: 'value', axisLabel: { ...axisLabelStyle(), formatter: fmtAxis }, ...extra };
}
export function catAxis(extra: Record<string, unknown> = {}) {
  return { type: 'category', axisLabel: axisLabelStyle(), axisTick: { show: false }, ...extra };
}
export function xName(name: string, gap: number) {
  return {
    name,
    nameLocation: 'middle',
    nameGap: gap,
    nameTextStyle: { fontFamily: MONO, fontSize: 11 },
  };
}
export function yName(name: string, gap: number) {
  return {
    name,
    nameLocation: 'middle',
    nameGap: gap,
    nameRotate: 90,
    nameTextStyle: { fontFamily: MONO, fontSize: 11 },
  };
}
export function rightLegend(items: string[]) {
  return {
    type: 'scroll',
    orient: 'vertical',
    right: 6,
    top: 'middle',
    icon: 'roundRect',
    itemWidth: 12,
    itemHeight: 8,
    itemGap: 12,
    data: items,
    textStyle: { fontFamily: MONO, fontSize: 11 },
  };
}
export function bottomLegend(items: string[]) {
  return {
    type: 'scroll',
    bottom: 0,
    icon: 'roundRect',
    itemWidth: 12,
    itemHeight: 8,
    itemGap: 12,
    data: items,
    textStyle: { fontFamily: MONO, fontSize: 11 },
  };
}
