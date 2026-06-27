import { echarts } from './echartsCore';

const MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

// `tooltipShadow` lifts the tooltip off the surface per-mode. The per-option
// tooltips (see TOOLTIP in echartsTheme.ts) intentionally omit `extraCssText`
// so this theme-level value wins and the drop-shadow renders on every chart.
function theme(ink: string, muted: string, line: string, panel: string, tooltipShadow: string) {
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
      borderWidth: 1,
      padding: [8, 11],
      textStyle: { color: ink, fontFamily: MONO, fontSize: 12 },
      extraCssText: `border-radius:8px; box-shadow:${tooltipShadow};`,
    },
  };
}

export const REPORT_LIGHT = theme('#0d1320', '#5b6573', '#d7dde6', '#ffffff', '0 6px 20px rgba(13,19,32,0.16)');
export const REPORT_DARK = theme('#e6ecf4', '#97a3b4', '#313b47', '#1e242c', '0 10px 28px rgba(0,0,0,0.60)');

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
