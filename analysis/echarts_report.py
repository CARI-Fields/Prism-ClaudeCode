from __future__ import annotations

import html as _html
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
# Per-condition accent colors — kept in sync with `conditionColors` in the JS so the
# masthead gradient (a Python-built CSS string) matches the in-chart series colors.
CONDITION_COLORS = {
    "single_agent": "#3b5bdb",
    "goal": "#2f9e44",
    "subagents": "#0c8599",
    "ralph_loop": "#e8590c",
    "dynamic_workflow": "#7048e8",
    "loop_dynamic": "#c2255c",
}
# Default masthead gradient for the combined report (section accents, not conditions).
_DEFAULT_GRADIENT = (
    "linear-gradient(90deg, #3b5bdb 0 33.33%, #0c8599 33.33% 66.66%, #e8590c 66.66% 100%) 1"
)
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
    *,
    conditions: list[str] | None = None,
    tasks: list[str] | None = None,
    page: dict[str, Any] | None = None,
) -> Path:
    """Render one self-contained dashboard.

    ``conditions`` / ``tasks`` restrict the report to a subset (the embedded data is
    pruned to match, so a sub-report file is smaller than the full one). ``page``
    overrides the masthead copy and, when it carries ``task_briefs`` / ``strategies``,
    adds the orientation band that lists each task's verbatim prompt. All three default
    to the full combined report, so existing callers are unaffected.
    """
    return render_combined_report(
        runs, turns, components, html_path, component_texts,
        reports=[{"key": "report", "conditions": conditions, "tasks": tasks, "page": page}],
    )


def render_combined_report(
    runs: pd.DataFrame,
    turns: pd.DataFrame,
    components: pd.DataFrame,
    html_path: str | Path,
    component_texts: pd.DataFrame | None = None,
    *,
    reports: list[dict[str, Any]],
) -> Path:
    """Render ONE self-contained single-page report holding every entry in ``reports``.

    Each entry is ``{key, conditions, tasks, page}``. A switcher in the masthead flips
    between them client-side; every report's data + context-texts are embedded as JSON
    and parsed on demand, so the shared chart code lives once. When ``reports`` has a
    single entry the switcher is hidden — that is the path the existing single-report
    callers (and tests) take via ``render_echarts_report``."""
    html_path = Path(html_path)
    payloads = [
        _report_payload(runs, turns, components, component_texts,
                        r["key"], r.get("conditions"), r.get("tasks"), r.get("page"))
        for r in reports
    ]
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(_render_spa_html(payloads), encoding="utf-8")
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
    conditions: list[str] | None = None,
    tasks: list[str] | None = None,
) -> dict[str, Any]:
    conditions = list(conditions) if conditions is not None else CONDITIONS
    tasks = list(tasks) if tasks is not None else TASKS
    runs = _scope_rows(runs, conditions, tasks)
    turns = _scope_rows(turns, conditions, tasks)
    components = _scope_rows(components, conditions, tasks)
    for df in (runs, turns, components):
        if "rep" in df.columns:
            df["rep"] = pd.to_numeric(df["rep"], errors="coerce").astype("Int64")
    condition_metrics = _condition_metrics(runs, turns, conditions, tasks)
    turn_records = _turn_records(turns)
    # Only surface reps that actually exist in this report's data — a long-horizon
    # report has a single rep, so r2 / r3 must not appear as dead sidebar chips or
    # all-missing matrix rows.
    present_reps = (
        sorted({int(r) for r in runs["rep"].dropna().tolist()})
        if ("rep" in runs.columns and not runs.empty)
        else []
    ) or list(REPS)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "conditions": conditions,
        "tasks": tasks,
        "reps": present_reps,
        "matrix_rows": _matrix_rows(tasks, present_reps),
        "matrix": _matrix(runs, conditions, tasks, present_reps),
        "condition_metrics": condition_metrics,
        "condition_overheads": _condition_overheads(condition_metrics, tasks),
        "runs": _run_records(runs),
        "turns": turn_records,
        "cache_timeline": _cache_timeline_records(turn_records),
        "cache_by_agent": _cache_agent_timeline_records(turn_records),
        "components": _component_records(components),
        "context_source_components": _component_records(components),
        "context_token_components": _context_token_component_records(turn_records),
    }


def _scope_rows(df: pd.DataFrame, conditions: list[str], tasks: list[str]) -> pd.DataFrame:
    """Keep only rows whose condition and task are in the report's subset.

    A copy is always returned so callers can mutate freely. Rows missing either
    column are kept (they predate the split and have nothing to filter on)."""
    out = df.copy()
    if not out.empty and "condition" in out.columns:
        out = out[out["condition"].isin(conditions)]
    if not out.empty and "task" in out.columns:
        out = out[out["task"].isin(tasks)]
    return out.copy()


def _matrix_rows(tasks: list[str], reps: list[int] | None = None) -> list[str]:
    reps = reps if reps is not None else REPS
    return [f"{task} r{rep}" for task in tasks for rep in reps]


def _matrix(runs: pd.DataFrame, conditions: list[str], tasks: list[str],
            reps: list[int] | None = None) -> list[dict[str, Any]]:
    reps = reps if reps is not None else REPS
    rows = []
    matrix_rows = _matrix_rows(tasks, reps)
    for task in tasks:
        for rep in reps:
            row_label = f"{task} r{rep}"
            row_index = matrix_rows.index(row_label)
            for condition_index, condition in enumerate(conditions):
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


def _condition_metrics(
    runs: pd.DataFrame, turns: pd.DataFrame, conditions: list[str], tasks: list[str]
) -> list[dict[str, Any]]:
    rows = []
    for task in ["all", *tasks]:
        for condition in conditions:
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


def _condition_overheads(
    condition_metrics: list[dict[str, Any]], tasks: list[str]
) -> list[dict[str, Any]]:
    rows = []
    for task in ["all", *tasks]:
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
        for turn in sorted(run_turns, key=lambda row: row.get("request_index") or 0):
            cum_read += float(turn.get("cache_read") or 0)
            cum_write += float(turn.get("cache_creation") or 0)
            cum_input += float(turn.get("input_tokens") or 0)
            denom = cum_read + cum_write + cum_input
            rows.append({
                "run_id": run_id,
                "task": turn.get("task"),
                "condition": turn.get("condition"),
                "rep": turn.get("rep"),
                "request_index": turn.get("request_index"),
                "request_type": str(turn.get("request_type") or "main-agent"),
                "cum_cache_read": _clean(cum_read),
                "cum_cache_write": _clean(cum_write),
                "cum_input_tokens": _clean(cum_input),
                "cum_total_context_tokens": _clean(denom),
                "accumulated_cache_hit_rate": _clean(cum_read / denom if denom else None),
            })
    return rows


def _cache_agent_timeline_records(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-(run, request_type) accumulated prefix-cache-hit-rate curve.

    Each agent-type stream gets its own within-stream ordinal (1..n) and its own
    cumulative hit rate over the raw, as-observed token counts — every reported
    cache read is counted, including the warm cache inherited from a shared
    system-prompt prefix. The renderer averages these across reps per
    (condition, request_type).
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
        cum_read = 0.0
        cum_write = 0.0
        cum_input = 0.0
        ordinal = 0
        for turn in sorted(group, key=lambda row: row.get("request_index") or 0):
            cum_read += float(turn.get("cache_read") or 0)
            cum_write += float(turn.get("cache_creation") or 0)
            cum_input += float(turn.get("input_tokens") or 0)
            denom = cum_read + cum_write + cum_input
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
                    cum_read / denom if denom else None
                ),
                "cum_cache_read": _clean(cum_read),
                "cum_context_tokens": _clean(denom),
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


_DEFAULT_PAGE = {
    "eyebrow": "Claude Code · context &amp; cache experiment",
    "title": "Orchestration telemetry",
    "lede": (
        "Five orchestration strategies &mdash; single agent, subagents, ralph loop, "
        "dynamic workflow, and loop&nbsp;+&nbsp;dynamic &mdash; across coding and research "
        "tasks, three runs each. Generated <span id=\"generated-at\"></span>."
    ),
}


