import type { EChartsOption } from 'echarts';
import { baseTextStyle, TOOLTIP, valueAxis, yName, bottomLegend } from './echartsTheme';
import { groupedXAxis, type Ordered } from './ordered';
import type { Breakdown } from './contextBreakdown';

export function contextOption(
  bd: Breakdown,
  o: Ordered,
  showHit: boolean,
  hitData: (number | null)[],
  barMaxWidth?: number,
  barCategoryGap: string = '20%',
): EChartsOption {
  const barSeries = bd.buckets.map((b) => ({
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
          name: 'prefix cache hit rate',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 1,
          data: hitData,
          connectNulls: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { color: '#f03e3e', width: 2 },
          itemStyle: { color: '#f03e3e' },
          z: 12,
        },
      ]
    : barSeries;

  const yAxis = showHit
    ? [
        valueAxis({ ...yName('context length (tokens)', 58), min: 0 }),
        valueAxis({ min: 0, max: 100, inverse: true, splitLine: { show: false } }),
      ]
    : [valueAxis({ ...yName('context length (tokens)', 58), min: 0 })];

  return {
    textStyle: baseTextStyle(),
    tooltip: { ...TOOLTIP, trigger: 'axis' },
    legend: bottomLegend(showHit ? bd.buckets.concat(['prefix cache hit rate']) : bd.buckets),
    grid: { left: 74, right: showHit ? 60 : 24, top: 48, bottom: 66 },
    xAxis: groupedXAxis(o),
    yAxis,
    series,
  } as unknown as EChartsOption;
}
