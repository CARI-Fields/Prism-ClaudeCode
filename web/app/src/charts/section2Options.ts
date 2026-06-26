// Ported from analysis/echarts_report.py
//   cacheOption  <- renderCacheChartFor()   lines 1575-1649
//   latencyOption <- renderLatencyChart()   lines 1651-1693
// -------------------------------------------------------------------
import type { EChartsOption } from 'echarts';
import type { Turn } from '../types';
import type { CacheRow } from './cacheTimeline';
import { promptTokens } from './cacheTimeline';
import { REP_LINE_TYPES, REQUEST_TYPE_SYMBOLS, agentDotSpec } from './agentSymbols';
import { baseTextStyle, TOOLTIP, valueAxis, xName, yName, rightLegend } from './echartsTheme';
import { conditionColor } from '../theme';
import { fmt } from './format';

// ----------------------------------------------------------------
// Internal data-point shapes (avoids `any` in implementation)
// ----------------------------------------------------------------

type CacheDataPoint = {
  value: [number, number];
  run_id: string;
  condition: string;
  rep: number;
  type: string;
  request_index: number;
  cum_read: number;
  cum_ctx: number;
  label: string;
};

type ScatterDataPoint = {
  value: [number, number, number | null, string, number, string, number | null];
  symbol: string;
  symbolSize: number;
  itemStyle?: { color: string; borderColor?: string; borderWidth?: number; opacity?: number };
};

// ----------------------------------------------------------------
// cacheOption
// Port of renderCacheChartFor() echarts_report.py:1575-1649
// One line series per (run_id, request_type); name = condition so the legend
// collapses all runs of a condition into one toggle.
// ----------------------------------------------------------------

export function cacheOption(
  rows: CacheRow[],
  conditions: string[],
  singleAgent: string,
): EChartsOption {
  // Group by (run_id, agent type) -- one line per pair, no averaging across reps
  const groups = new Map<
    string,
    { run_id: string; condition: string; rep: number; type: string; points: CacheRow[] }
  >();
  for (const r of rows) {
    const type = r.request_type || 'main-agent';
    const key = `${r.run_id}|${type}`;
    if (!groups.has(key)) {
      groups.set(key, { run_id: r.run_id, condition: r.condition, rep: r.rep, type, points: [] });
    }
    groups.get(key)!.points.push(r);
  }

  const condOrder = new Map(conditions.map((c, i) => [c, i]));

  const series = [...groups.values()]
    .sort(
      (a, b) =>
        ((condOrder.get(a.condition) ?? 999) - (condOrder.get(b.condition) ?? 999)) ||
        (a.rep - b.rep) ||
        a.type.localeCompare(b.type),
    )
    .map((g) => {
      const color = conditionColor(g.condition);
      // All runs of a condition share the legend name so the legend collapses to one chip.
      let runLabel = `${g.condition} r${g.rep}`;
      if (singleAgent === 'all') runLabel = `${runLabel} \u00b7 ${g.type}`;
      const pts = g.points.slice().sort((a, b) => (a.ordinal || 0) - (b.ordinal || 0));
      const spec = agentDotSpec(g.type);
      const data: CacheDataPoint[] = pts.map((r) => ({
        value: [r.ordinal, (r.accumulated_cache_hit_rate ?? 0) * 100],
        run_id: g.run_id,
        condition: g.condition,
        rep: g.rep,
        type: g.type,
        request_index: r.request_index,
        cum_read: r.cum_cache_read,
        cum_ctx: r.cum_context_tokens,
        label: runLabel,
      }));
      return {
        // shared legend name collapses runs of same condition
        name: g.condition,
        type: 'line' as const,
        showSymbol: true,
        // main-agent = solid circle; each subagent = own shape; security-monitor = diamond
        symbol: REQUEST_TYPE_SYMBOLS[g.type] ?? 'circle',
        symbolSize: spec.size,
        data,
        lineStyle: { width: 2, type: REP_LINE_TYPES[g.rep] ?? 'solid', color },
        itemStyle: { color },
      };
    });

  const condsPresent = conditions.filter((c) => series.some((s) => s.name === c));

  return {
    textStyle: baseTextStyle(),
    tooltip: {
      ...TOOLTIP,
      trigger: 'item',
      formatter(p: { data: CacheDataPoint; value: [number, number]; seriesName: string }) {
        const d = p.data ?? ({} as CacheDataPoint);
        const x = p.value?.[0] ?? 0;
        const y = p.value?.[1] ?? 0;
        const read = d.cum_read != null ? fmt(d.cum_read) : '0';
        const ctx = d.cum_ctx != null ? fmt(d.cum_ctx) : '0';
        return (
          `<b>${d.label ?? p.seriesName}</b>` +
          `<br>run: ${d.run_id ?? '\u2014'}` +
          `<br>agent type: ${d.type ?? 'main-agent'}` +
          `<br>request # in stream: ${x}` +
          `<br>accumulated hit rate: ${fmt(y, 1)}%` +
          `<br>cumulative cache read: ${read} of ${ctx} context tokens`
        );
      },
    },
    legend: rightLegend(condsPresent),
    grid: { left: 72, right: 230, top: 16, bottom: 62 },
    xAxis: { type: 'value', name: 'Request # within selected run', min: 1 },
    yAxis: valueAxis({ ...yName('prefix cache hit rate (%)', 52), min: 0, max: 100 }),
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 18 }],
    series,
  } as unknown as EChartsOption;
}

