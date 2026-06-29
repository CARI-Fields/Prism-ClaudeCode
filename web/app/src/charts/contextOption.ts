import type { EChartsOption } from 'echarts';
import { baseTextStyle, TOOLTIP, valueAxis, axisLabelStyle, yName, bottomLegend } from './echartsTheme';
import { groupedXAxis, type Ordered } from './ordered';
import type { Breakdown } from './contextBreakdown';

export function contextOption(
  bd: Breakdown,
  o: Ordered,
  showHit: boolean,
  hitData: (number | null)[],
  barMaxWidth?: number,
  barCategoryGap: string = '20%',
  dark: boolean = false,
): EChartsOption {
  // The cache-hit overlay is deliberately monochrome (theme ink) so it never
  // reads as one of the constant context-source data hues.
  const hitInk = dark ? '#e6ecf4' : '#0d1320';
  // Stack so the "head" of the context window (the stable prefix — system prompt,
  // tools …) reads at the TOP of each bar and the last-appended context (messages /
  // conversation) at the bottom. ECharts draws the first stacked series at the
  // bottom, so iterate buckets tail→head. bd.buckets stays head→tail for the legend.
  const stackBuckets = [...bd.buckets].reverse();
  const barSeries = stackBuckets.map((b) => ({
    name: b,
    type: 'bar' as const,
    stack: 'context',
    xAxisIndex: 0,
    yAxisIndex: 0,
    barMaxWidth,
    barCategoryGap,
    data: o.indexes.map((pos) => bd.byKey.get(`${pos}:${b}`) ?? 0),
    itemStyle: { color: bd.colors[b] ?? '#868e96' },
  }));

  const series: EChartsOption['series'] = showHit
    ? [
        ...barSeries,
        {
          name: 'cache hit',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 1,
          data: hitData,
          connectNulls: true,
          smooth: true,
          showSymbol: false,
          lineStyle: { color: hitInk, width: 2 },
          itemStyle: { color: hitInk },
          z: 12,
        },
      ]
    : barSeries;

  const yAxis = showHit
    ? [
        valueAxis({ ...yName('tokens', 58), min: 0 }),
        valueAxis({ min: 0, max: 100, inverse: true, splitLine: { show: false }, axisLabel: { ...axisLabelStyle(), formatter: (v: number) => `${v}%` } }),
      ]
    : [valueAxis({ ...yName('tokens', 58), min: 0 })];

  return {
    textStyle: baseTextStyle(),
    tooltip: { ...TOOLTIP, trigger: 'axis' },
    legend: bottomLegend(showHit ? bd.buckets.concat(['cache hit']) : bd.buckets),
    grid: { left: 74, right: showHit ? 60 : 24, top: 48, bottom: 66 },
    xAxis: groupedXAxis(o),
    yAxis,
    series,
  } as unknown as EChartsOption;
}
