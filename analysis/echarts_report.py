from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import pandas as pd


CONDITIONS = ["single_agent", "goal", "subagents", "ralph_loop", "dynamic_workflow", "loop_dynamic"]
TASKS = ["coding", "research"]
REPS = [1, 2, 3]
STATUS_CODE = {"missing": 0, "failed": 1, "success": 2, "skipped": 3}
OVERHEAD_METRICS = [
    ("completion_time_factor", "mean_completion_time_s"),
    ("num_requests_factor", "mean_num_requests"),
    ("total_cost_factor", "mean_total_cost_usd"),
    ("peak_prompt_tokens_factor", "mean_peak_prompt_tokens"),
    ("total_cache_read_factor", "mean_total_cache_read"),
    ("output_tokens_factor", "mean_output_tokens_total"),
]


def render_echarts_report(
    runs: pd.DataFrame,
    turns: pd.DataFrame,
    components: pd.DataFrame,
    html_path: str | Path,
    component_texts: pd.DataFrame | None = None,
) -> Path:
    html_path = Path(html_path)
    data = build_dashboard_data(runs, turns, components)
    texts = _context_text_map(component_texts)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(_render_html(data, texts), encoding="utf-8")
    return html_path


def _context_text_map(component_texts: pd.DataFrame | None) -> dict[str, Any]:
    """Flat lookup for the context-text panel. Stable components are keyed by
    ``run|*|component`` (one preview per run); volatile ones by ``run|index|component``."""
    out: dict[str, Any] = {}
    if component_texts is None or component_texts.empty:
        return out
    for rec in component_texts.to_dict("records"):
        run_id = rec.get("run_id")
        component = rec.get("component")
        if not run_id or not component:
            continue
        entry = {
            "text": rec.get("text") or "",
            "truncated": bool(rec.get("truncated")),
            "bytes": int(rec.get("bytes") or 0),
        }
        if rec.get("stable"):
            out[f"{run_id}|*|{component}"] = entry
        else:
            out[f"{run_id}|{_clean(rec.get('request_index'))}|{component}"] = entry
    return out


def build_dashboard_data(
    runs: pd.DataFrame,
    turns: pd.DataFrame,
    components: pd.DataFrame,
) -> dict[str, Any]:
    runs = runs.copy()
    turns = turns.copy()
    components = components.copy()
    for df in (runs, turns, components):
        if "rep" in df.columns:
            df["rep"] = pd.to_numeric(df["rep"], errors="coerce").astype("Int64")
    condition_metrics = _condition_metrics(runs, turns)
    turn_records = _turn_records(turns)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "conditions": CONDITIONS,
        "tasks": TASKS,
        "reps": REPS,
        "matrix_rows": _matrix_rows(),
        "matrix": _matrix(runs),
        "condition_metrics": condition_metrics,
        "condition_overheads": _condition_overheads(condition_metrics),
        "runs": _run_records(runs),
        "turns": turn_records,
        "cache_timeline": _cache_timeline_records(turn_records),
        "cache_by_agent": _cache_agent_timeline_records(turn_records),
        "components": _component_records(components),
        "context_source_components": _component_records(components),
        "context_token_components": _context_token_component_records(turn_records),
    }


def _matrix_rows() -> list[str]:
    return [f"{task} r{rep}" for task in TASKS for rep in REPS]


