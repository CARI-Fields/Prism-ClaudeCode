import { echarts } from './echartsCore';

const MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

function theme(ink: string, muted: string, line: string, panel: string) {
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
      splitLine: { lineStyle: { color: line, type: 'dashed' } },
    },
    legend: { textStyle: { color: ink, fontFamily: MONO, fontSize: 11 } },
    tooltip: {
      backgroundColor: panel,
      borderColor: line,
      textStyle: { color: ink, fontFamily: MONO, fontSize: 12 },
    },
  };
}

export const REPORT_LIGHT = theme('#10151d', '#5c6675', '#dde2e9', '#ffffff');
export const REPORT_DARK = theme('#e7ecf3', '#9aa6b4', '#38404b', '#252b34');

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
