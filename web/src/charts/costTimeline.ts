import type { EChartsOption } from 'echarts';
import type { Turn } from '../types';
import { baseTextStyle, TOOLTIP, valueAxis, yName, bottomLegend } from './echartsTheme';
import { REQUEST_TYPE_SYMBOLS } from './agentSymbols';
import { groupedXAxis, type Ordered } from './ordered';

const n = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

export function costTimelineOption(rows: Turn[], o: Ordered, barMaxWidth: number): EChartsOption {
  const ordered = o.indexes.map(i => rows[i]);

  function barData(field: keyof Turn): number[] {
    return ordered.map(t => n(t[field]));
  }

  function lineData(field: keyof Turn): { value: number; symbol: string }[] {
    return ordered.map(t => ({
      value: n(t[field]),
      symbol: REQUEST_TYPE_SYMBOLS[String(t.request_type ?? '')] ?? 'circle',
    }));
  }

  return {
    textStyle: baseTextStyle(),
    tooltip: { ...TOOLTIP, trigger: 'axis' },
    legend: bottomLegend(['input', 'cache read', 'cache write 5m', 'cache write 1h', 'output', 'TTFT', 'total']),
    grid: { left: 66, right: 24, top: 16, bottom: 120 },
    xAxis: groupedXAxis(o),
    yAxis: [
      valueAxis({ ...yName('tokens', 58), min: 0 }),
      valueAxis({ ...yName('seconds', 46), splitLine: { show: false } }),
    ] as EChartsOption['yAxis'],
    series: [
      { name: 'input',          type: 'bar',  stack: 'tokens', xAxisIndex: 0, barMaxWidth, data: barData('input_tokens'),       itemStyle: { color: '#3b5bdb' } },
      { name: 'cache read',     type: 'bar',  stack: 'tokens', xAxisIndex: 0, barMaxWidth, data: barData('cache_read'),          itemStyle: { color: '#0c8599' } },
      { name: 'cache write 5m', type: 'bar',  stack: 'tokens', xAxisIndex: 0, barMaxWidth, data: barData('cache_creation_5m'),  itemStyle: { color: '#e8590c' } },
      { name: 'cache write 1h', type: 'bar',  stack: 'tokens', xAxisIndex: 0, barMaxWidth, data: barData('cache_creation_1h'),  itemStyle: { color: '#f59f00' } },
      { name: 'output',         type: 'bar',  stack: 'tokens', xAxisIndex: 0, barMaxWidth, data: barData('output_tokens'),      itemStyle: { color: '#7048e8' } },
      {
        name: 'TTFT', type: 'line', xAxisIndex: 0, yAxisIndex: 1,
        data: lineData('ttft_s'),
        itemStyle: { color: '#1098ad' },
        lineStyle: { color: '#1098ad' },
      },
      {
        name: 'total', type: 'line', xAxisIndex: 0, yAxisIndex: 1,
        data: lineData('total_s'),
        itemStyle: { color: '#c2255c' },
        lineStyle: { color: '#c2255c' },
      },
    ],
  };
}