def _report_payload(
    runs: pd.DataFrame,
    turns: pd.DataFrame,
    components: pd.DataFrame,
    component_texts: pd.DataFrame | None,
    key: str,
    conditions: list[str] | None,
    tasks: list[str] | None,
    page: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build one report's embed payload: scoped data + context-texts + the masthead copy
    and §0 brief-band HTML the switcher injects when this report becomes active."""
    conditions = list(conditions) if conditions is not None else CONDITIONS
    tasks = list(tasks) if tasks is not None else TASKS
    data = build_dashboard_data(runs, turns, components, conditions=conditions, tasks=tasks)
    # Prune the context-text blob to the same subset so a report only carries the
    # previews for runs it can actually display.
    scoped_texts = _scope_rows(component_texts, conditions, tasks) if component_texts is not None else None
    texts = _context_text_map(scoped_texts)
    page = {**_DEFAULT_PAGE, **(page or {})}
    lede = page["lede"]
    if "generated-at" not in lede:
        lede = f'{lede} Generated <span id="generated-at"></span>.'
    gradient = _masthead_gradient(conditions) if page.get("scope_gradient") else _DEFAULT_GRADIENT
    return {
        "key": key,
        "title": page["title"],
        "eyebrow": page["eyebrow"],
        "lede": lede,
        "gradient": gradient,
        "brief_html": _brief_band_html(page),
        "data": data,
        "texts": texts,
    }


def _json_embed(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _render_spa_html(payloads: list[dict[str, Any]]) -> str:
    blocks = []
    manifest = []
    for p in payloads:
        data_id = f"rpt-{p['key']}-data"
        texts_id = f"rpt-{p['key']}-texts"
        blocks.append(f'<script type="application/json" id="{data_id}">{_json_embed(p["data"])}</script>')
        blocks.append(f'<script type="application/json" id="{texts_id}">{_json_embed(p["texts"])}</script>')
        manifest.append({
            "key": p["key"], "title": p["title"], "eyebrow": p["eyebrow"],
            "lede": p["lede"], "gradient": p["gradient"], "briefHtml": p["brief_html"],
            "dataId": data_id, "textsId": texts_id,
        })
    multi = len(payloads) > 1
    switcher = "".join(
        f'<button type="button" class="switch-tab" data-report="{p["key"]}">{p["title"]}</button>'
        for p in payloads
    )
    return (_HTML_TEMPLATE
            .replace("__REPORT_BLOCKS__", "\n  ".join(blocks))
            .replace("__REPORTS_MANIFEST__", _json_embed(manifest))
            .replace("__SWITCHER__", switcher)
            .replace("__SWITCHER_HIDDEN__", "" if multi else " hidden"))


def _masthead_gradient(conditions: list[str] | None) -> str:
    """A hard-stop gradient built from the report's compared conditions, so the chrome
    encodes which strategies the page is about (single → subagents → workflow, etc.)."""
    colors = [CONDITION_COLORS.get(c, "#5c6675") for c in (conditions or [])] or ["#5c6675"]
    n = len(colors)
    stops = []
    for i, color in enumerate(colors):
        start = round(100 * i / n, 2)
        end = round(100 * (i + 1) / n, 2)
        stops.append(f"{color} {start}% {end}%")
    return f"linear-gradient(90deg, {', '.join(stops)}) 1"


def _brief_band_html(page: dict[str, Any]) -> str:
    """Orientation band: each task as a spec sheet with its verbatim prompt, plus the
    legend of strategies being compared. Returns '' when the page declares neither, so
    the combined report keeps its original layout."""
    briefs = page.get("task_briefs") or []
    strategies = page.get("strategies") or []
    if not briefs and not strategies:
        return ""

    cards = []
    for brief in briefs:
        n = _html.escape(str(brief.get("n", "")))
        task = _html.escape(str(brief.get("task", "")))
        title = _html.escape(str(brief.get("title", "")))
        measures = _html.escape(str(brief.get("measures", "")))
        source = _html.escape(str(brief.get("source", "")))
        prompt = _html.escape(str(brief.get("prompt", "")))
        has_data = brief.get("has_data", True)
        status = (
            '<span class="brief-status live">data captured</span>' if has_data
            else '<span class="brief-status pending">awaiting sweep</span>'
        )
        cards.append(f"""
        <article class="brief">
          <header class="brief-head">
            <span class="brief-no">{n}</span>
            <div class="brief-title">
              <span class="brief-task">{task}</span>
              <h3>{title}</h3>
            </div>
            {status}
          </header>
          <p class="brief-measures">{measures}</p>
          <div class="brief-prompt">
            <div class="brief-prompt-bar"><span class="dot-r"></span><span class="dot-y"></span><span class="dot-g"></span><span class="brief-path">{source}</span></div>
            <pre class="brief-prompt-body">{prompt}</pre>
          </div>
        </article>""")

    strat_html = ""
    if strategies:
        chips = []
        for strat in strategies:
            color = CONDITION_COLORS.get(strat.get("condition", ""), "#5c6675")
            label = _html.escape(str(strat.get("label", strat.get("condition", ""))))
            desc = _html.escape(str(strat.get("desc", "")))
            baseline = '<span class="strat-base">baseline</span>' if strat.get("baseline") else ""
            chips.append(f"""
            <div class="strat">
              <span class="strat-dot" style="background:{color}"></span>
              <div class="strat-text"><div class="strat-line"><b>{label}</b>{baseline}</div><span>{desc}</span></div>
            </div>""")
        strat_html = f"""
        <div class="strat-legend">
          <div class="strat-legend-head">Strategies compared</div>
          <div class="strat-grid">{''.join(chips)}</div>
        </div>"""

    return f"""
    <section class="band band-brief">
      <div class="band-head">
        <div class="band-label"><span class="band-no">&sect;0</span>Tasks &amp; strategies</div>
        <div class="band-scope">What each run is asked to do &middot; the verbatim task prompt and the strategies under comparison</div>
      </div>
      <div class="brief-grid">{''.join(cards)}</div>{strat_html}
    </section>
"""


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
    .switcher { display:flex; gap:7px; flex-wrap:wrap; }
    .switcher[hidden] { display:none; }
    .switch-tab { font-family:var(--mono); font-size:12px; letter-spacing:.02em; color:var(--muted); background:var(--paper); border:1px solid var(--line); border-radius:8px; padding:7px 13px; cursor:pointer; transition:all .12s ease; }
    .switch-tab:hover { color:var(--ink); border-color:var(--muted); }
    .switch-tab.on { color:#fff; background:var(--ink); border-color:var(--ink); }
    .switch-tab:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
    .eyebrow { font-family:var(--mono); font-size:11.5px; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
    h1 { margin:7px 0 9px; font-size:27px; font-weight:700; letter-spacing:-.01em; }
    .lede { margin:0; color:var(--muted); max-width:780px; }
    #generated-at { font-family:var(--mono); color:var(--ink); }
    .control { display:grid; gap:6px; font-family:var(--mono); font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
    .control.global { min-width:230px; }
    select { font-family:var(--mono); font-size:13px; text-transform:none; letter-spacing:0; color:var(--ink); background:var(--panel); border:1px solid var(--line); border-radius:7px; padding:7px 10px; min-height:36px; }
    select:hover { border-color:var(--scope, var(--agg)); }
    select:focus-visible { outline:2px solid var(--scope, var(--agg)); outline-offset:1px; }
    main { max-width:var(--maxw); margin:0 auto; padding:20px 28px 56px; }
    .fstrip { display:flex; flex-wrap:wrap; align-items:center; gap:10px 18px; margin:0 0 14px; padding:10px 12px; background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); }
    .fstrip-global { position:sticky; top:0; z-index:20; }
    .fchunk { display:flex; align-items:center; gap:7px; flex-wrap:wrap; }
    .fchunk-tag { font-family:var(--mono); font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--ink); font-weight:600; }
    .fchunk .ftoggle { font-family:var(--mono); font-size:10px; color:var(--muted); cursor:pointer; }
    .fchunk .ftoggle:hover { color:var(--agg); text-decoration:underline; }
    main { min-width:0; }
    .sidebar { position:sticky; top:14px; align-self:start; max-height:calc(100vh - 28px); overflow:auto; background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); padding:14px 14px 16px; font-family:var(--sans); }
    .sb-top { display:flex; align-items:center; justify-content:space-between; margin:0 0 10px; }
    .sb-title { font-family:var(--mono); font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
    .sb-reset { font-family:var(--mono); font-size:10.5px; letter-spacing:.04em; text-transform:uppercase; color:var(--muted); background:none; border:1px solid var(--line); border-radius:6px; padding:3px 8px; cursor:pointer; }
    .sb-reset:hover { color:var(--ink); border-color:var(--muted); }
    .fgroup { margin:0 0 13px; }
    .fhead { display:flex; align-items:baseline; justify-content:space-between; gap:8px; margin:0 0 6px; }
    .fhead .name { font-family:var(--mono); font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--ink); font-weight:600; }
    .fhead .ftoggle { font-family:var(--mono); font-size:10px; letter-spacing:.03em; color:var(--muted); cursor:pointer; }
    .fhead .ftoggle:hover { color:var(--agg); text-decoration:underline; }
    .chips { display:flex; flex-wrap:wrap; gap:5px; }
    .chip { display:inline-flex; align-items:center; gap:5px; font-family:var(--mono); font-size:11.5px; color:var(--muted); background:var(--paper); border:1px solid var(--line); border-radius:999px; padding:3px 9px; cursor:pointer; user-select:none; transition:all .12s ease; }
    .chip:hover { border-color:var(--muted); color:var(--ink); }
    .chip.on { color:#fff; background:var(--agg); border-color:var(--agg); }
    .chip .dot { width:9px; height:9px; border-radius:50%; flex:none; box-shadow:inset 0 0 0 1px rgba(0,0,0,.12); }
    .chip .gly { font-size:12px; line-height:1; }
    .chip.on .dot { box-shadow:inset 0 0 0 1px rgba(255,255,255,.5); }
    .sb-divider { height:1px; background:var(--line); margin:4px 0 13px; }
    .sb-view .control { margin:0 0 11px; }
    .sb-view select { width:100%; }
    .band { --scope:var(--agg); margin:0 0 30px; }
    .band-agg { --scope:var(--agg); } .band-dist { --scope:var(--dist); } .band-run { --scope:var(--run); }
    .band-head { display:flex; align-items:center; justify-content:space-between; gap:10px 18px; flex-wrap:wrap; padding:2px 0 12px 14px; border-left:3px solid var(--scope); }
    .band-label { font-size:16px; font-weight:600; }
    .band-no { font-family:var(--mono); color:var(--scope); font-weight:600; margin-right:9px; }
    .band-scope { font-family:var(--mono); font-size:11.5px; letter-spacing:.03em; color:var(--muted); }
    .band-scope.row { padding:0 0 14px 14px; }
    .scope-tag { display:inline-block; font-family:var(--mono); font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--scope); border:1px solid color-mix(in srgb, var(--scope) 32%, var(--line)); background:color-mix(in srgb, var(--scope) 7%, #fff); padding:4px 10px; border-radius:999px; margin:0 0 14px 14px; }
    .kpis { display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:14px; }
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
    .control.inline input[type=range] { width:120px; accent-color:var(--muted); cursor:pointer; }
    .control.inline.check { cursor:pointer; gap:6px; }
    .control.inline.check input[type=checkbox] { width:15px; height:15px; accent-color:var(--ink); cursor:pointer; margin:0; }
    .control-group { display:flex; align-items:flex-end; gap:14px; flex-wrap:wrap; }
    .ctx-text-panel { margin-top:12px; border:1px solid var(--line); border-radius:8px; background:#fbfcfe; overflow:hidden; }
    .ctx-text-panel .ctx-head { display:flex; flex-wrap:wrap; align-items:baseline; gap:6px 12px; padding:9px 12px; border-bottom:1px solid var(--line); font-family:var(--mono); font-size:11.5px; color:var(--muted); }
    .ctx-text-panel .ctx-head b { color:var(--ink); font-size:12.5px; }
    .ctx-text-panel .ctx-trunc { color:#b45309; }
    .ctx-text-panel .ctx-body { margin:0; padding:11px 13px; max-height:300px; overflow:auto; white-space:pre-wrap; word-break:break-word; font-family:var(--mono); font-size:11.5px; line-height:1.5; color:var(--ink); }
    .ctx-text-panel .ctx-empty { padding:11px 13px; color:var(--muted); font-family:var(--mono); font-size:11.5px; }
    .drilldown-runs { display:flex; flex-direction:column; gap:18px; }
    .drilldown-run .run-tag { font-family:var(--mono); font-size:11px; color:var(--muted); }
    .drilldown-run .drill-sub { margin:14px 0 4px; font-family:var(--mono); font-size:12px; color:var(--muted); font-weight:600; }
    .chart { width:100%; height:340px; }
    .chart.tall { height:440px; }
    .chart.short { height:290px; }
    .note { margin:10px 0 0; color:var(--muted); font-size:12px; max-width:920px; }
    .status-key { display:flex; flex-wrap:wrap; gap:7px 16px; margin-top:10px; font-family:var(--mono); font-size:11px; color:var(--muted); }
    .status-key .chip { display:inline-flex; align-items:center; gap:6px; }
    .status-key .sw { width:12px; height:12px; border-radius:3px; border:1px solid var(--line); }
    .cache-sub { margin:8px 0 2px; font-size:12.5px; font-weight:600; color:var(--muted); font-family:var(--mono); letter-spacing:.06em; text-transform:uppercase; }
    .cache-sub + .chart { margin-bottom:6px; }
    /* ---- §0 Tasks & strategies orientation band ---- */
    .band-brief { --scope:var(--ink); }
    .brief-grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:16px; }
    .brief { display:flex; flex-direction:column; background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); overflow:hidden; }
    .brief-head { display:flex; align-items:flex-start; gap:12px; padding:15px 16px 11px; border-bottom:1px solid var(--line); }
    .brief-no { font-family:var(--mono); font-size:12px; font-weight:600; color:#fff; background:var(--ink); border-radius:6px; padding:3px 7px; letter-spacing:.04em; flex:none; margin-top:1px; }
    .brief-title { flex:1; min-width:0; }
    .brief-task { display:block; font-family:var(--mono); font-size:10.5px; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
    .brief-title h3 { margin:3px 0 0; font-size:16px; font-weight:600; letter-spacing:-.01em; line-height:1.25; }
    .brief-status { flex:none; font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase; padding:3px 8px; border-radius:999px; border:1px solid var(--line); align-self:flex-start; margin-top:2px; }
    .brief-status.live { color:#2f9e44; border-color:color-mix(in srgb, #2f9e44 36%, var(--line)); background:color-mix(in srgb, #2f9e44 8%, #fff); }
    .brief-status.pending { color:#b45309; border-color:color-mix(in srgb, #e8590c 34%, var(--line)); background:color-mix(in srgb, #e8590c 8%, #fff); }
    .brief-measures { margin:11px 16px 0; color:var(--ink); font-size:13px; line-height:1.45; }
    .brief-prompt { margin:12px 14px 14px; border:1px solid var(--line); border-radius:8px; background:#0f1722; overflow:hidden; }
    .brief-prompt-bar { display:flex; align-items:center; gap:6px; padding:8px 11px; background:#16202e; border-bottom:1px solid #243246; }
    .brief-prompt-bar .dot-r, .brief-prompt-bar .dot-y, .brief-prompt-bar .dot-g { width:9px; height:9px; border-radius:50%; flex:none; }
    .brief-prompt-bar .dot-r { background:#ff5f56; } .brief-prompt-bar .dot-y { background:#ffbd2e; } .brief-prompt-bar .dot-g { background:#27c93f; }
    .brief-path { margin-left:7px; font-family:var(--mono); font-size:11px; color:#8aa0bd; letter-spacing:.02em; }
    .brief-prompt-body { margin:0; padding:13px 14px; max-height:300px; overflow:auto; white-space:pre-wrap; word-break:break-word; font-family:var(--mono); font-size:11.5px; line-height:1.55; color:#d7e1ee; }
    .strat-legend { margin-top:16px; background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); padding:14px 16px 16px; }
    .strat-legend-head { font-family:var(--mono); font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); margin-bottom:11px; }
    .strat-grid { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:14px; }
    .strat { display:flex; gap:9px; }
    .strat-dot { width:11px; height:11px; border-radius:50%; flex:none; margin-top:3px; box-shadow:inset 0 0 0 1px rgba(0,0,0,.12); }
    .strat-text { display:flex; flex-direction:column; min-width:0; }
    .strat-line { display:flex; align-items:center; gap:7px; }
    .strat-text b { font-family:var(--mono); font-size:12.5px; font-weight:600; color:var(--ink); }
    .strat-text span { color:var(--muted); font-size:12px; line-height:1.4; margin-top:2px; }
    .strat-base { font-family:var(--mono); font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); border:1px solid var(--line); border-radius:999px; padding:1px 6px; flex:none; }
    @media (max-width:980px) {
      .brief-grid { grid-template-columns:1fr; }
      .strat-grid { grid-template-columns:1fr; }
      .masthead-inner { padding-left:16px; padding-right:16px; }
      main { padding-left:16px; padding-right:16px; }
      .sidebar { position:static; max-height:none; }
      .sidebar .chips { gap:6px; }
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
  <header class="masthead" id="masthead">
    <div class="masthead-inner">
      <div>
        <div class="eyebrow" id="rpt-eyebrow"></div>
        <h1 id="rpt-title"></h1>
        <p class="lede" id="rpt-lede"></p>
      </div>
      <nav class="switcher" id="switcher"__SWITCHER_HIDDEN__>__SWITCHER__</nav>
    </div>
  </header>
  <main>
      <div class="fstrip fstrip-global">
        <div class="fchunk"><span class="fchunk-tag">Task</span><span class="ftoggle" data-scope="g" data-toggle="task">all</span><div class="chips" id="chips-task"></div></div>
      </div>
      <div id="brief-band-host"></div>
    <section class="band band-agg">
      <div class="scope-tag">Aggregate &middot; current selection</div>
      <div class="kpis" id="kpis"></div>
    </section>

    <section class="band band-agg">
      <div class="band-head">
        <div class="band-label"><span class="band-no">&sect;1</span>Averages across conditions</div>
        <div class="band-scope">Mean across rollouts &middot; the Experiment matrix shows every rollout</div>
      </div>
      <div class="fstrip">
        <div class="fchunk"><span class="fchunk-tag">Feature</span><span class="ftoggle" data-scope="s1" data-toggle="condition">all</span><div class="chips" id="chips-s1-condition"></div></div>
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
            <div class="control-group">
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
                  <option value="success_rate">Success rate</option>
                </select>
              </label>
            </div>
          </div>
          <div id="condition-chart" class="chart"></div>
          <p class="note">Each bar averages the selected metric (set above this chart) across rollouts for one condition. With both tasks selected, bars are grouped by task. Rollout filter does not apply here (these are rollout-averaged); use the run-level panels below for per-rollout views.</p>
        </article>
        <article class="panel" id="overhead-panel">
          <div class="panel-head"><h2>Overhead vs single agent</h2>
            <div class="control-group">
              <label class="control inline" id="overhead-control">resource
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
        <div class="band-scope">Each line or dot is a single run &middot; scoped by this section's Feature / Rollout / Agent</div>
      </div>
      <div class="fstrip">
        <div class="fchunk"><span class="fchunk-tag">Feature</span><span class="ftoggle" data-scope="s2" data-toggle="condition">all</span><div class="chips" id="chips-s2-condition"></div></div>
        <div class="fchunk"><span class="fchunk-tag">Rollout</span><span class="ftoggle" data-scope="s2" data-toggle="rep">all</span><div class="chips" id="chips-s2-rep"></div></div>
        <div class="fchunk"><span class="fchunk-tag">Agent</span><span class="ftoggle" data-scope="s2" data-toggle="agent">all</span><div class="chips" id="chips-s2-agent"></div></div>
      </div>
      <div class="stack">
        <article class="panel">
          <div class="panel-head"><h2>Prefix Cache Hit Rate (accumulated)</h2></div>
          <div id="cache-panels"></div>
          <p class="note">Accumulated prefix-cache hit rate, one line per run (not averaged) — coding and research are shown in separate panels (each shows when its Task is selected in the sidebar). Color = condition; line style = rep (solid r1, dashed r2, dotted r3); marker shape = agent type (main-agent ● circle, each subagent type its own shape, security-monitor ◆ diamond). The legend has one entry per condition — toggling it shows/hides all runs of that condition. Pick an agent type above to scope every run to that stream. Hover any point for the run id, agent type, request index, and cumulative cache read. The rate is computed from the raw, as-observed token counts: every reported cache read is counted, including the warm cache inherited from a shared system-prompt prefix. Note: <code>web-search-subagent</code> / <code>web-fetch-subagent</code> are server-side tool calls that carry no prefix cache (read = write = 0), so they sit flat at 0%; a genuine spawned subagent also starts at 0% on its first request (a cold cache write) and only climbs once it reads that prefix back.</p>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>Prefix cache hit rate vs context length</h2></div>
          <div id="latency-chart" class="chart"></div>
          <p class="note">One dot per request of the selected agent type across every run of this task. X = that request's context length (prompt tokens); Y = that request's own prefix cache hit rate (cache read ÷ context length). Marker shape encodes agent type: main-agent = small circle; each subagent type = its own shape (workflow ▲ triangle, task ■ square, web-search ★ star, web-fetch arrow, internal rounded square); security-monitor = hollow diamond. Color = condition.</p>
        </article>
      </div>
    </section>

    <section class="band band-run">
      <div class="band-head">
        <div class="band-label"><span class="band-no">&sect;3</span>Single run drilldown</div>
      </div>
      <div class="fstrip">
        <div class="fchunk"><span class="fchunk-tag">Feature</span><span class="ftoggle" data-scope="s3" data-toggle="condition">all</span><div class="chips" id="chips-s3-condition"></div></div>
        <div class="fchunk"><span class="fchunk-tag">Rollout</span><span class="ftoggle" data-scope="s3" data-toggle="rep">all</span><div class="chips" id="chips-s3-rep"></div></div>
        <div class="fchunk"><span class="fchunk-tag">Agent</span><span class="ftoggle" data-scope="s3" data-toggle="agent">all</span><div class="chips" id="chips-s3-agent"></div></div>
        <div class="control-group">
          <label class="control inline" id="run-scale-control">bar density
            <input type="range" id="run-scale" min="0" max="100" value="100" title="Compress bar width + gaps for sparse runs">
          </label>
          <label class="control inline">compose by
            <select id="compose-filter">
              <option value="context">/context</option>
              <option value="source">source (detailed)</option>
              <option value="token">token type</option>
            </select>
          </label>
          <label class="control inline">group
            <select id="group-filter">
              <option value="agent">agent type</option>
              <option value="none">none</option>
            </select>
          </label>
          <label class="control inline check"><input type="checkbox" id="hitrate-toggle" checked>cache hit rate</label>
        </div>
      </div>
      <div class="band-scope row">One block per run in this section's Feature &times; Rollout &middot; the Agent chips scope each split. Default: the first feature's rollouts.</div>
      <div id="drilldown-runs" class="drilldown-runs"></div>
    </section>
    </main>
  __REPORT_BLOCKS__
  <script type="application/json" id="reports-manifest">__REPORTS_MANIFEST__</script>
  <script>
    // One self-contained page holding every report; the active one's data + context-texts
    // are parsed on demand and assigned to these (reassignable) globals by activateReport().
    const REPORTS_MANIFEST = (() => { try { return JSON.parse(document.getElementById("reports-manifest").textContent || "[]"); } catch (e) { return []; } })();
    const REPORTS_PARSED = {};
    let ACTIVE_REPORT = null;
    let EXPERIMENT_DATA = { conditions: [], tasks: [], reps: [], matrix_rows: [], matrix: [], condition_metrics: [], condition_overheads: [], runs: [], turns: [], cache_by_agent: [], context_source_components: [], context_token_components: [], generated_at: "" };
    let CONTEXT_TEXTS = {};
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
      "stop-condition-eval": "stop-condition-eval",
      "subagent-internal": "subagent-internal",
    };
    const requestTypeSymbols = {
      "main-agent": "circle",
      "security-monitor": "diamond",
      "workflow-subagent": "triangle",
      "task-subagent": "rect",
      "web-search-subagent": "path://M50,5 L60.6,35.4 L92.8,36.1 L67.1,55.6 L76.4,86.4 L50,68 L23.6,86.4 L32.9,55.6 L7.2,36.1 L39.4,35.4 Z",  // star
      "web-fetch-subagent": "arrow",
      "stop-condition-eval": "pin",
      "subagent-internal": "roundRect",
    };
    const sourceColors = {
      "base system prompt": "#3b5bdb",
      "builtin tool definitions": "#1098ad",
      "MCP / extension tool definitions": "#15aabf",
      "custom agent definitions": "#f76707",
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
    // Full agent-type name wrapped onto two lines for the §3 group axis — keeps the whole
    // label (no abbreviation) but ~halves its width so adjacent narrow bands don't collide.
    function agentWrapLabel(type) {
      const s = requestTypeLabel(type);
      const i = s.lastIndexOf("-");
      return i > 0 ? `${s.slice(0, i)}\\n${s.slice(i + 1)}` : s;
    }
    function agentDotSpec(type) {
      const t = type || "main-agent";
      if (t === "main-agent") return { size: 6, hollow: false };         // solid circle
      if (t === "security-monitor") return { size: 7, hollow: true };    // hollow diamond
      return { size: 8, hollow: false };                                 // subagents — own shape
    }
    function requestAxisLabel(row) { return `#${requestNumber(row.request_index)}\\n${requestTypeLabel(row.request_type)}`; }
    function niceCeil(x) { if (!(x > 0)) return 0; const p = Math.pow(10, Math.floor(Math.log10(x))); const n = x / p; const m = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10; return m * p; }
    // Report-global maxima so the §3 drilldown y-axes stay fixed (and comparable) as you
    // flip through runs. Context length = the input context (excludes output); the run
    // chart's token stack adds output.
    function contextLengthMax() { return niceCeil(Math.max(0, ...EXPERIMENT_DATA.turns.map(t => t.prompt_tokens || 0))); }
    function runTokenMax() { return niceCeil(Math.max(0, ...EXPERIMENT_DATA.turns.map(t => (t.prompt_tokens || 0) + (t.output_tokens || 0)))); }
    // Shared §3 ordering: cluster the per-request x positions by agent type (grouped) or
    // keep raw global order; number rounds 1..n WITHIN each agent-type group; surface the
    // type as a second x-axis label so it sits above the chart, not over the bars.
    function orderedRequests(typeByIndex, rawIndexes, at, groupMode) {
      let indexes = rawIndexes.slice();
      const grouped = groupMode === "agent" && at === "all";
      if (grouped) {
        const typeRank = t => { const k = Object.keys(requestTypeLabels).indexOf(t); return k < 0 ? 999 : k; };
        indexes.sort((a, b) => (typeRank(typeByIndex.get(a)) - typeRank(typeByIndex.get(b))) || (a - b));
      }
      const bands = [];
      indexes.forEach((i, pos) => {
        const t = typeByIndex.get(i);
        const last = bands[bands.length - 1];
        if (last && last.type === t) last.endPos = pos;
        else bands.push({ type: t, startPos: pos, endPos: pos });
      });
      const ordinal = new Array(indexes.length);
      for (const g of bands) { let n = 1; for (let p = g.startPos; p <= g.endPos; p++) ordinal[p] = n++; }
      // annotate (within-group #n + a 2nd type axis) whenever grouped OR a single agent
      // type is selected; ungrouped "all" keeps the interleaved #N + type per tick.
      const annotate = grouped || at !== "all";
      // x-axis labelling: when annotating (grouped or single-agent) mark ONE centred
      // tick per band — the band's TOTAL request count — instead of the start/end round
      // numbers. Ungrouped "all" keeps the global request # at the first + last turn.
      const xLabels = new Array(indexes.length).fill("");
      const showLabel = new Array(indexes.length).fill(false);
      if (annotate) {
        for (const g of bands) {
          const midPos = Math.floor((g.startPos + g.endPos) / 2);
          xLabels[midPos] = `${g.endPos - g.startPos + 1}`;
          showLabel[midPos] = true;
        }
      } else {
        indexes.forEach((i, pos) => { xLabels[pos] = `#${requestNumber(i)}\\n${requestTypeLabel(typeByIndex.get(i))}`; });
        if (indexes.length) { showLabel[0] = true; showLabel[indexes.length - 1] = true; }
      }
      const groupAxisLabels = new Array(indexes.length).fill("");
      if (annotate) for (const g of bands) groupAxisLabels[Math.floor((g.startPos + g.endPos) / 2)] = agentWrapLabel(g.type);
      return { indexes, bands, ordinal, annotate, grouped, xLabels, showLabel, groupAxisLabels };
    }
    // x-axis array for the §3 charts: a primary category axis whose labels are the
    // within-group ordinals, plus (when annotating) a second top axis printing the agent
    // type centered over each group — above the ticks, clear of the plot.
    function groupedXAxis(o, position) {
      // Primary tick axis only (within-group #n). The agent-type labels are drawn as
      // dimension brackets via drawGroupBrackets() so they centre exactly on each band.
      const primary = catAxis({ data: o.indexes.map(String), position: position || "top",
        axisLabel: { ...axisLabelStyle(), fontSize: 10, interval: 0, formatter: (v, i) => (o.showLabel[i] ? o.xLabels[i] : "") } });
      return [primary];
    }
    function bandTintArea(o) {
      // alternating tint per agent-type band — the coloured column the in-plot agent-type
      // tag sits in (see drawGroupBrackets "inside").
      if (!(o.grouped && o.bands.length > 1)) return undefined;
      const cats = o.indexes.map(String);
      const tints = ["rgba(59,91,219,0.09)", "rgba(12,133,153,0.09)"];
      return { silent: true, data: o.bands.map((g, gi) => [
        { xAxis: cats[g.startPos], itemStyle: { color: tints[gi % tints.length] } },
        { xAxis: cats[g.endPos] },
      ]) };
    }
    // Shrink a band label to fit `availPx` of horizontal space: drop the font to a floor,
    // then middle-truncate with an ellipsis. Keeps narrow bands from crowding.
    function fitBandLabel(full, availPx) {
      const CW = 0.62;                              // mono glyph advance ≈ 0.62em
      let fs = 10, txt = full;
      if (full.length * CW * fs > availPx) fs = Math.max(7, Math.floor(availPx / (full.length * CW)));
      const maxChars = Math.floor(availPx / (CW * fs));
      if (full.length > maxChars) {
        if (maxChars >= 3) {
          const keep = maxChars - 1, head = Math.ceil(keep / 2), tail = keep - head;
          txt = full.slice(0, head) + "…" + (tail > 0 ? full.slice(full.length - tail) : "");
        } else {
          txt = full.slice(0, Math.max(1, maxChars));
        }
      }
      return { txt, fs };
    }
    // Label each contiguous agent-type band. position "inside" (the Context Source
    // Breakdown) tags the type just BELOW the plot box — centred under each band's
    // tinted column, in the bottom margin above the legend; "top"/"bottom" (the run
    // chart) draw a |─── type ───►| bracket in the axis margin. Pixel coords, redrawn on resize.
    function drawGroupBrackets(chart, o, position) {
      if (!chart || !o.annotate || !o.bands.length) {
        if (chart) chart.setOption({ graphic: [] }, { replaceMerge: ["graphic"] });
        return;
      }
      const cats = o.indexes.map(String);
      const xAt = c => chart.convertToPixel({ xAxisIndex: 0 }, c);
      const half = cats.length >= 2 ? Math.abs(xAt(cats[1]) - xAt(cats[0])) / 2 : 36;

      if (position === "inside") {
        const topY = chart.convertToPixel({ yAxisIndex: 0 }, 0);
        const botY = chart.convertToPixel({ yAxisIndex: 0 }, contextLengthMax());
        if (!isFinite(topY) || !isFinite(botY)) return;
        const labelY = botY + 14;                   // just BELOW the plot box, in the bottom margin
        const els = [];
        for (const g of o.bands) {
          const L = xAt(cats[g.startPos]) - half;
          const R = xAt(cats[g.endPos]) + half;
          const mid = (L + R) / 2;
          const fit = fitBandLabel(requestTypeLabel(g.type), Math.max(10, (R - L) - 10));
          els.push({ type: "text", silent: true,
            style: { x: mid, y: labelY, text: fit.txt, textAlign: "center", textVerticalAlign: "middle",
              fill: INK, fontFamily: MONO, fontSize: fit.fs, fontWeight: 600,
              backgroundColor: "rgba(255,255,255,0.85)", borderColor: LINE, borderWidth: 1,
              borderRadius: 4, padding: [2, 6] } });
        }
        chart.setOption({ graphic: els }, { replaceMerge: ["graphic"] });
        return;
      }

      const up = position !== "bottom";
      const edgeY = chart.convertToPixel({ yAxisIndex: 0 }, 0);  // plot edge at value 0
      if (!isFinite(edgeY)) return;
      const sgn = up ? -1 : 1;
      const lineY = edgeY + sgn * 34;          // bracket clear of the #n ticks
      const cap = 4, pad = 6;
      const line = (els, x1, y1, x2, y2) => els.push({ type: "line", silent: true,
        shape: { x1, y1, x2, y2 }, style: { stroke: MUTED, lineWidth: 1 } });
      const els = [];
      for (const g of o.bands) {
        const L = xAt(cats[g.startPos]) - half + pad;
        const R = xAt(cats[g.endPos]) + half - pad;
        const mid = (L + R) / 2;
        line(els, L, lineY, R, lineY);                         // span  |--- ... --->|
        line(els, L, lineY - cap, L, lineY + cap);             // left end-cap |
        line(els, R, lineY - cap, R, lineY + cap);             // right end-cap |
        line(els, R - 6, lineY - 3, R, lineY); line(els, R - 6, lineY + 3, R, lineY);  // ►  (right arrow only)
        // agent-type label INLINE on the span — a panel-coloured background masks the
        // line behind the text, giving the |--- main-agent --->| look, fitted to the band.
        const fit = fitBandLabel(requestTypeLabel(g.type), Math.max(10, (R - L) - 22));
        els.push({ type: "text", silent: true,
          style: { x: mid, y: lineY, text: fit.txt, textAlign: "center", textVerticalAlign: "middle",
            fill: INK, fontFamily: MONO, fontSize: fit.fs, fontWeight: 600,
            backgroundColor: "#ffffff", padding: [1, 4] } });
      }
      chart.setOption({ graphic: els }, { replaceMerge: ["graphic"] });
    }
    function prettyDate(iso) { if (!iso) return ""; return String(iso).replace("T", " ").slice(0, 16) + " UTC"; }
    // ---- shared multi-select filter state (empty set for a dimension = "all") ----
    // Per-section selection state. Task is global; Feature/Rollout/Agent are independent per
    // section (s1 = §1 averages, s2 = §2 across-run, s3 = §3 drilldown). An empty set means
    // "show all" (active() fallback). §1 has no rollout/agent (matrix shows every rollout).
    const SEL = {
      task: new Set(),
      s1: { condition: new Set() },
      s2: { condition: new Set(), rep: new Set(), agent: new Set() },
      s3: { condition: new Set(), rep: new Set(), agent: new Set() },
    };
    const agentGlyphs = {
      "main-agent": "●", "security-monitor": "◆", "workflow-subagent": "▲",
      "task-subagent": "■", "web-search-subagent": "★", "web-fetch-subagent": "➤",
      "stop-condition-eval": "⬣", "subagent-internal": "▢",
    };
    // selSet(scope,dim): the Set backing a (scope,dim). scope "g" → the global SEL[dim] (task).
    function selSet(scope, dim) { return scope === "g" ? SEL[dim] : SEL[scope][dim]; }
    function active(scope, dim, val) { const s = selSet(scope, dim); return s.size === 0 || s.has(String(val)); }
    const taskActive = t => active("g", "task", t);
    function selectedTasks() { return EXPERIMENT_DATA.tasks.filter(taskActive); }
    function selectedConditions(scope) { return EXPERIMENT_DATA.conditions.filter(c => active(scope, "condition", c)); }
    function singleAgent(scope) { return SEL[scope].agent.size === 1 ? [...SEL[scope].agent][0] : "all"; }
    // Agent types present given a scope's task(global)+feature+rollout selection — only types that
    // actually appear are offered (single_agent has no subagents; coding has no web-*).
    function presentAgentTypes(scope) {
      const s = SEL[scope];
      const present = new Set(EXPERIMENT_DATA.turns
        .filter(t => taskActive(t.task) && active(scope, "condition", t.condition) && (!s.rep || active(scope, "rep", t.rep)))
        .map(t => t.request_type || "main-agent"));
      return Object.keys(requestTypeLabels).filter(type => present.has(type));
    }
    // runs / turns for a scope — applies only the dimensions that scope owns (§1 has no rep, so
    // the matrix/coverage shows every rollout).
    function runsFor(scope) {
      const s = SEL[scope];
      return EXPERIMENT_DATA.runs.filter(r => taskActive(r.task)
        && (!s.condition || active(scope, "condition", r.condition))
        && (!s.rep || active(scope, "rep", r.rep)));
    }
    function turnsFor(scope) {
      const s = SEL[scope];
      return EXPERIMENT_DATA.turns.filter(t => taskActive(t.task)
        && (!s.condition || active(scope, "condition", t.condition))
        && (!s.rep || active(scope, "rep", t.rep))
        && (!s.agent || active(scope, "agent", t.request_type || "main-agent")));
    }
    // Default-selected state: global task = first (coding-type) task; §1 = all features; §2 = all
    // features/rollouts/present-agents; §3 = FIRST feature + all rollouts + present-agents (so §3
    // defaults to one feature's rollouts, not every run). Empty set still falls back to "show all".
    // Order matters: a scope's feature/rollout must be set before seeding its agent (present types
    // depend on them).
    function seedDefaultFilters() {
      const tasks = EXPERIMENT_DATA.tasks || [], conds = EXPERIMENT_DATA.conditions || [], reps = EXPERIMENT_DATA.reps || [];
      SEL.task = new Set(tasks.length ? [String(tasks[0])] : []);
      SEL.s1.condition = new Set(conds.map(String));
      SEL.s2.condition = new Set(conds.map(String)); SEL.s2.rep = new Set(reps.map(String));
      SEL.s3.condition = new Set(conds.length ? [String(conds[0])] : []); SEL.s3.rep = new Set(reps.map(String));
      SEL.s2.agent = new Set(presentAgentTypes("s2").map(String));
      SEL.s3.agent = new Set(presentAgentTypes("s3").map(String));
    }
    // Every chip row, keyed by (scope,dim). Agent rows scope to presentAgentTypes(scope).
    const STRIPS = [
      { scope: "g",  dim: "task",      id: "chips-task",         values: () => EXPERIMENT_DATA.tasks.slice(),      label: v => v,           dot: null,                                  glyph: null },
      { scope: "s1", dim: "condition", id: "chips-s1-condition", values: () => EXPERIMENT_DATA.conditions.slice(), label: v => v,           dot: v => conditionColors[v] || palette[0], glyph: null },
      { scope: "s2", dim: "condition", id: "chips-s2-condition", values: () => EXPERIMENT_DATA.conditions.slice(), label: v => v,           dot: v => conditionColors[v] || palette[0], glyph: null },
      { scope: "s2", dim: "rep",       id: "chips-s2-rep",       values: () => EXPERIMENT_DATA.reps.map(String),   label: v => "r" + v,     dot: null,                                  glyph: null },
      { scope: "s2", dim: "agent",     id: "chips-s2-agent",     values: () => presentAgentTypes("s2"),            label: requestTypeLabel, dot: null,                                  glyph: v => agentGlyphs[v] || "" },
      { scope: "s3", dim: "condition", id: "chips-s3-condition", values: () => EXPERIMENT_DATA.conditions.slice(), label: v => v,           dot: v => conditionColors[v] || palette[0], glyph: null },
      { scope: "s3", dim: "rep",       id: "chips-s3-rep",       values: () => EXPERIMENT_DATA.reps.map(String),   label: v => "r" + v,     dot: null,                                  glyph: null },
      { scope: "s3", dim: "agent",     id: "chips-s3-agent",     values: () => presentAgentTypes("s3"),            label: requestTypeLabel, dot: null,                                  glyph: v => agentGlyphs[v] || "" },
    ];
    function renderChipGroup(strip) {
      const el = document.getElementById(strip.id); if (!el) return;
      el.innerHTML = strip.values().map(v => {
        const dot = strip.dot ? `<span class="dot" style="background:${strip.dot(v)}"></span>` : "";
        const gly = strip.glyph ? `<span class="gly">${strip.glyph(v)}</span>` : "";
        return `<span class="chip" data-scope="${strip.scope}" data-dim="${strip.dim}" data-val="${v}">${dot}${gly}${strip.label(v)}</span>`;
      }).join("");
    }
    function buildStrips() { for (const s of STRIPS) renderChipGroup(s); syncChips(); }
    // An agent row is rescoped (rebuilt + reseeded to all present) whenever its scope's
    // task/feature/rollout changes — keeps the default-selected look; a deselect-to-one still
    // scopes the §3 single stream.
    function refreshAgentChips(scope) {
      const strip = STRIPS.find(s => s.scope === scope && s.dim === "agent"); if (!strip) return;
      renderChipGroup(strip);
      SEL[scope].agent = new Set(strip.values().map(String));
    }
    function syncChips() {
      document.querySelectorAll(".chip[data-scope]").forEach(el =>
        el.classList.toggle("on", selSet(el.dataset.scope, el.dataset.dim).has(el.dataset.val)));
    }
    function readURL() {
      const h = new URLSearchParams((location.hash || "").replace(/^#/, ""));
      SEL.task = new Set((h.get("task") || "").split(",").filter(Boolean));
      return h.get("report");
    }
    function writeURL() {
      const parts = [];
      if (ACTIVE_REPORT) parts.push(`report=${ACTIVE_REPORT}`);
      if (SEL.task.size) parts.push(`task=${[...SEL.task].join(",")}`);
      history.replaceState(null, "", parts.length ? "#" + parts.join("&") : location.pathname + location.search);
    }
    // Re-render only the section a filter change affects (task = global → everything).
    function renderSection(scope) {
      if (scope === "g") { buildStrips(); renderAll(); return; }
      if (scope === "s1") { renderKpis(); renderMatrix(); renderConditionChart(); renderOverheadChart(); renderEfficiencyChart(); return; }
      if (scope === "s2") { renderCacheChart(); renderLatencyChart(); return; }
      if (scope === "s3") { refreshDrilldown(); return; }
    }
    function commitFilter(scope, dim) {
      if (scope === "g") {                           // task is global: rescope agent rows, full re-render
        refreshAgentChips("s2"); refreshAgentChips("s3");
        syncChips(); writeURL(); renderAll();
        return;
      }
      if (dim !== "agent") refreshAgentChips(scope); // feature/rollout change rescopes this scope's agents
      syncChips(); writeURL(); renderSection(scope);
    }

    // One accumulated-cache panel per task (task names are arbitrary, e.g.
    // coding / research / coding_longhorizon), built from the report's own task list.
    function buildCachePanels() {
      const host = document.getElementById("cache-panels");
      if (!host) return;
      host.innerHTML = EXPERIMENT_DATA.tasks.map(task =>
        `<div id="cache-panel-${task}"><h3 class="cache-sub">${task}</h3>`
        + `<div id="cache-chart-${task}" class="chart short"></div></div>`
      ).join("");
    }

    function initCharts() {
      // Re-runnable: switching reports changes the per-task cache panels, so dispose any
      // existing instances and rebuild from the active report's task list.
      for (const id of Object.keys(charts)) { try { charts[id].dispose(); } catch (e) {} delete charts[id]; }
      _drillSig = null;   // force the §3 per-run panels to rebuild for the newly active report
      buildCachePanels();
      const ids = ["matrix-chart", "condition-chart", "efficiency-chart", "latency-chart"];
      if (overheadApplies()) ids.push("overhead-chart");
      for (const task of EXPERIMENT_DATA.tasks) ids.push("cache-chart-" + task);
      for (const id of ids) {
        const el = document.getElementById(id);
        if (el) charts[id] = echarts.init(el);
      }
    }

    function renderKpis() {
      const runs = runsFor("s1");
      const cacheHit = avg(runs.map(r => r.cache_hit_ratio));
      const requests = avg(runs.map(r => r.num_requests));
      const totalCost = avg(runs.map(r => r.total_cost_usd));
      const quality = avg(runs.map(r => r.quality_score));
      const tasks = selectedTasks();
      const qualityUnit = tasks.length === 1 ? (tasks[0].startsWith("coding") ? "×" : "/100") : "";
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
      const condCols = selectedConditions("s1");
      const colIndex = new Map(condCols.map((c, i) => [c, i]));
      const repOf = label => { const m = String(label).match(/r(\\d+)\\s*$/); return m ? m[1] : null; };
      const rows = EXPERIMENT_DATA.matrix_rows.filter(r => taskActive(r.split(" ")[0]));
      const cells = EXPERIMENT_DATA.matrix.filter(c => taskActive(c.task) && colIndex.has(c.condition) && rows.includes(c.row));
      const rowIndex = new Map(rows.map((r, i) => [r, i]));
      charts["matrix-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          formatter(params) {
            const cell = cells.find(d => colIndex.get(d.condition) === params.data[0] && rowIndex.get(d.row) === params.data[1]);
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
        xAxis: catAxis({ data: condCols, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
        yAxis: catAxis({ data: rows }),
        visualMap: { show: false, min: 0, max: 3, inRange: { color: statusColors } },
        series: [{
          type: "heatmap",
          data: cells.map(d => [colIndex.get(d.condition), rowIndex.get(d.row), d.status_code]),
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
      const metric = document.getElementById("metric-filter").value;
      const metricLabel = document.getElementById("metric-filter").selectedOptions[0].textContent;
      const conds = selectedConditions("s1");
      const tasks = selectedTasks();
      const grouped = tasks.length > 1;
      const series = tasks.map((task, ti) => {
        const rows = EXPERIMENT_DATA.condition_metrics.filter(r => r.task === task);
        return {
          name: task,
          type: "bar",
          barMaxWidth: 46,
          data: conds.map(c => { const row = rows.find(r => r.condition === c); return row ? row[metric] : null; }),
          itemStyle: grouped
            ? { color: palette[ti % palette.length], borderRadius: [4, 4, 0, 0] }
            : { color: p => conditionColors[conds[p.dataIndex]] || conditionColors.single_agent, borderRadius: [4, 4, 0, 0] },
          label: { show: !grouped, position: "top", fontFamily: MONO, fontSize: 11, color: MUTED, formatter: p => fmtMetric(p.value, metric) },
        };
      });
      charts["condition-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: { ...TT, trigger: "axis", valueFormatter: value => fmtMetric(value, metric) },
        legend: grouped ? bottomLegend(tasks) : { show: false },
        grid: { left: 66, right: 20, top: 18, bottom: grouped ? 92 : 72 },
        xAxis: catAxis({ data: conds, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
        yAxis: valueAxis(yName(metricLabel, 54)),
        series,
      }, { notMerge: true });
    }

    // The overhead chart is single_agent-relative; only meaningful for reports that
    // include that baseline. Long-horizon (goal vs ralph_loop) has no baseline, so it
    // is hidden there and the chart is never built or rendered.
    function overheadApplies() { return (EXPERIMENT_DATA.conditions || []).includes("single_agent"); }

    function renderOverheadChart() {
      if (!overheadApplies() || !charts["overhead-chart"]) return;
      const metric = document.getElementById("overhead-filter").value;
      const metricLabel = document.getElementById("overhead-filter").selectedOptions[0].textContent;
      const conds = selectedConditions("s1");
      const tasks = selectedTasks();
      const grouped = tasks.length > 1;
      const series = tasks.map((task, ti) => {
        const rows = EXPERIMENT_DATA.condition_overheads.filter(r => r.task === task);
        return {
          name: task,
          type: "bar",
          barMaxWidth: 46,
          data: conds.map(c => { const row = rows.find(r => r.condition === c); return row ? row[metric] : null; }),
          itemStyle: grouped
            ? { color: palette[ti % palette.length], borderRadius: [4, 4, 0, 0] }
            : { color: p => conditionColors[conds[p.dataIndex]] || conditionColors.single_agent, borderRadius: [4, 4, 0, 0] },
          label: { show: !grouped, position: "top", fontFamily: MONO, fontSize: 11, color: MUTED, formatter: p => p.value === null ? "" : `${fmt(p.value, 2)}×` },
          markLine: ti === 0 ? { symbol: "none", data: [{ yAxis: 1 }], label: { position: "end", formatter: "1.0× baseline", fontFamily: MONO, fontSize: 10, color: MUTED }, lineStyle: { type: "dashed", color: MUTED } } : undefined,
        };
      });
      charts["overhead-chart"].setOption({
        textStyle: baseTextStyle(),
        tooltip: { ...TT, trigger: "axis", formatter(params) { return params.map(p => `<b>${p.name}</b><br>${grouped ? p.seriesName + " · " : ""}${metricLabel}: ${fmt(p.value, 2)}×`).join("<br>"); } },
        legend: grouped ? bottomLegend(tasks) : { show: false },
        grid: { left: 62, right: 26, top: 18, bottom: grouped ? 92 : 72 },
        xAxis: catAxis({ data: conds, axisLabel: { ...axisLabelStyle(), rotate: 26 } }),
        yAxis: valueAxis({ ...yName("× vs single_agent", 50), min: 0 }),
        series,
      }, { notMerge: true });
    }

    function renderEfficiencyChart() {
      const task = selectedTasks()[0] || "coding";
      const conds = selectedConditions("s1");
      const rows = EXPERIMENT_DATA.condition_metrics
        .filter(r => r.task === task && r.runs > 0 && r.mean_total_cost_usd !== null && r.mean_quality_score !== null);
      const maxRequests = Math.max(1, ...rows.map(r => r.mean_num_requests || 0));
      const qualityAxis = (task.startsWith("coding") ? "mean speedup" : (task.startsWith("research") ? "mean rubric score" : "mean quality score")) + " · " + task;
      const series = conds.map(condition => {
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
        legend: rightLegend(conds),
        grid: { left: 64, right: 152, top: 16, bottom: 50 },
        xAxis: valueAxis(xName("mean total cost ($)", 28)),
        yAxis: valueAxis(yName(qualityAxis, 56)),
        series,
      }, { notMerge: true });
    }

    function renderCacheChart() {
      // each task's panel shows when its Task is selected in the sidebar.
      for (const task of EXPERIMENT_DATA.tasks) {
        const show = taskActive(task);
        const panel = document.getElementById("cache-panel-" + task);
        if (panel) panel.style.display = show ? "" : "none";
        const chart = charts["cache-chart-" + task];
        if (show && chart) { renderCacheChartFor(task, "cache-chart-" + task); chart.resize(); }
      }
    }

    function renderCacheChartFor(task, elId) {
      const at = singleAgent("s2");   // "all" unless exactly one agent type is selected
      const rows = EXPERIMENT_DATA.cache_by_agent.filter(r =>
        r.task === task && active("s2", "condition", r.condition) && active("s2", "rep", r.rep)
        && active("s2", "agent", r.request_type || "main-agent"));
      // one line per (run, agent type) — no averaging across reps
      const groups = new Map();
      for (const r of rows) {
        const type = r.request_type || "main-agent";
        const key = `${r.run_id}|${type}`;
        if (!groups.has(key)) groups.set(key, { run_id: r.run_id, condition: r.condition, rep: r.rep, type, points: [] });
        groups.get(key).points.push(r);
      }
      const condOrder = new Map(EXPERIMENT_DATA.conditions.map((c, i) => [c, i]));
      const series = [...groups.values()]
        .sort((a, b) => (condOrder.get(a.condition) - condOrder.get(b.condition)) || (a.rep - b.rep) || a.type.localeCompare(b.type))
        .map(g => {
          const color = conditionColors[g.condition] || palette[0];
          let runLabel = `${g.condition} r${g.rep}`;
          if (at === "all") runLabel = `${runLabel} · ${g.type}`;
          const pts = g.points.slice().sort((a, b) => (a.ordinal || 0) - (b.ordinal || 0));
          const spec = agentDotSpec(g.type);
          return {
            // All runs of a condition share the legend name, so the legend collapses to
            // one color chip per condition and toggling it shows/hides all its runs.
            name: g.condition,
            type: "line",
            showSymbol: true,
            // main-agent = solid circle; each subagent type = its own shape; security-monitor = diamond
            symbol: requestTypeSymbols[g.type] || "circle",
            symbolSize: spec.size,
            // Each point is an object so the tooltip can surface the underlying run details.
            data: pts.map(r => ({
              value: [r.ordinal, (r.accumulated_cache_hit_rate || 0) * 100],
              run_id: g.run_id,
              condition: g.condition,
              rep: g.rep,
              type: g.type,
              request_index: r.request_index,
              cum_read: r.cum_cache_read,
              cum_ctx: r.cum_context_tokens,
              label: runLabel,
            })),
            lineStyle: { width: 2, type: repLineTypes[g.rep] || "solid", color },
            itemStyle: { color },
          };
        });
      const condsPresent = EXPERIMENT_DATA.conditions.filter(c => series.some(s => s.name === c));
      charts[elId].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          trigger: "item",
          formatter(p) {
            const d = p.data || {};
            const x = (p.value && p.value[0]) || 0;
            const y = (p.value && p.value[1]) || 0;
            const read = d.cum_read != null ? fmt(d.cum_read) : "0";
            const ctx = d.cum_ctx != null ? fmt(d.cum_ctx) : "0";
            return `<b>${d.label || p.seriesName}</b>`
              + `<br>run: ${d.run_id || "—"}`
              + `<br>agent type: ${d.type || "main-agent"}`
              + `<br>request # in stream: ${x}`
              + `<br>accumulated hit rate: ${fmt(y, 1)}%`
              + `<br>cumulative cache read: ${read} of ${ctx} context tokens`;
          }
        },
        legend: rightLegend(condsPresent),
        grid: { left: 72, right: 230, top: 16, bottom: 62 },
        xAxis: { type: "value", name: "Request # within selected run", min: 1 },
        yAxis: valueAxis({ ...yName("prefix cache hit rate (%)", 52), min: 0, max: 100 }),
        dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 18 }],
        series,
      }, { notMerge: true });
    }

    function renderLatencyChart() {
      const byCondition = new Map();
      for (const turn of turnsFor("s2")) {
        const ctx = turn.prompt_tokens;
        if (ctx === null || ctx === undefined || ctx <= 0) continue;
        const hitRate = 100 * (turn.cache_read || 0) / ctx;
        if (!byCondition.has(turn.condition)) byCondition.set(turn.condition, []);
        const color = conditionColors[turn.condition] || palette[0];
        const spec = agentDotSpec(turn.request_type);
        const item = {
          value: [ctx, hitRate, turn.total_s, turn.run_id, requestNumber(turn.request_index),
                  requestTypeLabel(turn.request_type), turn.ttft_s],
          // main-agent stays a circle; each subagent type gets its own shape; security-monitor a diamond
          symbol: requestTypeSymbols[turn.request_type] || "circle",
          symbolSize: spec.size,
        };
        // security-monitor renders hollow (outline only); others are filled
        if (spec.hollow) item.itemStyle = { color: "transparent", borderColor: color, borderWidth: 1.6, opacity: 0.95 };
        byCondition.get(turn.condition).push(item);
      }
      const series = selectedConditions("s2").map(condition => ({
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
        legend: rightLegend(selectedConditions("s2")),
        grid: { left: 64, right: 152, top: 16, bottom: 62 },
        xAxis: valueAxis(xName("context length (tokens)", 30)),
        yAxis: valueAxis({ ...yName("prefix cache hit rate (%)", 52), min: 0, max: 100 }),
        dataZoom: [{ type: "inside" }, { type: "slider", height: 18, bottom: 20 }],
        series,
      }, { notMerge: true });
    }

    // Bar-density control shared by the two §3 (single-run) charts. Sparse runs render fat
    // bars with wide gaps; shrinking the plot width compresses bar width AND inter-bar gaps
    // together (ECharts auto-distributes within the grid), so a few requests can be packed to
    // the fine density of a long-horizon run. Runs at/above DENSE_N are already fine, so the
    // slider is hidden and the plot keeps its full default width. Returns the grid.right to use.
    const DENSE_N = 40;
    function densityGridRight(chartId, n, gridLeft, defaultRight) {
      const showScale = n > 1 && n < DENSE_N;
      const scaleCtl = document.getElementById("run-scale-control");
      if (scaleCtl) scaleCtl.style.display = showScale ? "" : "none";
      if (!showScale) return defaultRight;
      const slider = document.getElementById("run-scale");
      const s = slider ? Math.min(1, Math.max(0, Number(slider.value) / 100)) : 1;  // 1 = full width, 0 = densest
      const chart = charts[chartId];
      const W = chart ? chart.getWidth() : 0;
      if (!(W > 0)) return defaultRight;
      const fullPlot = Math.max(40, W - gridLeft - defaultRight);
      const densePlot = fullPlot * (n / DENSE_N);                 // width n bars would get in a full DENSE_N chart
      const plot = densePlot + s * (fullPlot - densePlot);        // interpolate dense <-> full
      return Math.max(defaultRight, Math.round(W - gridLeft - plot));
    }

    function renderRunChart(runId, key) {
      const at = singleAgent("s3");
      const groupMode = (document.getElementById("group-filter") || {}).value || "agent";
      const turnRows = EXPERIMENT_DATA.turns
        .filter(t => t.run_id === runId && active("s3", "agent", t.request_type || "main-agent"))
        .sort((a, b) => a.request_index - b.request_index);
      const typeByIndex = new Map();
      for (const t of turnRows) if (!typeByIndex.has(t.request_index)) typeByIndex.set(t.request_index, t.request_type);
      const turnByIndex = new Map(turnRows.map(t => [t.request_index, t]));
      const rawIndexes = [...new Set(turnRows.map(t => t.request_index))].sort((a, b) => a - b);
      // Same grouping/annotation as Context Source Breakdown, driven by the shared group toggle.
      const o = orderedRequests(typeByIndex, rawIndexes, at, groupMode);
      const rows = o.indexes.map(i => turnByIndex.get(i) || {});
      const tintArea = bandTintArea(o);
      const gridRight = densityGridRight("run-chart-" + key, o.indexes.length, 66, 62);
      charts["run-chart-" + key].setOption({
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          trigger: "axis",
          formatter(params) {
            const pos = params[0]?.dataIndex || 0;
            const row = rows[pos] || {};
            return [
              `<b>${runId}</b>`,
              o.annotate ? `round: ${o.ordinal[pos]} (within ${requestTypeLabel(row.request_type)})`
                         : `position: #${pos + 1}`,
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
        grid: { left: 66, right: gridRight, top: 16, bottom: 120 },
        xAxis: groupedXAxis(o, "bottom"),
        yAxis: [
          valueAxis({ ...yName("tokens", 58), min: 0, max: runTokenMax() }),
          valueAxis({ ...yName("seconds", 46), splitLine: { show: false } }),
        ],
        series: [
          { name: "input", type: "bar", stack: "tokens", xAxisIndex: 0, data: rows.map(t => t.input_tokens || 0), itemStyle: { color: "#3b5bdb" }, markArea: tintArea },
          { name: "cache read", type: "bar", stack: "tokens", xAxisIndex: 0, data: rows.map(t => t.cache_read || 0), itemStyle: { color: "#0c8599" } },
          { name: "cache write 5m", type: "bar", stack: "tokens", xAxisIndex: 0, data: rows.map(t => t.cache_creation_5m || 0), itemStyle: { color: "#e8590c" } },
          { name: "cache write 1h", type: "bar", stack: "tokens", xAxisIndex: 0, data: rows.map(t => t.cache_creation_1h || 0), itemStyle: { color: "#f59f00" } },
          { name: "output", type: "bar", stack: "tokens", xAxisIndex: 0, data: rows.map(t => t.output_tokens || 0), itemStyle: { color: "#7048e8" } },
          {
            name: "TTFT",
            type: "line",
            xAxisIndex: 0,
            yAxisIndex: 1,
            data: rows.map(t => ({ value: t.ttft_s, symbol: requestTypeSymbols[t.request_type] || "circle" })),
            itemStyle: { color: "#1098ad" },
            lineStyle: { color: "#1098ad" },
          },
          {
            name: "total",
            type: "line",
            xAxisIndex: 0,
            yAxisIndex: 1,
            data: rows.map(t => ({ value: t.total_s, symbol: requestTypeSymbols[t.request_type] || "circle" })),
            itemStyle: { color: "#c2255c" },
            lineStyle: { color: "#c2255c" },
          },
        ],
      });
      drawGroupBrackets(charts["run-chart-" + key], o, "bottom");
    }

    function resetContextText(hint, panelId) {
      const panel = document.getElementById(panelId || "ctx-text-panel");
      const msg = hint || "Click a stacked segment above to view the text captured for that context part.";
      if (panel) panel.innerHTML = `<div class="ctx-empty">${msg}</div>`;
    }

    function showContextText(runId, reqIndex, component, requestType, tokens, panelId) {
      const panel = document.getElementById(panelId || "ctx-text-panel");
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

    // Two ways to compose the Context Source Breakdown: by source category (the
    // /context-style breakdown, click-to-text) or by token billing bucket (input /
    // cache read / cache write — the tokens actually sent each request, output excluded).
    const COMPONENT_MODES = {
      context: {
        // Claude Code's /context buckets, mirrored exactly: System prompt / System tools /
        // MCP tools / Custom agents / Memory files / Skills / Messages. Matches the order
        // and split of `/context` (Free space — the unused window — is not part of a
        // per-request composition, so it is omitted). Note like /context: Skills counts
        // only the skill LISTING; an invoked skill body counts under Messages.
        datasetKey: "context_source_components",
        valueField: "est_tokens",
        bucketOf: c => ({
          "base system prompt": "System prompt",
          "builtin tool definitions": "System tools",
          "MCP / extension tool definitions": "MCP tools",
          "custom agent definitions": "Custom agents",
          "auto memory": "Memory files",
          "CLAUDE.md / project instructions": "Memory files",
          "skills listing": "Skills",
          "invoked skill bodies": "Messages",
          "hooks / system reminders": "Messages",
          "user input": "Messages",
          "assistant / conversation history": "Messages",
          "tool results / file reads": "Messages",
          "subagent summaries": "Messages",
          "uncategorized context": "Messages",
        }[c] ?? "Messages"),
        order: ["System prompt", "System tools", "MCP tools", "Custom agents", "Memory files", "Skills", "Messages"],
        colors: { "System prompt": "#3b5bdb", "System tools": "#0c8599", "MCP tools": "#15aabf",
          "Custom agents": "#f76707", "Memory files": "#2f9e44",
          "Skills": "#7048e8", "Messages": "#495057" },
        yName: "context length (tokens)",
        legendReserve: 150,
        clickable: false,
      },
      source: {
        datasetKey: "context_source_components",
        valueField: "est_tokens",
        bucketOf: c => c,
        order: [
          "base system prompt",
          "builtin tool definitions",
          "MCP / extension tool definitions",
          "custom agent definitions",
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
        ],
        colors: sourceColors,
        yName: "context length (tokens)",
        legendReserve: 272,
        clickable: true,
      },
      token: {
        datasetKey: "context_token_components",
        valueField: "tokens",
        // Fold the 5m / 1h cache writes into one "cache write" bucket; drop output tokens
        // (generated, not part of the input context). bucketOf -> null means "exclude".
        bucketOf: c => ({
          "input tokens": "input",
          "prefix cache read": "cache read",
          "prefix cache write 5m": "cache write",
          "prefix cache write 1h": "cache write",
        }[c] ?? null),
        order: ["input", "cache read", "cache write"],
        colors: { "input": "#3b5bdb", "cache read": "#0c8599", "cache write": "#e8590c" },
        yName: "context length (tokens)",
        legendReserve: 140,
        clickable: false,
      },
    };
    const COMPONENT_NOTES = {
      context: "Per-request context window in Claude Code's /context categories, mirrored exactly — System prompt · System tools · MCP tools · Custom agents · Memory files · Skills · Messages — aggregated up from our finer source split (Free space, the unused window, is omitted: this is what's USED, not the whole window). Bucketing matches /context: builtin tool defs → System tools, MCP/extension tool defs → MCP tools, the agent registry → Custom agents, the skill LISTING → Skills, while an invoked skill BODY counts under Messages (as in /context). Each bar's TOTAL is the exact context length (input + cache read + cache write, from the API usage); the y-axis is fixed to the largest context across runs so they compare. The split is a data-calibrated estimate (per-category tokens-per-byte fit to the exact totals; /context is itself an estimate). Switch compose to 'source (detailed)' to split Messages into user input / conversation / tool results / subagent summaries, or to 'token type' for the measured input/cache-read/cache-write decomposition.",
      source: "Per-request context composition by source, like Claude Code's /context but FINER (Messages split into user input / conversation / tool results / subagent summaries; System tools split into builtin vs MCP). Switch compose to '/context' for Claude Code's exact buckets. Each bar's TOTAL height is the exact context length (input + cache read + cache write, from the API usage); the y-axis is fixed to the largest context across runs so they compare. The per-source SPLIT is a data-calibrated estimate — per-category tokens-per-byte fit to the exact totals — not a measured per-category count (Claude Code's /context is itself an estimate; an exact split needs the count_tokens API per section). For the measured decomposition, switch compose to 'token type'. Stacked top→bottom in canonical context order: the stable prefix (system prompt, tool definitions) at the top, the most recent content (conversation, tool results) toward the bottom — categories interleaved in the real request appear as separate blocks. Click a segment to see its captured text.",
      token: "Per-request context length by token bucket: input + prefix cache read + prefix cache write (5m+1h summed) — the MEASURED decomposition from each request's usage (exact, not estimated). Output tokens are excluded (the model's reply, not input context). The y-axis is fixed to the largest context across runs so they compare. Group = agent type clusters requests by who made them (with the type labelled above the x-axis); group = none keeps raw request order.",
    };

    // §3 renders one block per selected run, stacked top to bottom. The run set follows the
    // sidebar Task / Feature / Rollout chips; the DOM + chart instances are rebuilt only when
    // that set changes (refreshDrilldown), and every block re-renders on any control change.
    let _drillSig = null;
    let _drillRuns = [];
    function buildDrilldownPanels(runs) {
      const host = document.getElementById("drilldown-runs");
      if (!host) return runs;
      for (const id of Object.keys(charts)) {
        if (id.startsWith("run-chart-") || id.startsWith("component-chart-")) {
          try { charts[id].dispose(); } catch (e) {}
          delete charts[id];
        }
      }
      host.innerHTML = runs.length
        ? runs.map((run, i) => `
          <article class="panel drilldown-run">
            <div class="panel-head"><h2>${run.task} / ${run.condition} / r${run.rep}</h2><span class="run-tag">${run.run_id}</span></div>
            <h3 class="drill-sub">Per-Run Request Cost Timeline</h3>
            <div id="run-chart-${i}" class="chart"></div>
            <h3 class="drill-sub">Context Source Breakdown</h3>
            <div id="component-chart-${i}" class="chart tall"></div>
            <p class="note" id="component-note-${i}"></p>
            <div class="ctx-text-panel" id="ctx-text-panel-${i}"><div class="ctx-empty">Click a stacked segment above to view the text captured for that context part.</div></div>
          </article>`).join("")
        : `<p class="note">No runs match the current Task / Feature / Rollout selection.</p>`;
      runs.forEach((run, i) => {
        const rc = document.getElementById("run-chart-" + i); if (rc) charts["run-chart-" + i] = echarts.init(rc);
        const cc = document.getElementById("component-chart-" + i); if (cc) charts["component-chart-" + i] = echarts.init(cc);
      });
      return runs;
    }
    function renderDrilldown() {
      const composeMode = (document.getElementById("compose-filter") || {}).value || "context";
      const groupMode = (document.getElementById("group-filter") || {}).value || "agent";
      const cfg = COMPONENT_MODES[composeMode] || COMPONENT_MODES.source;
      _drillRuns.forEach((run, i) => {
        renderRunChart(run.run_id, i);
        renderStackedContextChart(cfg, composeMode, groupMode, run.run_id, i);
      });
    }
    function refreshDrilldown() {
      const runs = runsFor("s3");
      const sig = runs.map(r => r.run_id).join("|");
      if (sig !== _drillSig) { _drillRuns = buildDrilldownPanels(runs); _drillSig = sig; }
      renderDrilldown();
    }

    function renderStackedContextChart(cfg, composeMode, groupMode, runId, key) {
      const at = singleAgent("s3");
      resetContextText(cfg.clickable ? null : "Text preview is available in the source view.", "ctx-text-panel-" + key);
      const rows = (EXPERIMENT_DATA[cfg.datasetKey] || [])
        .filter(c => c.run_id === runId && active("s3", "agent", c.request_type || "main-agent"))
        .map(c => ({ run_index: c.request_index, request_type: c.request_type, bucket: cfg.bucketOf(c.component), value: c[cfg.valueField] || 0 }))
        .filter(c => c.bucket !== null)
        .sort((a, b) => a.run_index - b.run_index);
      const typeByIndex = new Map();
      for (const row of rows) {
        if (!typeByIndex.has(row.run_index)) typeByIndex.set(row.run_index, row.request_type);
      }
      const rawIndexes = [...new Set(rows.map(r => r.run_index))].sort((a, b) => a - b);
      const o = orderedRequests(typeByIndex, rawIndexes, at, groupMode);
      const indexes = o.indexes;
      const present = [...new Set(rows.map(r => r.bucket))];
      const components = cfg.order.filter(c => present.includes(c)).concat(present.filter(c => !cfg.order.includes(c)));
      // Sum by (request, bucket) — token mode folds two cache-write TTLs into one bucket.
      const byKey = new Map();
      for (const r of rows) {
        const key = `${r.run_index}:${r.bucket}`;
        byKey.set(key, (byKey.get(key) || 0) + r.value);
      }
      const tintArea = bandTintArea(o);
      // Per-request prefix cache hit rate (cache read ÷ context length), overlaid as a
      // line on a right-hand 0–100% axis (inverted: 100% at the bottom). Toggleable via
      // the "cache hit rate" switch in the panel head — off drops the line + right axis.
      const HIT_NAME = "prefix cache hit rate";
      const HIT_COLOR = "#f03e3e";
      const showHit = (document.getElementById("hitrate-toggle") || {}).checked !== false;
      const hitByIndex = new Map();
      if (showHit) for (const t of (EXPERIMENT_DATA.turns || [])) {
        if (String(t.run_id) !== String(runId)) continue;
        const denom = t.prompt_tokens || 0;
        hitByIndex.set(t.request_index, denom ? (t.cache_read || 0) / denom * 100 : null);
      }
      const hitData = indexes.map(i => { const v = hitByIndex.get(i); return (v === null || v === undefined) ? null : v; });
      const barSeries = components.map((component, idx) => ({
        name: component,
        type: "bar",
        stack: "context",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: indexes.map(i => byKey.get(`${i}:${component}`) || 0),
        itemStyle: { color: cfg.colors[component] || palette[idx % palette.length] },
        markArea: idx === 0 ? tintArea : undefined,
      }));
      const hitSeries = {
        name: HIT_NAME, type: "line", xAxisIndex: 0, yAxisIndex: 1, data: hitData,
        connectNulls: true, symbol: "circle", symbolSize: 4,
        lineStyle: { color: HIT_COLOR, width: 2 }, itemStyle: { color: HIT_COLOR },
        emphasis: { disabled: true }, z: 12,
      };
      // [0] context bars — top-aligned (root at y=0, growing downward), fixed to the
      // report-global max context length; [1] the cache hit-rate line, inverted so 100%
      // sits at the BOTTOM and 0 at the top, reading with the top-anchored bars.
      const leftAxis = valueAxis({ ...yName(cfg.yName, 62), inverse: true, min: 0, max: contextLengthMax() });
      const rightAxis = valueAxis({ min: 0, max: 100, inverse: true, position: "right", splitLine: { show: false },
        axisLabel: { ...axisLabelStyle(), formatter: v => v + "%" } });
      const componentOption = {
        textStyle: baseTextStyle(),
        tooltip: {
          ...TT,
          trigger: "axis",
          formatter(params) {
            const pos = params[0]?.dataIndex || 0;
            const request = indexes[pos];
            const lines = [
              `<b>${runId}</b>`,
              o.annotate ? `round: ${o.ordinal[pos]} (within ${requestTypeLabel(typeByIndex.get(request))})`
                         : `position: #${pos + 1}`,
              `global request #: ${request === null || request === undefined ? "n/a" : requestNumber(request)}`,
              `Request type: ${requestTypeLabel(typeByIndex.get(request))}`,
            ];
            for (const p of params) {
              if (p.seriesName === HIT_NAME) {
                if (p.value !== null && p.value !== undefined) lines.push(`${p.marker}${p.seriesName}: ${fmt(p.value, 1)}%`);
              } else if (p.value) {
                lines.push(`${p.marker}${p.seriesName}: ${fmt(p.value)}`);
              }
            }
            return lines.join("<br>");
          }
        },
        legend: bottomLegend(showHit ? components.concat([HIT_NAME]) : components),
        grid: { left: 74, right: densityGridRight("component-chart-" + key, o.indexes.length, 74, showHit ? 60 : 24), top: 48, bottom: 66 },
        xAxis: groupedXAxis(o),
        yAxis: showHit ? [leftAxis, rightAxis] : [leftAxis],
        series: showHit ? barSeries.concat([hitSeries]) : barSeries,
      };
      charts["component-chart-" + key].setOption(componentOption, { notMerge: true });
      const noteEl = document.getElementById("component-note-" + key);
      if (noteEl) noteEl.textContent = (COMPONENT_NOTES[composeMode] || COMPONENT_NOTES.source)
        + (showHit ? " The red line (right axis, inverted — 100% at the bottom) overlays each request's prefix cache hit rate (cache read ÷ context length)." : "");
      const chart = charts["component-chart-" + key];
      drawGroupBrackets(chart, o, "inside");
      chart.off("click");
      if (cfg.clickable) {
        chart.on("click", params => {
          if (params.seriesName === "prefix cache hit rate") return;  // overlay line has no captured text
          const reqIndex = indexes[params.dataIndex];
          showContextText(runId, reqIndex, params.seriesName, typeByIndex.get(reqIndex), params.value, "ctx-text-panel-" + key);
        });
      }
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
      renderCacheChart();
      renderLatencyChart();
      refreshDrilldown();
    }

    // Make `key` the active report: swap in its (lazily parsed) data + context-texts,
    // repaint the masthead/§0 band, rebuild the sidebar + charts, and re-render.
    function activateReport(key, resetFilters) {
      const m = REPORTS_MANIFEST.find(r => r.key === key) || REPORTS_MANIFEST[0];
      if (!m) return;
      ACTIVE_REPORT = m.key;
      if (!REPORTS_PARSED[m.key]) {
        const parse = id => { const el = document.getElementById(id); try { return JSON.parse((el && el.textContent) || "{}"); } catch (e) { return {}; } };
        REPORTS_PARSED[m.key] = { data: parse(m.dataId), texts: parse(m.textsId) };
      }
      EXPERIMENT_DATA = REPORTS_PARSED[m.key].data;
      CONTEXT_TEXTS = REPORTS_PARSED[m.key].texts;
      document.getElementById("rpt-eyebrow").innerHTML = m.eyebrow || "";
      document.getElementById("rpt-title").innerHTML = m.title || "";
      document.getElementById("rpt-lede").innerHTML = m.lede || "";
      if (m.gradient) document.getElementById("masthead").style.borderImage = m.gradient;
      document.getElementById("brief-band-host").innerHTML = m.briefHtml || "";
      const gen = document.getElementById("generated-at");
      if (gen) gen.textContent = prettyDate(EXPERIMENT_DATA.generated_at);
      document.querySelectorAll(".switch-tab").forEach(t => t.classList.toggle("on", t.dataset.report === m.key));
      // Show the single_agent-relative overhead panel + control only when a baseline exists.
      for (const id of ["overhead-panel", "overhead-control"]) {
        const el = document.getElementById(id);
        if (el) el.style.display = overheadApplies() ? "" : "none";
      }
      // Sections are not URL-persisted, so always seed them to defaults; preserve a URL-provided
      // global Task on initial load (resetFilters=false), reset it on a tab switch.
      const keepTask = (!resetFilters && SEL.task.size) ? new Set(SEL.task) : null;
      seedDefaultFilters();
      if (keepTask) SEL.task = keepTask;
      buildStrips();
      initCharts();
      renderAll();
      writeURL();
    }

    document.getElementById("switcher").addEventListener("click", (e) => {
      const tab = e.target.closest(".switch-tab");
      if (tab && tab.dataset.report !== ACTIVE_REPORT) activateReport(tab.dataset.report, true);
    });
    // Chip / "all"-toggle clicks across every section strip (event delegation on <main>): each
    // chip carries data-scope + data-dim; commitFilter re-renders only the affected section.
    document.querySelector("main").addEventListener("click", (e) => {
      const chip = e.target.closest(".chip[data-scope]");
      if (chip) {
        const { scope, dim, val } = chip.dataset;
        const set = selSet(scope, dim);
        if (set.has(val)) set.delete(val); else set.add(val);
        commitFilter(scope, dim);
        return;
      }
      const tog = e.target.closest(".ftoggle[data-scope]");
      if (tog) { selSet(tog.dataset.scope, tog.dataset.toggle).clear(); commitFilter(tog.dataset.scope, tog.dataset.toggle); }  // clear = show all
    });
    document.getElementById("metric-filter").addEventListener("change", renderConditionChart);
    document.getElementById("overhead-filter").addEventListener("change", renderOverheadChart);
    document.getElementById("run-scale").addEventListener("input", renderDrilldown);
    document.getElementById("compose-filter").addEventListener("change", renderDrilldown);
    document.getElementById("hitrate-toggle").addEventListener("change", renderDrilldown);
    document.getElementById("group-filter").addEventListener("change", renderDrilldown);
    let _resizeTimer = null;
    window.addEventListener("resize", () => {
      Object.values(charts).forEach(chart => chart.resize());
      // the §3 group brackets are absolute-pixel graphics — recompute them after layout settles
      clearTimeout(_resizeTimer);
      _resizeTimer = setTimeout(renderDrilldown, 120);
    });
    window.addEventListener("hashchange", () => {
      const r = readURL();
      if (r && r !== ACTIVE_REPORT) activateReport(r, false);
      else { buildStrips(); renderAll(); writeURL(); }
    });

    const initialReport = readURL();
    activateReport(initialReport || (REPORTS_MANIFEST[0] && REPORTS_MANIFEST[0].key), false);
  </script>
</body>
</html>"""
