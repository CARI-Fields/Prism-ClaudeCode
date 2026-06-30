import { echarts } from './echartsCore';

const MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

// Flat, hairline tooltip + solid splitlines (Foundry idiom — no elevation glow).
// `split` is a dedicated, lighter gridline color so splitlines sit quieter than
// the heavier axis `line`. `tipBg`/`tipBorder` match the design's tooltip tokens
// (panel-2 surface, line-2 border) rather than the panel/line used elsewhere.
function theme(
  ink: string,
  muted: string,
  line: string,
  split: string,
  tipBg: string,
  tipBorder: string,
) {
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: MONO, color: ink },
    categoryAxis: {
      axisLine: { lineStyle: { color: line } },
      axisTick: { show: false },
      axisLabel: { color: muted, fontFamily: MONO, fontSize: 11 },
      splitLine: { show: false },
    },
    valueAxis: {
      axisLabel: { color: muted, fontFamily: MONO, fontSize: 11 },
      splitLine: { lineStyle: { color: split } },
    },
    legend: { textStyle: { color: ink, fontFamily: MONO, fontSize: 11 } },
    tooltip: {
      backgroundColor: tipBg,
      borderColor: tipBorder,
      borderWidth: 1,
      padding: [8, 11],
      textStyle: { color: ink, fontFamily: MONO, fontSize: 12 },
    },
  };
}

export const REPORT_LIGHT = theme('#0d1320', '#5b6573', '#d7dde6', '#e7ebf1', '#ffffff', '#d7dde6');
export const REPORT_DARK = theme('#e6ecf4', '#97a3b4', '#313b47', '#2a323c', '#232a33', '#3d4753');

export function reportThemeName(mode: 'light' | 'dark'): string {
  return mode === 'dark' ? 'report-dark' : 'report-light';
}

let registered = false;
export function registerReportThemes(): void {
  if (registered) return;
  echarts.registerTheme('report-light', REPORT_LIGHT);
  echarts.registerTheme('report-dark', REPORT_DARK);
  registered = true;
}