// ----------------------------------------------------------------
// latencyOption
// Port of renderLatencyChart() echarts_report.py:1651-1693
// Scatter per condition: x = prompt context tokens, y = per-turn prefix cache hit %.
// Turns with context <= 0 are skipped.
// ----------------------------------------------------------------

export function latencyOption(turns: Turn[], conditions: string[]): EChartsOption {
  const byCondition = new Map<string, ScatterDataPoint[]>();

  for (const turn of turns) {
    const ctx = promptTokens(turn);
    if (ctx <= 0) continue;
    const hitRate = (100 * (turn.cache_read ?? 0)) / ctx;
    if (!byCondition.has(turn.condition)) byCondition.set(turn.condition, []);
    const color = conditionColor(turn.condition);
    const type = turn.request_type || 'main-agent';
    const spec = agentDotSpec(type);
    const item: ScatterDataPoint = {
      value: [
        ctx,
        hitRate,
        turn.total_s ?? null,
        turn.run_id,
        (turn.request_index ?? 0) + 1,
        type,
        turn.ttft_s ?? null,
      ],
      // main-agent = circle; each subagent = own shape; security-monitor = diamond
      symbol: REQUEST_TYPE_SYMBOLS[type] ?? 'circle',
      symbolSize: spec.size,
    };
    // security-monitor renders hollow (outline only); others are filled
    if (spec.hollow) {
      item.itemStyle = { color: 'transparent', borderColor: color, borderWidth: 1.6, opacity: 0.95 };
    }
    byCondition.get(turn.condition)!.push(item);
  }

  const series = conditions.map((condition) => ({
    name: condition,
    type: 'scatter' as const,
    data: byCondition.get(condition) ?? [],
    itemStyle: { color: conditionColor(condition), opacity: 0.72 },
  }));

  return {
    textStyle: baseTextStyle(),
    tooltip: {
      ...TOOLTIP,
      formatter(params: { seriesName: string; value: (number | string | null)[] }) {
        const v = params.value;
        return (
          `<b>${params.seriesName}</b>` +
          `<br>run: ${v[3]}` +
          `<br>Request # within selected run: ${v[4]}` +
          `<br>Request type: ${String(v[5] ?? 'main-agent')}` +
          `<br>context length: ${fmt(v[0] as number | null)}` +
          `<br>prefix cache hit rate: ${fmt(v[1] as number | null, 1)}%` +
          `<br>TTFT: ${fmt(v[6] as number | null)}s` +
          `<br>total: ${fmt(v[2] as number | null)}s`
        );
      },
    },
    legend: rightLegend(conditions),
    grid: { left: 64, right: 152, top: 16, bottom: 62 },
    xAxis: valueAxis(xName('context length (tokens)', 30)),
    yAxis: valueAxis({ ...yName('prefix cache hit rate (%)', 52), min: 0, max: 100 }),
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 20 }],
    series,
  } as unknown as EChartsOption;
}