def _matrix(runs: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    matrix_rows = _matrix_rows()
    for task in TASKS:
        for rep in REPS:
            row_label = f"{task} r{rep}"
            row_index = matrix_rows.index(row_label)
            for condition_index, condition in enumerate(CONDITIONS):
                match = _filter_eq(_filter_eq(_filter_eq(runs, "task", task), "condition", condition), "rep", rep)
                if match.empty:
                    status = "missing"
                    record: dict[str, Any] = {}
                else:
                    record = match.sort_values("run_id").iloc[-1].to_dict()
                    if str(record.get("status", "")).lower() == "skipped":
                        status = "skipped"
                    else:
                        status = "success" if bool(record.get("success")) else "failed"
                rows.append({
                    "task": task,
                    "rep": rep,
                    "condition": condition,
                    "condition_index": condition_index,
                    "row": row_label,
                    "row_index": row_index,
                    "status": status,
                    "status_code": STATUS_CODE[status],
                    "run_id": _clean(record.get("run_id")) if record else None,
                    "completion_time_s": _clean(record.get("completion_time_s")) if record else None,
                    "num_requests": _clean(record.get("num_requests")) if record else None,
                    "cache_hit_ratio": _clean(record.get("cache_hit_ratio")) if record else None,
                    "total_cost_usd": _clean(record.get("total_cost_usd")) if record else None,
                    "quality_score": _clean(record.get("quality_score")) if record else None,
                })
    return rows


def _condition_metrics(runs: pd.DataFrame, turns: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for task in ["all", *TASKS]:
        for condition in CONDITIONS:
            rgroup = _filter_eq(runs, "condition", condition)
            tgroup = _filter_eq(turns, "condition", condition)
            if task != "all":
                rgroup = _filter_eq(rgroup, "task", task)
                tgroup = _filter_eq(tgroup, "task", task)
            rows.append(_metric_row(task, condition, rgroup, tgroup))
    return rows


def _metric_row(task: str, condition: str, runs: pd.DataFrame, turns: pd.DataFrame) -> dict[str, Any]:
    success_values = _num_series(runs, "success")
    return {
        "task": task,
        "condition": condition,
        "runs": int(len(runs)),
        "success_rate": _mean(success_values),
        "mean_completion_time_s": _mean(_num_series(runs, "completion_time_s")),
        "mean_num_requests": _mean(_num_series(runs, "num_requests")),
        "mean_cache_hit_ratio": _mean(_num_series(runs, "cache_hit_ratio")),
        "mean_total_cache_read": _mean(_num_series(runs, "total_cache_read")),
        "mean_peak_prompt_tokens": _mean(_num_series(runs, "peak_prompt_tokens")),
        "mean_output_tokens_total": _mean(_num_series(runs, "output_tokens_total")),
        "mean_total_cost_usd": _mean(_num_series(runs, "total_cost_usd")),
        "mean_input_cost_usd": _mean(_num_series(runs, "input_cost_usd")),
        "mean_cache_read_cost_usd": _mean(_num_series(runs, "cache_read_cost_usd")),
        "mean_cache_creation_5m_cost_usd": _mean(_num_series(runs, "cache_creation_5m_cost_usd")),
        "mean_cache_creation_1h_cost_usd": _mean(_num_series(runs, "cache_creation_1h_cost_usd")),
        "mean_output_cost_usd": _mean(_num_series(runs, "output_cost_usd")),
        "mean_quality_score": _mean(_num_series(runs, "quality_score")),
        "mean_cost_efficiency_score": _mean(_num_series(runs, "cost_efficiency_score")),
        "mean_research_rubric_score": _mean(_num_series(runs, "research_rubric_score")),
        "mean_coding_quality_score": _mean(_num_series(runs, "coding_quality_score")),
        "mean_speedup": _mean(_num_series(runs, "speedup")),
        "ttft_p50_s": _quantile(_num_series(turns, "ttft_s"), 0.5),
        "ttft_p95_s": _quantile(_num_series(turns, "ttft_s"), 0.95),
        "total_p50_s": _quantile(_num_series(turns, "total_s"), 0.5),
        "total_p95_s": _quantile(_num_series(turns, "total_s"), 0.95),
    }


def _condition_overheads(condition_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for task in ["all", *TASKS]:
        task_rows = [row for row in condition_metrics if row.get("task") == task]
        baseline = next((row for row in task_rows if row.get("condition") == "single_agent"), None)
        for row in task_rows:
            out = {
                "task": task,
                "condition": row.get("condition"),
                "runs": row.get("runs"),
                "baseline_condition": "single_agent",
            }
            for factor_name, metric_name in OVERHEAD_METRICS:
                value = row.get(metric_name)
                baseline_value = baseline.get(metric_name) if baseline else None
                out[metric_name] = value
                out[f"baseline_{metric_name}"] = baseline_value
                out[factor_name] = _safe_factor(value, baseline_value)
            rows.append(out)
    return rows


def _run_records(runs: pd.DataFrame) -> list[dict[str, Any]]:
    columns = [
        "run_id", "task", "condition", "rep", "model", "success", "correctness",
        "speedup", "completion_time_s", "num_subagents", "num_requests",
        "total_input", "total_cache_read", "total_cache_creation",
        "cache_hit_ratio", "peak_prompt_tokens", "output_tokens_total",
        "billable_input_tokens", "billable_cache_read_tokens",
        "billable_cache_creation_5m_tokens", "billable_cache_creation_1h_tokens",
        "billable_output_tokens", "input_cost_usd", "cache_read_cost_usd",
        "cache_creation_5m_cost_usd", "cache_creation_1h_cost_usd",
        "output_cost_usd", "total_cost_usd", "pricing_model",
        "quality_metric", "quality_score", "coding_quality_score",
        "research_quality_score", "research_rubric_score",
        "research_format_score", "research_coverage_score",
        "research_word_count", "research_unique_url_count",
        "research_exact_two_url_sections", "cost_efficiency_score",
        "speedup_per_dollar", "research_score_per_dollar",
    ]
    return _records(runs, columns)


def _turn_records(turns: pd.DataFrame) -> list[dict[str, Any]]:
    columns = [
        "run_id", "task", "condition", "rep", "request_index",
        "input_tokens", "output_tokens", "cache_read", "cache_creation_5m",
        "cache_creation_1h", "duration_ms", "ttft_s", "prefill_s", "total_s",
        "request_type", "input_cost_usd", "cache_read_cost_usd",
        "cache_creation_5m_cost_usd", "cache_creation_1h_cost_usd",
        "output_cost_usd", "total_cost_usd",
    ]
    records = _records(turns, columns)
    for row in records:
        row["cache_creation"] = (row.get("cache_creation_5m") or 0) + (row.get("cache_creation_1h") or 0)
        row["prompt_tokens"] = (
            (row.get("input_tokens") or 0)
            + (row.get("cache_read") or 0)
            + row["cache_creation"]
        )
    return records


def _cache_timeline_records(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    by_run: dict[str, list[dict[str, Any]]] = {}
    for turn in turns:
        run_id = turn.get("run_id")
        if not run_id:
            continue
        by_run.setdefault(str(run_id), []).append(turn)

    for run_id, run_turns in by_run.items():
        cum_read = 0.0
        cum_write = 0.0
        cum_input = 0.0
        cum_run_local_read = 0.0
        cum_run_local_write = 0.0
        cum_run_local_input = 0.0
        warm_start_by_type: dict[str, float] = {}
        for turn in sorted(run_turns, key=lambda row: row.get("request_index") or 0):
            read = float(turn.get("cache_read") or 0)
            write = float(turn.get("cache_creation") or 0)
            input_tokens = float(turn.get("input_tokens") or 0)
            request_type = str(turn.get("request_type") or "main-agent")
            if request_type not in warm_start_by_type:
                warm_start_by_type[request_type] = read
            warm_start_read = warm_start_by_type[request_type]
            run_local_read = max(0.0, read - warm_start_read)
            cum_read += read
            cum_write += write
            cum_input += input_tokens
            denom = cum_read + cum_write + cum_input
            cum_run_local_read += run_local_read
            cum_run_local_write += write
            cum_run_local_input += input_tokens
            run_local_denom = cum_run_local_read + cum_run_local_write + cum_run_local_input
            rows.append({
                "run_id": run_id,
                "task": turn.get("task"),
                "condition": turn.get("condition"),
                "rep": turn.get("rep"),
                "request_index": turn.get("request_index"),
                "request_type": request_type,
                "warm_start_cache_read": _clean(warm_start_read),
                "run_local_cache_read": _clean(run_local_read),
                "cum_cache_read": _clean(cum_read),
                "cum_cache_write": _clean(cum_write),
                "cum_input_tokens": _clean(cum_input),
                "cum_total_context_tokens": _clean(denom),
                "cum_run_local_cache_read": _clean(cum_run_local_read),
                "cum_run_local_context_tokens": _clean(run_local_denom),
                "observed_accumulated_cache_hit_rate": _clean(cum_read / denom if denom else None),
                "accumulated_cache_hit_rate": _clean(
                    cum_run_local_read / run_local_denom if run_local_denom else None
                ),
            })
    return rows


def _cache_agent_timeline_records(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-(run, request_type) accumulated run-local cache-hit-rate curve.

    Each agent-type stream gets its own warm-start baseline (first request of that
    type), its own within-stream ordinal (1..n), and its own cumulative run-local
    hit rate. The renderer averages these across reps per (condition, request_type).
    """
    rows = []
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for turn in turns:
        run_id = turn.get("run_id")
        if not run_id:
            continue
        request_type = str(turn.get("request_type") or "main-agent")
        by_key.setdefault((str(run_id), request_type), []).append(turn)

    for (run_id, request_type), group in by_key.items():
        warm_start: float | None = None
        cum_run_local_read = 0.0
        cum_write = 0.0
        cum_input = 0.0
        ordinal = 0
        for turn in sorted(group, key=lambda row: row.get("request_index") or 0):
            read = float(turn.get("cache_read") or 0)
            write = float(turn.get("cache_creation") or 0)
            input_tokens = float(turn.get("input_tokens") or 0)
            if warm_start is None:
                warm_start = read
            run_local_read = max(0.0, read - warm_start)
            cum_run_local_read += run_local_read
            cum_write += write
            cum_input += input_tokens
            denom = cum_run_local_read + cum_write + cum_input
            ordinal += 1
            rows.append({
                "run_id": run_id,
                "task": turn.get("task"),
                "condition": turn.get("condition"),
                "rep": turn.get("rep"),
                "request_type": request_type,
                "request_index": turn.get("request_index"),
                "ordinal": ordinal,
                "accumulated_cache_hit_rate": _clean(
                    cum_run_local_read / denom if denom else None
                ),
                "cum_run_local_cache_read": _clean(cum_run_local_read),
                "cum_run_local_context_tokens": _clean(denom),
            })
    return rows


def _context_token_component_records(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    component_specs = [
        ("input tokens", "input_tokens"),
        ("prefix cache read", "cache_read"),
        ("prefix cache write 5m", "cache_creation_5m"),
        ("prefix cache write 1h", "cache_creation_1h"),
        ("output tokens", "output_tokens"),
    ]
    for turn in turns:
        for component, key in component_specs:
            rows.append({
                "run_id": turn.get("run_id"),
                "task": turn.get("task"),
                "condition": turn.get("condition"),
                "rep": turn.get("rep"),
                "request_index": turn.get("request_index"),
                "request_type": turn.get("request_type"),
                "component": component,
                "tokens": turn.get(key) or 0,
            })
    return rows


def _component_records(components: pd.DataFrame) -> list[dict[str, Any]]:
    return _records(components, [
        "run_id", "task", "condition", "rep", "request_index",
        "request_type", "component", "est_tokens", "bytes",
    ])


def _records(df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    if df.empty:
        return []
    present = [c for c in columns if c in df.columns]
    rows = []
    for record in df[present].to_dict(orient="records"):
        rows.append({k: _clean(v) for k, v in record.items()})
    return rows


def _num_series(df: pd.DataFrame, column: str) -> list[float]:
    if df.empty or column not in df.columns:
        return []
    out = []
    for value in df[column].tolist():
        if value is None or pd.isna(value):
            continue
        if isinstance(value, bool):
            out.append(1.0 if value else 0.0)
        else:
            try:
                f = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(f):
                out.append(f)
    return out


def _filter_eq(df: pd.DataFrame, column: str, value: Any) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df.iloc[0:0]
    return df[df[column] == value]


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)


def _safe_factor(value: Any, baseline: Any) -> float | None:
    if value is None or baseline is None:
        return None
    try:
        v = float(value)
        b = float(baseline)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or not math.isfinite(b) or b == 0:
        return None
    return v / b


def _clean(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        f = float(value)
        return f if math.isfinite(f) else None
    return value


def _render_html(data: dict[str, Any], texts: dict[str, Any] | None = None) -> str:
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    texts_json = json.dumps(texts or {}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (_HTML_TEMPLATE
            .replace("__EXPERIMENT_DATA_JSON__", data_json)
            .replace("__CONTEXT_TEXTS_JSON__", texts_json))


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Claude Code · Orchestration Telemetry</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/echarts@6.0.0/dist/echarts.min.js"></script>
  <style>
    :root {
      color-scheme: light;
      --paper:#eceef2; --panel:#ffffff; --ink:#10151d; --muted:#5c6675; --line:#dde2e9;
      --agg:#3b5bdb; --dist:#0c8599; --run:#e8590c;
      --sans:'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
      --mono:'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
      --radius:10px; --maxw:1240px;
    }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--paper); color:var(--ink); font-family:var(--sans); font-size:14px; line-height:1.5; -webkit-font-smoothing:antialiased; }
    a { color:var(--agg); }
    .masthead {
      background:var(--panel); border-bottom:1px solid var(--line);
      border-top:3px solid transparent;
      border-image:linear-gradient(90deg, var(--agg) 0 33.33%, var(--dist) 33.33% 66.66%, var(--run) 66.66% 100%) 1;
    }
    .masthead-inner { max-width:var(--maxw); margin:0 auto; padding:26px 28px 22px; display:flex; gap:24px 32px; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; }
    .eyebrow { font-family:var(--mono); font-size:11.5px; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
    h1 { margin:7px 0 9px; font-size:27px; font-weight:700; letter-spacing:-.01em; }
    .lede { margin:0; color:var(--muted); max-width:780px; }
    #generated-at { font-family:var(--mono); color:var(--ink); }
    .control { display:grid; gap:6px; font-family:var(--mono); font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
    .control.global { min-width:230px; }
    select { font-family:var(--mono); font-size:13px; text-transform:none; letter-spacing:0; color:var(--ink); background:var(--panel); border:1px solid var(--line); border-radius:7px; padding:7px 10px; min-height:36px; }
    select:hover { border-color:var(--scope, var(--agg)); }
    select:focus-visible { outline:2px solid var(--scope, var(--agg)); outline-offset:1px; }
    main { max-width:var(--maxw); margin:0 auto; padding:24px 28px 56px; }
    .band { --scope:var(--agg); margin:0 0 30px; }
    .band-agg { --scope:var(--agg); } .band-dist { --scope:var(--dist); } .band-run { --scope:var(--run); }
    .band-head { display:flex; align-items:center; justify-content:space-between; gap:10px 18px; flex-wrap:wrap; padding:2px 0 12px 14px; border-left:3px solid var(--scope); }
    .band-label { font-size:16px; font-weight:600; }
    .band-no { font-family:var(--mono); color:var(--scope); font-weight:600; margin-right:9px; }
    .band-scope { font-family:var(--mono); font-size:11.5px; letter-spacing:.03em; color:var(--muted); }
    .band-scope.row { padding:0 0 14px 14px; }
    .scope-tag { display:inline-block; font-family:var(--mono); font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--scope); border:1px solid color-mix(in srgb, var(--scope) 32%, var(--line)); background:color-mix(in srgb, var(--scope) 7%, #fff); padding:4px 10px; border-radius:999px; margin:0 0 14px 14px; }
    .kpis { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:14px; }
    .kpi { background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); border-left:3px solid var(--scope); padding:14px 16px; }
    .kpi .label { font-family:var(--mono); font-size:11px; letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }
    .kpi .value { margin-top:7px; font-family:var(--mono); font-size:26px; font-weight:600; letter-spacing:-.01em; }
    .kpi .unit { font-size:14px; color:var(--muted); margin-left:2px; }
    .grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:16px; }
    .stack { display:grid; grid-template-columns:1fr; gap:16px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); padding:14px 16px 16px; min-width:0; }
    .panel-head { display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:34px; margin-bottom:4px; }
    h2 { margin:0; font-size:14.5px; font-weight:600; }
    .control.inline { display:flex; flex-flow:row nowrap; align-items:center; gap:8px; }
    .control.inline select { min-height:32px; padding:5px 9px; font-size:12.5px; }
    .control-group { display:flex; align-items:flex-end; gap:14px; flex-wrap:wrap; }
    .ctx-text-panel { margin-top:12px; border:1px solid var(--line); border-radius:8px; background:#fbfcfe; overflow:hidden; }
    .ctx-text-panel .ctx-head { display:flex; flex-wrap:wrap; align-items:baseline; gap:6px 12px; padding:9px 12px; border-bottom:1px solid var(--line); font-family:var(--mono); font-size:11.5px; color:var(--muted); }
    .ctx-text-panel .ctx-head b { color:var(--ink); font-size:12.5px; }
    .ctx-text-panel .ctx-trunc { color:#b45309; }
    .ctx-text-panel .ctx-body { margin:0; padding:11px 13px; max-height:300px; overflow:auto; white-space:pre-wrap; word-break:break-word; font-family:var(--mono); font-size:11.5px; line-height:1.5; color:var(--ink); }
    .ctx-text-panel .ctx-empty { padding:11px 13px; color:var(--muted); font-family:var(--mono); font-size:11.5px; }
    .chart { width:100%; height:340px; }
    .chart.tall { height:440px; }
    .note { margin:10px 0 0; color:var(--muted); font-size:12px; max-width:920px; }
    .status-key { display:flex; flex-wrap:wrap; gap:7px 16px; margin-top:10px; font-family:var(--mono); font-size:11px; color:var(--muted); }
    .status-key .chip { display:inline-flex; align-items:center; gap:6px; }
    .status-key .sw { width:12px; height:12px; border-radius:3px; border:1px solid var(--line); }
    @media (max-width:980px) {
      .masthead-inner, main { padding-left:16px; padding-right:16px; }
      .grid { grid-template-columns:1fr; }
      .kpis { grid-template-columns:repeat(2,1fr); }
      .chart { height:300px; }
    }
    @media (prefers-reduced-motion:no-preference) {
      .band { animation:rise .5s ease both; }
      .band:nth-of-type(2){animation-delay:.05s} .band:nth-of-type(3){animation-delay:.1s} .band:nth-of-type(4){animation-delay:.15s}
      @keyframes rise { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }
    }
  </style>
</head>
<body>
  <header class="masthead">
    <div class="masthead-inner">
      <div>
        <div class="eyebrow">Claude Code · context &amp; cache experiment</div>
        <h1>Orchestration telemetry</h1>
        <p class="lede">Five orchestration strategies &mdash; single agent, subagents, ralph loop, dynamic workflow, and loop&nbsp;+&nbsp;dynamic &mdash; across coding and research tasks, three runs each. Generated <span id="generated-at"></span>.</p>
      </div>
      <label class="control global">Task &middot; applies to everything
        <select id="task-filter">
          <option value="all">All tasks</option>
          <option value="coding">Coding</option>
          <option value="research">Research</option>
        </select>
      </label>
    </div>
  </header>
  <main>
    <section class="band band-agg">
      <div class="scope-tag">Aggregate &middot; current task</div>
      <div class="kpis" id="kpis"></div>
    </section>

    <section class="band band-agg">
      <div class="band-head">
        <div class="band-label"><span class="band-no">&sect;1</span>Averages across conditions</div>
        <div class="band-scope">Mean of the three reps &middot; follows the Task filter</div>
      </div>
      <div class="grid">
        <article class="panel">
          <div class="panel-head"><h2>Experiment matrix</h2></div>
          <div id="matrix-chart" class="chart"></div>
          <div class="status-key" id="matrix-key"></div>
          <p class="note">Outcome of every task &times; condition &times; rep cell for the selected task. Independent of the metric selectors below.</p>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>Condition comparison</h2>
            <label class="control inline">metric
              <select id="metric-filter">
                <option value="mean_completion_time_s">Mean completion time (s)</option>
                <option value="mean_num_requests">Mean requests</option>
                <option value="mean_total_cost_usd">Mean total cost ($)</option>
                <option value="mean_quality_score">Mean quality score</option>
                <option value="mean_cost_efficiency_score">Mean cost efficiency</option>
                <option value="mean_speedup">Mean coding speedup</option>
                <option value="mean_research_rubric_score">Mean research rubric score</option>
                <option value="mean_peak_prompt_tokens">Mean peak prompt tokens</option>
                <option value="mean_total_cache_read">Mean cache read tokens</option>
                <option value="mean_cache_hit_ratio">Mean cache hit ratio</option>
                <option value="ttft_p95_s">TTFT p95 (s)</option>
                <option value="total_p95_s">Total latency p95 (s)</option>
                <option value="success_rate">Success rate</option>
              </select>
            </label>
          </div>
          <div id="condition-chart" class="chart"></div>
          <p class="note">Each bar averages the selected metric across reps for one condition.</p>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>Overhead vs single agent</h2>
            <label class="control inline">resource
              <select id="overhead-filter">
                <option value="num_requests_factor">Requests</option>
                <option value="completion_time_factor">Completion time</option>
                <option value="total_cost_factor">Total cost</option>
                <option value="peak_prompt_tokens_factor">Peak prompt tokens</option>
                <option value="total_cache_read_factor">Cache reads</option>
                <option value="output_tokens_factor">Output tokens</option>
              </select>
            </label>
          </div>
          <div id="overhead-chart" class="chart"></div>
          <p class="note">How many times more of the chosen resource a strategy spends versus single_agent (1.0&times; line).</p>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>Quality vs cost map</h2></div>
          <div id="efficiency-chart" class="chart"></div>
          <p class="note">One dot per condition: estimated API-equivalent cost (x) against task quality (y). Coding quality is speedup; research quality is the deterministic rubric score. Dot size is mean request count.</p>
        </article>
      </div>
    </section>

    <section class="band band-dist">
      <div class="band-head">
        <div class="band-label"><span class="band-no">&sect;2</span>Across all runs</div>
        <div class="band-scope">Each line or dot is a single run &middot; follows the Task filter</div>
      </div>
      <div class="stack">
        <article class="panel">
          <div class="panel-head"><h2>Prefix Cache Hit Rate (accumulated)</h2>
            <label class="control inline">agent type
              <select id="cache-agent-filter"></select>
            </label>
          </div>
          <div id="cache-chart" class="chart tall"></div>
          <p class="note">Accumulated run-local hit rate, one line per run (not averaged). Color = condition; line style = rep (solid r1, dashed r2, dotted r3). The legend has one entry per condition — toggling it shows/hides all runs of that condition. Pick an agent type above to scope every run to that stream. The run-local rate strips the warm cache inherited on the first request of each agent-type stream. Use the Task filter to isolate coding or research.</p>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>Prefix cache hit rate vs context length</h2>
            <label class="control inline">agent type
              <select id="latency-agent-filter"></select>
            </label>
          </div>
          <div id="latency-chart" class="chart"></div>
          <p class="note">One dot per request of the selected agent type across every run of this task. X = that request's context length (prompt tokens); Y = that request's own prefix cache hit rate (cache read ÷ context length). Dot encodes agent type: main-agent large, subagents small, security-monitor hollow. Color = condition.</p>
        </article>
      </div>
    </section>

    <section class="band band-run">
      <div class="band-head">
        <div class="band-label"><span class="band-no">&sect;3</span>Single run drilldown</div>
        <div class="control-group">
          <label class="control inline">run
            <select id="run-filter"></select>
          </label>
          <label class="control inline">agent type
            <select id="agent-filter"></select>
          </label>
        </div>
      </div>
      <div class="band-scope row">Everything below is one run, split by agent type &middot; pick a run and an agent type above.</div>
      <div class="stack">
        <article class="panel">
          <div class="panel-head"><h2>Per-Run Request Cost Timeline</h2></div>
          <div id="run-chart" class="chart"></div>
          <p class="note">Token accounting (bars, left axis), latency (lines, right axis), and estimated request cost in the tooltip for each request of the selected agent type in the selected run.</p>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>Context Source Breakdown</h2></div>
          <div id="component-chart" class="chart tall"></div>
          <p class="note">Estimated context-window composition per request for the selected agent type, similar to the Claude Code /context breakdown. Top-aligned like a real context window: the root (base system prompt) sits at the top and the window grows downward. Click a segment to see the real text for that part.</p>
          <div class="ctx-text-panel" id="ctx-text-panel"><div class="ctx-empty">Click a stacked segment above to view the text captured for that context part.</div></div>
        </article>
      </div>
    </section>
  </main>
  <script type="application/json" id="context-texts">__CONTEXT_TEXTS_JSON__</script>
  <script>
    const EXPERIMENT_DATA = __EXPERIMENT_DATA_JSON__;
    const CONTEXT_TEXTS = (() => { try { return JSON.parse(document.getElementById("context-texts").textContent || "{}"); } catch (e) { return {}; } })();
    const SANS = "'IBM Plex Sans', system-ui, sans-serif";
    const MONO = "'IBM Plex Mono', ui-monospace, monospace";
    const INK = "#10151d", MUTED = "#5c6675", LINE = "#dde2e9";

    const statusNames = ["missing", "failed", "success", "skipped"];
    const statusGlyph = ["", "✗", "✓", "–"];
    const statusColors = ["#eef1f5", "#e03131", "#2f9e44", "#adb5bd"];
    const conditionColors = {
      single_agent: "#3b5bdb",
      goal: "#2f9e44",
      subagents: "#0c8599",
      ralph_loop: "#e8590c",
      dynamic_workflow: "#7048e8",
      loop_dynamic: "#c2255c",
    };
    const palette = ["#3b5bdb", "#0c8599", "#e8590c", "#7048e8", "#c2255c", "#1098ad", "#f59f00"];
    const repLineTypes = { 1: "solid", 2: "dashed", 3: "dotted" };
    const requestTypeLabels = {
      "main-agent": "main-agent",
      "security-monitor": "security-monitor",
      "workflow-subagent": "workflow-subagent",
      "task-subagent": "task-subagent",
      "web-search-subagent": "web-search-subagent",
      "web-fetch-subagent": "web-fetch-subagent",
      "subagent-internal": "subagent-internal",
    };
    const requestTypeSymbols = {
      "main-agent": "circle",
      "security-monitor": "diamond",
      "workflow-subagent": "triangle",
      "task-subagent": "rect",
      "web-search-subagent": "pin",
      "web-fetch-subagent": "arrow",
      "subagent-internal": "roundRect",
    };
    const sourceColors = {
      "base system prompt": "#3b5bdb",
      "builtin tool definitions": "#1098ad",
      "MCP / extension tool definitions": "#0c8599",
      "CLAUDE.md / project instructions": "#e8590c",
      "skills listing": "#7048e8",
      "invoked skill bodies": "#9775fa",
      "auto memory": "#2f9e44",
      "hooks / system reminders": "#f59f00",
      "user input": "#c2255c",
      "assistant / conversation history": "#868e96",
      "tool results / file reads": "#4263eb",
      "subagent summaries": "#a61e4d",
      "uncategorized context": "#adb5bd",
    };
    const charts = {};
    const TT = {
      confine: true, backgroundColor: "#ffffff", borderColor: LINE, borderWidth: 1, padding: [8, 11],
      textStyle: { color: INK, fontFamily: MONO, fontSize: 12 },
      extraCssText: "box-shadow:0 6px 22px rgba(16,21,29,.12);border-radius:8px;",
    };

    function baseTextStyle() { return { fontFamily: SANS, color: INK }; }
    function axisLabelStyle() { return { fontFamily: MONO, fontSize: 11, color: MUTED }; }
    function yName(name, gap) { return { name: name, nameLocation: "middle", nameGap: gap, nameRotate: 90, nameTextStyle: { fontFamily: MONO, fontSize: 11, color: MUTED } }; }
    function xName(name, gap) { return { name: name, nameLocation: "middle", nameGap: gap, nameTextStyle: { fontFamily: MONO, fontSize: 11, color: MUTED } }; }
    function rightLegend(items) { return { type: "scroll", orient: "vertical", right: 6, top: "middle", icon: "roundRect", itemWidth: 14, itemHeight: 9, itemGap: 9, data: items, textStyle: { fontFamily: MONO, fontSize: 11, color: INK }, pageTextStyle: { color: MUTED }, pageIconColor: MUTED }; }
    function bottomLegend(items) { return { type: "scroll", bottom: 0, icon: "roundRect", itemWidth: 14, itemHeight: 9, data: items, textStyle: { fontFamily: MONO, fontSize: 11, color: INK } }; }
    function fmtAxis(v) { if (v === null || v === undefined || !Number.isFinite(v)) return ""; const a = Math.abs(v); if (a >= 1000000) return (v / 1000000).toFixed(1) + "M"; if (a >= 1000) return (v / 1000).toFixed(0) + "k"; return String(v); }
    function valueAxis(extra) { return Object.assign({ type: "value", axisLabel: Object.assign(axisLabelStyle(), { formatter: fmtAxis }), splitLine: { lineStyle: { color: LINE, type: "dashed" } } }, extra || {}); }
    function catAxis(extra) { return Object.assign({ type: "category", axisLabel: axisLabelStyle(), axisLine: { lineStyle: { color: LINE } }, axisTick: { show: false } }, extra || {}); }

    function fmt(value, digits = 1) {
      if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
      if (Math.abs(value) >= 1000000) return (value / 1000000).toFixed(digits) + "M";
      if (Math.abs(value) >= 1000) return (value / 1000).toFixed(digits) + "k";
      return Number(value).toFixed(digits);
    }
    function fmtUsd(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
      const n = Number(value);
      if (Math.abs(n) < 0.01) return "$" + n.toFixed(4);
      if (Math.abs(n) < 1) return "$" + n.toFixed(3);
      return "$" + n.toFixed(2);
    }
    function fmtMetric(value, metric) {
      if (metric && metric.includes("cost_usd")) return fmtUsd(value);
      if (metric && (metric.includes("ratio") || metric.includes("rate"))) return fmt(value);
      return fmt(value);
    }
    function requestNumber(index) { return Number(index) + 1; }
    function requestTypeLabel(type) { return requestTypeLabels[type] || type || "main-agent"; }
    function agentDotSpec(type) {
      const t = type || "main-agent";
      if (t === "security-monitor") return { size: 7, hollow: true };    // same size as subagents, hollow
      if (t === "main-agent") return { size: 10, hollow: false };        // a bit larger
      return { size: 7, hollow: false };                                 // subagents
    }
    function requestAxisLabel(row) { return `#${requestNumber(row.request_index)}\\n${requestTypeLabel(row.request_type)}`; }
    function prettyDate(iso) { if (!iso) return ""; return String(iso).replace("T", " ").slice(0, 16) + " UTC"; }
    function taskFilter() { return document.getElementById("task-filter").value; }
    function filteredRuns() { const task = taskFilter(); return EXPERIMENT_DATA.runs.filter(r => task === "all" || r.task === task); }
    function filteredTurns() { const task = taskFilter(); return EXPERIMENT_DATA.turns.filter(t => task === "all" || t.task === task); }

    function distAgentTypes() {
      const present = new Set(filteredTurns().map(t => t.request_type || "main-agent"));
      return Object.keys(requestTypeLabels).filter(type => present.has(type));
    }
    function populateDistAgentFilters() {
      const opts = ["all", ...distAgentTypes()];
      for (const id of ["cache-agent-filter", "latency-agent-filter"]) {
        const sel = document.getElementById(id);
        const current = sel.value;
        sel.innerHTML = opts.map(v => `<option value="${v}">${v === "all" ? "all agent types" : requestTypeLabel(v)}</option>`).join("");
        if (opts.includes(current)) sel.value = current;
        else if (opts.includes("main-agent")) sel.value = "main-agent";
        else sel.value = opts[0];
      }
    }

    function initCharts() {
      for (const id of ["matrix-chart", "condition-chart", "overhead-chart", "efficiency-chart", "cache-chart", "latency-chart", "run-chart", "component-chart"]) {
        charts[id] = echarts.init(document.getElementById(id));
      }
      window.addEventListener("resize", () => Object.values(charts).forEach(chart => chart.resize()));
    }

    function renderKpis() {
      const runs = filteredRuns();
      const turns = filteredTurns();
      const cacheHit = avg(runs.map(r => r.cache_hit_ratio));
      const requests = avg(runs.map(r => r.num_requests));
      const totalCost = avg(runs.map(r => r.total_cost_usd));
      const quality = avg(runs.map(r => r.quality_score));
      const task = taskFilter();
      const qualityUnit = task === "coding" ? "×" : (task === "research" ? "/100" : "");
      const items = [
        ["Runs", fmt(runs.length, 0), ""],
        ["Mean requests / run", fmt(requests, 1), ""],
        ["Mean total cost", fmtUsd(totalCost), ""],
        ["Mean quality", quality === null ? "n/a" : fmt(quality, 1), quality === null ? "" : qualityUnit],
        ["Mean cache hit", cacheHit === null ? "n/a" : fmt(cacheHit * 100, 1), cacheHit === null ? "" : "%"],
      ];
      document.getElementById("kpis").innerHTML = items.map(([label, value, unit]) => `
        <div class="kpi"><div class="label">${label}</div><div class="value">${value}<span class="unit">${unit}</span></div></div>
      `).join("");
    }

    function renderMatrix() {
      const task = taskFilter();
      const rows = EXPERIMENT_DATA.matrix_rows.filter(r => task === "all" || r.startsWith(task + " "));
      const cells = EXPERIMENT_DATA.matrix.filter(c => task === "all" || c.task === task);
      const rowIndex = new Map(rows.map((r, i) => [r, i]));
      charts["matrix-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          formatter(params) {
            const cell = cells.find(d => d.condition_index === params.data[0] && rowIndex.get(d.row) === params.data[1]);
            if (!cell) return "";
            return [
              `<b>${cell.row} &middot; ${cell.condition}</b>`,
              `status: ${cell.status}`,
              `run: ${cell.run_id || "n/a"}`,
              `requests: ${cell.num_requests ?? "n/a"}`,
              `cost: ${fmtUsd(cell.total_cost_usd)}`,
              `quality: ${fmt(cell.quality_score)}`,
              `completion: ${fmt(cell.completion_time_s)}s`,
            ].join("<br>");
          }
        },
        grid: { left: 94, right: 16, top: 12, bottom: 64 },
        xAxis: catAxis({ data: EXPERIMENT_DATA.conditions, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
        yAxis: catAxis({ data: rows }),
        visualMap: { show: false, min: 0, max: 3, inRange: { color: statusColors } },
        series: [{
          type: "heatmap",
          data: cells.map(d => [d.condition_index, rowIndex.get(d.row), d.status_code]),
          label: { show: true, color: "#ffffff", fontFamily: MONO, fontSize: 13, fontWeight: 600, formatter: p => statusGlyph[p.data[2]] },
          itemStyle: { borderColor: "#ffffff", borderWidth: 3 },
          emphasis: { itemStyle: { borderColor: INK, borderWidth: 1 } },
        }],
      });
      document.getElementById("matrix-key").innerHTML = [2, 1, 3, 0]
        .map(code => `<span class="chip"><span class="sw" style="background:${statusColors[code]}"></span>${statusNames[code]}</span>`)
        .join("");
    }

    function renderConditionChart() {
      const task = taskFilter();
      const metric = document.getElementById("metric-filter").value;
      const rows = EXPERIMENT_DATA.condition_metrics.filter(r => r.task === task);
      const values = EXPERIMENT_DATA.conditions.map(condition => {
        const row = rows.find(r => r.condition === condition);
        return row ? row[metric] : null;
      });
      const metricLabel = document.getElementById("metric-filter").selectedOptions[0].textContent;
      charts["condition-chart"].setOption({
        textStyle: baseTextStyle(),
        color: [conditionColors.single_agent],
        tooltip: { ...TT, trigger: "axis", valueFormatter: value => fmtMetric(value, metric) },
        grid: { left: 66, right: 20, top: 18, bottom: 72 },
        xAxis: catAxis({ data: EXPERIMENT_DATA.conditions, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
        yAxis: valueAxis(yName(metricLabel, 54)),
        series: [{
          name: metricLabel,
          type: "bar",
          data: values,
          barMaxWidth: 46,
          itemStyle: { color: function (p) { return conditionColors[EXPERIMENT_DATA.conditions[p.dataIndex]] || conditionColors.single_agent; }, borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: "top", fontFamily: MONO, fontSize: 11, color: MUTED, formatter: p => fmtMetric(p.value, metric) },
        }],
      });
    }

    function renderOverheadChart() {
      const task = taskFilter();
      const metric = document.getElementById("overhead-filter").value;
      const rows = EXPERIMENT_DATA.condition_overheads.filter(r => r.task === task);
      const values = EXPERIMENT_DATA.conditions.map(condition => {
        const row = rows.find(r => r.condition === condition);
        return row ? row[metric] : null;
      });
      const metricLabel = document.getElementById("overhead-filter").selectedOptions[0].textContent;
      charts["overhead-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          trigger: "axis",
          formatter(params) {
            return params.map(p => `<b>${p.name}</b><br>${metricLabel}: ${fmt(p.value, 2)}×`).join("<br>");
          }
        },
        grid: { left: 62, right: 26, top: 18, bottom: 72 },
        xAxis: catAxis({ data: EXPERIMENT_DATA.conditions, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
        yAxis: valueAxis({ ...yName("× vs single_agent", 50), min: 0 }),
        series: [{
          name: metricLabel,
          type: "bar",
          data: values,
          barMaxWidth: 46,
          itemStyle: { color: function (p) { return conditionColors[EXPERIMENT_DATA.conditions[p.dataIndex]] || conditionColors.single_agent; }, borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: "top", fontFamily: MONO, fontSize: 11, color: MUTED, formatter: p => p.value === null ? "" : `${fmt(p.value, 2)}×` },
          markLine: {
            symbol: "none",
            data: [{ yAxis: 1 }],
            label: { position: "end", formatter: "1.0× baseline", fontFamily: MONO, fontSize: 10, color: MUTED },
            lineStyle: { type: "dashed", color: MUTED },
          },
        }],
      });
    }

    function renderEfficiencyChart() {
      const task = taskFilter();
      const rows = EXPERIMENT_DATA.condition_metrics
        .filter(r => r.task === task && r.runs > 0 && r.mean_total_cost_usd !== null && r.mean_quality_score !== null);
      const maxRequests = Math.max(1, ...rows.map(r => r.mean_num_requests || 0));
      const qualityAxis = task === "coding" ? "mean speedup" : (task === "research" ? "mean rubric score" : "mean quality score");
      const series = EXPERIMENT_DATA.conditions.map(condition => {
        const row = rows.find(r => r.condition === condition);
        const data = row ? [[
          row.mean_total_cost_usd,
          row.mean_quality_score,
          row.mean_num_requests || 0,
          row.success_rate,
          row.mean_cache_hit_ratio,
          row.mean_cost_efficiency_score,
          condition,
        ]] : [];
        return {
          name: condition,
          type: "scatter",
          data,
          symbolSize(value) { return Math.max(12, Math.min(46, 12 + 34 * ((value[2] || 0) / maxRequests))); },
          label: { show: false },
          itemStyle: { color: conditionColors[condition] || palette[0], opacity: 0.82, borderColor: "#ffffff", borderWidth: 1 },
        };
      });
      charts["efficiency-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          formatter(params) {
            const v = params.data;
            return `<b>${params.seriesName}</b><br>cost: ${fmtUsd(v[0])}<br>quality: ${fmt(v[1])}<br>requests: ${fmt(v[2])}<br>success: ${fmt((v[3] || 0) * 100)}%<br>cache hit: ${fmt((v[4] || 0) * 100)}%<br>quality / $: ${fmt(v[5])}`;
          }
        },
        legend: rightLegend(EXPERIMENT_DATA.conditions),
        grid: { left: 64, right: 152, top: 16, bottom: 50 },
        xAxis: valueAxis(xName("mean total cost ($)", 28)),
        yAxis: valueAxis(yName(qualityAxis, 56)),
        series,
      });
    }

    function renderCacheChart() {
      const task = taskFilter();
      const at = document.getElementById("cache-agent-filter").value || "main-agent";
      const rows = EXPERIMENT_DATA.cache_by_agent.filter(r =>
        (task === "all" || r.task === task) && (at === "all" || (r.request_type || "main-agent") === at));
      // one line per run (and per agent type when showing all) — no averaging across reps
      const groups = new Map();
      for (const r of rows) {
        const type = r.request_type || "main-agent";
        const key = `${r.run_id}|${type}`;
        if (!groups.has(key)) groups.set(key, { task: r.task, condition: r.condition, rep: r.rep, type, points: [] });
        groups.get(key).points.push([r.ordinal, (r.accumulated_cache_hit_rate || 0) * 100]);
      }
      const condOrder = new Map(EXPERIMENT_DATA.conditions.map((c, i) => [c, i]));
      const series = [...groups.values()]
        .sort((a, b) => (condOrder.get(a.condition) - condOrder.get(b.condition)) || (a.rep - b.rep) || a.type.localeCompare(b.type))
        .map(g => {
          const color = conditionColors[g.condition] || palette[0];
          let runLabel = `${g.condition} r${g.rep}`;
          if (task === "all") runLabel = `${g.task} · ${runLabel}`;
          if (at === "all") runLabel = `${runLabel} · ${g.type}`;
          return {
            // All runs of a condition share the legend name, so the legend collapses to
            // one color chip per condition and toggling it shows/hides all its runs.
            name: g.condition,
            type: "line",
            showSymbol: false,
            data: g.points.sort((a, b) => a[0] - b[0]).map(pt => [pt[0], pt[1], runLabel]),
            lineStyle: { width: 2, type: repLineTypes[g.rep] || "solid", color },
            itemStyle: { color },
          };
        });
      const condsPresent = EXPERIMENT_DATA.conditions.filter(c => series.some(s => s.name === c));
      charts["cache-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          trigger: "item",
          formatter(p) {
            const v = p.data || [];
            return `<b>${v[2] || p.seriesName}</b><br>Request # within agent-type stream: ${v[0]}<br>run-local hit rate: ${fmt(v[1], 1)}%`;
          }
        },
        legend: rightLegend(condsPresent),
        grid: { left: 72, right: 230, top: 16, bottom: 62 },
        xAxis: { type: "value", name: "Request # within selected run", min: 1 },
        yAxis: valueAxis({ ...yName("run-local hit rate (%)", 52), min: 0, max: 100 }),
        dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 18 }],
        series,
      }, { notMerge: true });
    }

    function renderLatencyChart() {
      const at = document.getElementById("latency-agent-filter").value || "main-agent";
      const byCondition = new Map();
      for (const turn of filteredTurns()) {
        if (at !== "all" && (turn.request_type || "main-agent") !== at) continue;
        const ctx = turn.prompt_tokens;
        if (ctx === null || ctx === undefined || ctx <= 0) continue;
        const hitRate = 100 * (turn.cache_read || 0) / ctx;
        if (!byCondition.has(turn.condition)) byCondition.set(turn.condition, []);
        const color = conditionColors[turn.condition] || palette[0];
        const spec = agentDotSpec(turn.request_type);
        const item = {
          value: [ctx, hitRate, turn.total_s, turn.run_id, requestNumber(turn.request_index),
                  requestTypeLabel(turn.request_type), turn.ttft_s],
          symbolSize: spec.size,
        };
        // security-monitor renders hollow (outline only); others are filled
        if (spec.hollow) item.itemStyle = { color: "transparent", borderColor: color, borderWidth: 1.6, opacity: 0.95 };
        byCondition.get(turn.condition).push(item);
      }
      const series = EXPERIMENT_DATA.conditions.map(condition => ({
        name: condition,
        type: "scatter",
        data: byCondition.get(condition) || [],
        itemStyle: { color: conditionColors[condition] || palette[0], opacity: 0.72 },
      }));
      charts["latency-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          formatter(params) {
            const v = params.value;
            return `<b>${params.seriesName}</b><br>run: ${v[3]}<br>Request # within selected run: ${v[4]}<br>Request type: ${v[5] || "main-agent"}<br>context length: ${fmt(v[0])}<br>prefix cache hit rate: ${fmt(v[1], 1)}%<br>TTFT: ${fmt(v[6])}s<br>total: ${fmt(v[2])}s`;
          }
        },
        legend: rightLegend(EXPERIMENT_DATA.conditions),
        grid: { left: 64, right: 152, top: 16, bottom: 62 },
        xAxis: valueAxis(xName("context length (tokens)", 30)),
        yAxis: valueAxis({ ...yName("prefix cache hit rate (%)", 52), min: 0, max: 100 }),
        dataZoom: [{ type: "inside" }, { type: "slider", height: 18, bottom: 20 }],
        series,
      });
    }

    function populateRunFilter() {
      const select = document.getElementById("run-filter");
      const runs = filteredRuns();
      const current = select.value;
      select.innerHTML = runs.map(run => `<option value="${run.run_id}">${run.task} / ${run.condition} / r${run.rep}</option>`).join("");
      if (runs.some(run => run.run_id === current)) select.value = current;
    }

    function selectedRunId() {
      const select = document.getElementById("run-filter");
      return select.value || (filteredRuns()[0] && filteredRuns()[0].run_id);
    }

    function populateAgentFilter() {
      const select = document.getElementById("agent-filter");
      const runId = selectedRunId();
      const types = [];
      EXPERIMENT_DATA.turns
        .filter(t => t.run_id === runId)
        .sort((a, b) => a.request_index - b.request_index)
        .forEach(t => { const rt = t.request_type || "main-agent"; if (!types.includes(rt)) types.push(rt); });
      const current = select.value;
      const opts = ["all", ...types];
      select.innerHTML = opts.map(v => `<option value="${v}">${v === "all" ? "all agent types" : requestTypeLabel(v)}</option>`).join("");
      if (opts.includes(current)) select.value = current;
      else if (types.includes("main-agent")) select.value = "main-agent";
      else select.value = opts[0];
    }

    function selectedAgentType() {
      const select = document.getElementById("agent-filter");
      return select.value || "all";
    }

    function renderRunChart() {
      const runId = selectedRunId();
      const at = selectedAgentType();
      const rows = EXPERIMENT_DATA.turns
        .filter(t => t.run_id === runId && (at === "all" || (t.request_type || "main-agent") === at))
        .sort((a, b) => a.request_index - b.request_index);
      // When a single agent type is selected, number its own rounds 1..n (no gaps);
      // in "all" view keep the global index + type to show interleaving.
      const x = rows.map((r, i) => at === "all" ? requestAxisLabel(r) : `#${i + 1}`);
      charts["run-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          trigger: "axis",
          formatter(params) {
            const pos = params[0]?.dataIndex || 0;
            const row = rows[pos] || {};
            return [
              `<b>${runId}</b>`,
              `round: #${pos + 1}${at === "all" ? "" : ` (within ${requestTypeLabel(at)})`}`,
              `global request #: ${row.request_index === null || row.request_index === undefined ? "n/a" : requestNumber(row.request_index)}`,
              `Request type: ${requestTypeLabel(row.request_type)}`,
              `input: ${fmt(row.input_tokens)}`,
              `cache read: ${fmt(row.cache_read)}`,
              `cache write 5m: ${fmt(row.cache_creation_5m)}`,
              `cache write 1h: ${fmt(row.cache_creation_1h)}`,
              `output: ${fmt(row.output_tokens)}`,
              `estimated request cost: ${fmtUsd(row.total_cost_usd)}`,
              `input cost: ${fmtUsd(row.input_cost_usd)}`,
              `cache read cost: ${fmtUsd(row.cache_read_cost_usd)}`,
              `cache write cost: ${fmtUsd((row.cache_creation_5m_cost_usd || 0) + (row.cache_creation_1h_cost_usd || 0))}`,
              `output cost: ${fmtUsd(row.output_cost_usd)}`,
              `TTFT: ${fmt(row.ttft_s)}s`,
              `total: ${fmt(row.total_s)}s`,
            ].join("<br>");
          }
        },
        legend: bottomLegend(["input", "cache read", "cache write 5m", "cache write 1h", "output", "TTFT", "total"]),
        grid: { left: 66, right: 62, top: 16, bottom: 78 },
        xAxis: catAxis({ data: x, axisLabel: { ...axisLabelStyle(), fontSize: 10 } }),
        yAxis: [
          valueAxis(yName("tokens", 58)),
          valueAxis({ ...yName("seconds", 46), splitLine: { show: false } }),
        ],
        series: [
          { name: "input", type: "bar", stack: "tokens", data: rows.map(t => t.input_tokens || 0), itemStyle: { color: "#3b5bdb" } },
          { name: "cache read", type: "bar", stack: "tokens", data: rows.map(t => t.cache_read || 0), itemStyle: { color: "#0c8599" } },
          { name: "cache write 5m", type: "bar", stack: "tokens", data: rows.map(t => t.cache_creation_5m || 0), itemStyle: { color: "#e8590c" } },
          { name: "cache write 1h", type: "bar", stack: "tokens", data: rows.map(t => t.cache_creation_1h || 0), itemStyle: { color: "#f59f00" } },
          { name: "output", type: "bar", stack: "tokens", data: rows.map(t => t.output_tokens || 0), itemStyle: { color: "#7048e8" } },
          {
            name: "TTFT",
            type: "line",
            yAxisIndex: 1,
            data: rows.map(t => ({ value: t.ttft_s, symbol: requestTypeSymbols[t.request_type] || "circle" })),
            itemStyle: { color: "#1098ad" },
            lineStyle: { color: "#1098ad" },
          },
          {
            name: "total",
            type: "line",
            yAxisIndex: 1,
            data: rows.map(t => ({ value: t.total_s, symbol: requestTypeSymbols[t.request_type] || "circle" })),
            itemStyle: { color: "#c2255c" },
            lineStyle: { color: "#c2255c" },
          },
        ],
      });
    }

    function resetContextText() {
      const panel = document.getElementById("ctx-text-panel");
      if (panel) panel.innerHTML = `<div class="ctx-empty">Click a stacked segment above to view the text captured for that context part.</div>`;
    }

    function showContextText(runId, reqIndex, component, requestType, tokens) {
      const panel = document.getElementById("ctx-text-panel");
      if (!panel) return;
      const entry = CONTEXT_TEXTS[`${runId}|${reqIndex}|${component}`] || CONTEXT_TEXTS[`${runId}|*|${component}`];
      const meta = entry
        ? `<span>${fmt(entry.bytes)} bytes${entry.truncated ? " &middot; <span class='ctx-trunc'>preview truncated</span>" : ""}</span>`
        : "";
      const head = `<div class="ctx-head"><b>${component}</b><span>request #${reqIndex === undefined || reqIndex === null ? "?" : requestNumber(reqIndex)}</span><span>${requestTypeLabel(requestType)}</span><span>${fmt(tokens)} est tokens</span>${meta}</div>`;
      if (!entry || !entry.text) {
        panel.innerHTML = head + `<div class="ctx-empty">No captured text for this part (it may be externalized or empty).</div>`;
        return;
      }
      panel.innerHTML = head + `<pre class="ctx-body"></pre>`;
      panel.querySelector(".ctx-body").textContent = entry.text;
    }

    function renderComponentChart() {
      const runId = selectedRunId();
      const at = selectedAgentType();
      resetContextText();
      const rows = EXPERIMENT_DATA.context_source_components
        .filter(c => c.run_id === runId && (at === "all" || (c.request_type || "main-agent") === at))
        .sort((a, b) => a.request_index - b.request_index);
      const indexes = [...new Set(rows.map(r => r.request_index))];
      const typeByIndex = new Map();
      for (const row of rows) {
        if (!typeByIndex.has(row.request_index)) typeByIndex.set(row.request_index, row.request_type);
      }
      // Single agent type -> sequential rounds 1..n; "all" -> global index + type.
      const x = indexes.map((i, pos) => at === "all" ? `#${requestNumber(i)}\\n${requestTypeLabel(typeByIndex.get(i))}` : `#${pos + 1}`);
      const preferred = [
        "base system prompt",
        "builtin tool definitions",
        "MCP / extension tool definitions",
        "CLAUDE.md / project instructions",
        "skills listing",
        "invoked skill bodies",
        "auto memory",
        "hooks / system reminders",
        "user input",
        "assistant / conversation history",
        "tool results / file reads",
        "subagent summaries",
        "uncategorized context",
      ];
      const present = [...new Set(rows.map(r => r.component))];
      const components = preferred.filter(c => present.includes(c)).concat(present.filter(c => !preferred.includes(c)));
      const byKey = new Map(rows.map(r => [`${r.request_index}:${r.component}`, r.est_tokens || 0]));
      charts["component-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          trigger: "axis",
          formatter(params) {
            const pos = params[0]?.dataIndex || 0;
            const request = indexes[pos];
            const lines = [
              `<b>${runId}</b>`,
              `round: #${pos + 1}${at === "all" ? "" : ` (within ${requestTypeLabel(at)})`}`,
              `global request #: ${request === null || request === undefined ? "n/a" : requestNumber(request)}`,
              `Request type: ${requestTypeLabel(typeByIndex.get(request))}`,
            ];
            for (const p of params) if (p.value) lines.push(`${p.marker}${p.seriesName}: ${fmt(p.value)}`);
            return lines.join("<br>");
          }
        },
        legend: rightLegend(components),
        grid: { left: 74, right: 236, top: 52, bottom: 24 },
        xAxis: catAxis({ data: x, position: "top", axisLabel: { ...axisLabelStyle(), fontSize: 10 } }),
        // Top-aligned: the context window starts at its root (base system prompt) at
        // the top (y=0) and grows downward, so the value axis is inverted and the
        // segments stack in canonical /context order (system prompt first/topmost).
        yAxis: valueAxis({ ...yName("estimated context tokens", 62), inverse: true }),
        series: components.map((component, idx) => ({
          name: component,
          type: "bar",
          stack: "context",
          data: indexes.map(i => byKey.get(`${i}:${component}`) || 0),
          itemStyle: { color: sourceColors[component] || palette[idx % palette.length] },
        })),
      }, { notMerge: true });
      const chart = charts["component-chart"];
      chart.off("click");
      chart.on("click", params => {
        const reqIndex = indexes[params.dataIndex];
        showContextText(runId, reqIndex, params.seriesName, typeByIndex.get(reqIndex), params.value);
      });
    }

    function avg(values) {
      const nums = values.filter(v => v !== null && v !== undefined && Number.isFinite(Number(v))).map(Number);
      return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
    }

    function quantile(values, q) {
      const nums = values.filter(v => v !== null && v !== undefined && Number.isFinite(Number(v))).map(Number).sort((a, b) => a - b);
      if (!nums.length) return null;
      const pos = (nums.length - 1) * q;
      const lo = Math.floor(pos);
      const hi = Math.ceil(pos);
      if (lo === hi) return nums[lo];
      return nums[lo] * (hi - pos) + nums[hi] * (pos - lo);
    }

    function renderAll() {
      renderKpis();
      renderMatrix();
      renderConditionChart();
      renderOverheadChart();
      renderEfficiencyChart();
      populateDistAgentFilters();
      renderCacheChart();
      renderLatencyChart();
      populateRunFilter();
      populateAgentFilter();
      renderRunChart();
      renderComponentChart();
    }

    document.getElementById("generated-at").textContent = prettyDate(EXPERIMENT_DATA.generated_at);
    document.getElementById("task-filter").addEventListener("change", renderAll);
    document.getElementById("metric-filter").addEventListener("change", renderConditionChart);
    document.getElementById("overhead-filter").addEventListener("change", renderOverheadChart);
    document.getElementById("cache-agent-filter").addEventListener("change", renderCacheChart);
    document.getElementById("latency-agent-filter").addEventListener("change", renderLatencyChart);
    document.getElementById("run-filter").addEventListener("change", () => {
      populateAgentFilter();
      renderRunChart();
      renderComponentChart();
    });
    document.getElementById("agent-filter").addEventListener("change", () => {
      renderRunChart();
      renderComponentChart();
    });
    initCharts();
    renderAll();
  </script>
</body>
</html>"""
