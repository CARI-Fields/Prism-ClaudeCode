import type { EChartsOption } from 'echarts';
import type { MetricRow, OverheadRow } from './conditionMetrics';
import type { MatrixCell } from './matrix';
import {
  STATUS_COLORS,
  STATUS_GLYPHS,
  PALETTE,
  baseTextStyle,
  axisLabelStyle,
  TOOLTIP,
  valueAxis,
  catAxis,
  xName,
  yName,
  rightLegend,
  bottomLegend,
} from './echartsTheme';
import { fmt, fmtUsd, fmtMetric } from './format';
import { conditionColor } from '../theme';
import { taskLabel } from '../data/taskLabel';

// ---------------------------------------------------------------------------
// matrixOption — heatmap showing per-cell status codes
// Ported from renderMatrix() echarts_report.py:1411-1451
// ---------------------------------------------------------------------------
export function matrixOption(m: {
  rows: string[];
  cols: string[];
  cells: MatrixCell[];
}): EChartsOption {
  const { rows, cols, cells } = m;
  const colIndex = new Map(cols.map((c, i) => [c, i]));
  const rowIndex = new Map(rows.map((r, i) => [r, i]));

  return {
    textStyle: baseTextStyle(),
    tooltip: {
      ...TOOLTIP,
      formatter(params: { data: [number, number, number] }) {
        const cell = cells.find(
          (d) =>
            colIndex.get(d.condition) === params.data[0] && rowIndex.get(d.row) === params.data[1],
        );
        if (!cell) return '';
        return [
          `<b>${cell.row} &middot; ${cell.condition}</b>`,
          `status: ${cell.status}`,
          `run: ${cell.run_id ?? 'n/a'}`,
          `requests: ${cell.num_requests ?? 'n/a'}`,
          `cost: ${fmtUsd(cell.total_cost_usd)}`,
          `quality: ${fmt(cell.quality_score)}`,
          `completion: ${fmt(cell.completion_time_s)}s`,
        ].join('<br>');
      },
    },
    grid: { left: 94, right: 16, top: 12, bottom: 64 },
    xAxis: catAxis({ data: cols, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
    yAxis: catAxis({ data: rows }),
    visualMap: { show: false, min: 0, max: 3, inRange: { color: STATUS_COLORS } },
    series: [
      {
        type: 'heatmap',
        data: cells.map((d) => [colIndex.get(d.condition), rowIndex.get(d.row), d.status_code]),
        label: {
          show: true,
          color: '#ffffff',
          fontSize: 13,
          fontWeight: 600,
          formatter: (p: { data: [number, number, number] }) => STATUS_GLYPHS[p.data[2]] ?? '',
        },
        itemStyle: { borderColor: '#ffffff', borderWidth: 3 },
        emphasis: { itemStyle: { borderWidth: 1 } },
      },
    ],
  } as unknown as EChartsOption;
}

// ---------------------------------------------------------------------------
// conditionOption — bar chart comparing conditions per metric
// Ported from renderConditionChart() echarts_report.py:1453-1481
// ---------------------------------------------------------------------------
export function conditionOption(
  metrics: MetricRow[],
  conditions: string[],
  tasks: string[],
  metric: string,
  metricLabel: string,
): EChartsOption {
  const grouped = tasks.length > 1;
  const series = tasks.map((task, ti) => {
    const rows = metrics.filter((r) => r.task === task);
    return {
      name: taskLabel(task),
      type: 'bar' as const,
      barMaxWidth: 46,
      data: conditions.map((c) => {
        const row = rows.find((r) => r.condition === c);
        return row ? ((row as unknown as Record<string, unknown>)[metric] as number | null) : null;
      }),
      itemStyle: grouped
        ? {
            color: PALETTE[ti % PALETTE.length],
            borderRadius: [4, 4, 0, 0] as [number, number, number, number],
          }
        : {
            color: (p: { dataIndex: number }) => conditionColor(conditions[p.dataIndex] ?? ''),
            borderRadius: [4, 4, 0, 0] as [number, number, number, number],
          },
      label: {
        show: !grouped,
        position: 'top' as const,
        fontSize: 11,
        formatter: (p: { value: number | null }) => fmtMetric(p.value, metric),
      },
    };
  });

  return {
    textStyle: baseTextStyle(),
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis' as const,
      valueFormatter: (value: number | null) => fmtMetric(value, metric),
    },
    legend: grouped ? bottomLegend(tasks.map(taskLabel)) : { show: false },
    grid: { left: 66, right: 20, top: 18, bottom: grouped ? 92 : 72 },
    xAxis: catAxis({ data: conditions, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
    yAxis: valueAxis(yName(metricLabel, 54)),
    series,
  } as unknown as EChartsOption;
}

// ---------------------------------------------------------------------------
// overheadOption — bar chart showing factors relative to single_agent baseline
// Ported from renderOverheadChart() echarts_report.py:1488-1518
// ---------------------------------------------------------------------------
export function overheadOption(
  overheads: OverheadRow[],
  conditions: string[],
  tasks: string[],
  factor: string,
  factorLabel: string,
): EChartsOption {
  const grouped = tasks.length > 1;
  const series = tasks.map((task, ti) => {
    const rows = overheads.filter((r) => r.task === task);
    return {
      name: taskLabel(task),
      type: 'bar' as const,
      barMaxWidth: 46,
      data: conditions.map((c) => {
        const row = rows.find((r) => r.condition === c);
        return row ? ((row as unknown as Record<string, unknown>)[factor] as number | null) : null;
      }),
      itemStyle: grouped
        ? {
            color: PALETTE[ti % PALETTE.length],
            borderRadius: [4, 4, 0, 0] as [number, number, number, number],
          }
        : {
            color: (p: { dataIndex: number }) => conditionColor(conditions[p.dataIndex] ?? ''),
            borderRadius: [4, 4, 0, 0] as [number, number, number, number],
          },
      label: {
        show: !grouped,
        position: 'top' as const,
        fontSize: 11,
        formatter: (p: { value: number | null }) => (p.value === null ? '' : `${fmt(p.value, 2)}×`),
      },
      markLine:
        ti === 0
          ? {
              symbol: 'none',
              data: [{ yAxis: 1 }],
              label: {
                position: 'end',
                formatter: '1.0× baseline',
                fontSize: 10,
              },
              lineStyle: { type: 'dashed' },
            }
          : undefined,
    };
  });

  return {
    textStyle: baseTextStyle(),
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis' as const,
      formatter(params: { name: string; seriesName: string; value: number | null }[]) {
        return params
          .map(
            (p) =>
              `<b>${p.name}</b><br>${grouped ? p.seriesName + ' · ' : ''}${factorLabel}: ${fmt(p.value, 2)}×`,
          )
          .join('<br>');
      },
    },
    legend: grouped ? bottomLegend(tasks.map(taskLabel)) : { show: false },
    grid: { left: 62, right: 26, top: 18, bottom: grouped ? 92 : 72 },
    xAxis: catAxis({ data: conditions, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
    yAxis: valueAxis({ ...yName('× vs single_agent', 50), min: 0 }),
    series,
  } as unknown as EChartsOption;
}

// ---------------------------------------------------------------------------
// efficiencyOption — scatter: cost vs quality, bubble size = requests
// Ported from renderEfficiencyChart() echarts_report.py:1520-1562
// ---------------------------------------------------------------------------

/** Select the quality field appropriate for the task type. */
function qualityFieldFor(task: string): keyof MetricRow {
  if (task.startsWith('coding')) return 'mean_speedup';
  if (task.startsWith('research')) return 'mean_research_rubric_score';
  return 'mean_quality_score';
}

/** Human-readable y-axis label for the quality field. */
function qualityAxisLabel(task: string): string {
  const prefix = task.startsWith('coding')
    ? 'mean speedup'
    : task.startsWith('research')
      ? 'mean rubric score'
      : 'mean quality score';
  return `${prefix} · ${taskLabel(task)}`;
}

export function efficiencyOption(
  metrics: MetricRow[],
  conditions: string[],
  task: string,
): EChartsOption {
  const qField = qualityFieldFor(task);

  const validRows = metrics.filter(
    (r) => r.task === task && r.runs > 0 && r.mean_total_cost_usd != null && r[qField] != null,
  );
  const maxRequests = Math.max(1, ...validRows.map((r) => r.mean_num_requests ?? 0));

  const series = conditions.map((condition) => {
    const row = validRows.find((r) => r.condition === condition);
    const quality = row != null ? row[qField] : null;
    const data =
      row != null && quality != null
        ? [
            [
              row.mean_total_cost_usd,
              quality,
              row.mean_num_requests ?? 0,
              row.success_rate,
              row.mean_cache_hit_ratio,
              row.mean_cost_efficiency_score,
              condition,
            ],
          ]
        : [];

    return {
      name: condition,
      type: 'scatter' as const,
      data,
      symbolSize(value: number[]) {
        return Math.max(12, Math.min(46, 12 + 34 * ((value[2] ?? 0) / maxRequests)));
      },
      label: { show: false },
      itemStyle: {
        color: conditionColor(condition),
        opacity: 0.82,
        borderColor: '#ffffff',
        borderWidth: 1,
      },
    };
  });

  return {
    textStyle: baseTextStyle(),
    tooltip: {
      ...TOOLTIP,
      formatter(params: { seriesName: string; data: (number | string | null)[] }) {
        const v = params.data;
        return [
          `<b>${params.seriesName}</b>`,
          `cost: ${fmtUsd(v[0] as number | null)}`,
          `quality: ${fmt(v[1] as number | null)}`,
          `requests: ${fmt(v[2] as number | null)}`,
          `success: ${fmt(((v[3] as number | null) ?? 0) * 100)}%`,
          `cache hit: ${fmt(((v[4] as number | null) ?? 0) * 100)}%`,
          `quality / $: ${fmt(v[5] as number | null)}`,
        ].join('<br>');
      },
    },
    legend: rightLegend(conditions),
    grid: { left: 64, right: 152, top: 16, bottom: 50 },
    // Positioning map: scale both axes to the data so the conditions spread out
    // and relative cost/quality is legible, rather than crushed against a 0-origin.
    xAxis: valueAxis({ ...xName('mean total cost ($)', 28), scale: true }),
    yAxis: valueAxis({ ...yName(qualityAxisLabel(task), 56), scale: true }),
    series,
  } as unknown as EChartsOption;
}
