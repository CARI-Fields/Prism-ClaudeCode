from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.build_tables import build_all
from analysis.plots.cache_accumulation import plot_cache_accumulation
from analysis.plots.context_growth import plot_context_growth
from analysis.plots.latency import plot_latency
from analysis.plots.success_speedup import plot_success_speedup
from analysis.echarts_report import render_echarts_report


def generate(raw_dir, processed_dir, figures_dir, report_path) -> Path:
    raw_dir, processed_dir = Path(raw_dir), Path(processed_dir)
    figures_dir, report_path = Path(figures_dir), Path(report_path)
    figures_dir.mkdir(parents=True, exist_ok=True)
    counts = build_all(raw_dir, processed_dir)
    if counts.get("runs", 0) == 0:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("# Experiment Report\n\nNo runs found in analysis/data/raw.\n")
        return report_path
    turns = pd.read_parquet(processed_dir / "turns.parquet")
    comps = pd.read_parquet(processed_dir / "components.parquet")
    runs = pd.read_parquet(processed_dir / "runs.parquet")
    texts_path = processed_dir / "component_texts.parquet"
    comp_texts = pd.read_parquet(texts_path) if texts_path.exists() else None
    _ensure_columns(runs, [
        "speedup", "research_rubric_score", "research_format_score",
        "research_coverage_score", "research_word_count",
        "research_exact_two_url_sections", "quality_score", "total_cost_usd",
        "input_cost_usd", "cache_read_cost_usd", "cache_creation_5m_cost_usd",
        "cache_creation_1h_cost_usd", "output_cost_usd",
        "cost_efficiency_score", "speedup_per_dollar",
        "research_score_per_dollar",
    ])

    plot_cache_accumulation(turns, figures_dir / "cache_accumulation.png")
    plot_context_growth(comps, figures_dir / "context_growth.png")
    plot_latency(turns, figures_dir / "latency.png")
    plot_success_speedup(runs, figures_dir / "success_speedup.png")
    html_report = render_echarts_report(runs, turns, comps, report_path.with_suffix(".html"), comp_texts)

    cols = [c for c in ("run_id", "task", "condition", "success", "speedup",
                        "research_rubric_score", "quality_score",
                        "total_cost_usd", "cost_efficiency_score",
                        "num_requests", "total_cache_read",
                        "cache_hit_ratio",
                        "completion_time_s") if c in runs.columns]
    table_md = _markdown_table(runs, cols)

    condition_cols = [
        "task", "condition", "runs", "mean_speedup", "mean_research_rubric_score",
        "mean_quality_score", "mean_total_cost_usd", "mean_cost_efficiency_score",
    ]
    condition_summary = _condition_summary(runs)
    condition_md = _markdown_table(condition_summary, [c for c in condition_cols if c in condition_summary.columns])

    coding_cols = [
        "condition", "rep", "success", "speedup", "total_cost_usd",
        "input_cost_usd", "cache_read_cost_usd", "cache_creation_5m_cost_usd",
        "cache_creation_1h_cost_usd", "output_cost_usd", "speedup_per_dollar",
        "num_requests", "completion_time_s", "run_id",
    ]
    coding_rank = runs[runs["task"] == "coding"].sort_values(
        ["speedup", "total_cost_usd"], ascending=[False, True], na_position="last"
    )
    coding_md = _markdown_table(coding_rank, [c for c in coding_cols if c in coding_rank.columns])

    research_cols = [
        "condition", "rep", "success", "research_rubric_score",
        "research_format_score", "research_coverage_score", "research_word_count",
        "research_exact_two_url_sections", "total_cost_usd", "input_cost_usd",
        "cache_read_cost_usd", "cache_creation_5m_cost_usd",
        "cache_creation_1h_cost_usd", "output_cost_usd",
        "research_score_per_dollar", "num_requests", "completion_time_s", "run_id",
    ]
    research_rank = runs[runs["task"] == "research"].sort_values(
        ["research_rubric_score", "total_cost_usd"], ascending=[False, True], na_position="last"
    )
    research_md = _markdown_table(research_rank, [c for c in research_cols if c in research_rank.columns])

    chart_plan = [
        "- Experiment matrix: status for every task / condition / repetition cell.",
        "- Condition comparison: switchable aggregate metrics for success, latency, requests, cost, quality, cache, and token pressure.",
        "- Condition overhead vs single-agent baseline: normalized feature cost for subagents, loops, dynamic workflow, and loop+dynamic.",
        "- Quality vs cost map: coding speedup or research rubric score against estimated API-equivalent dollar cost.",
        "- Prefix Cache Hit Rate (accumulated): cache-hit rate over the raw, as-observed token counts, counting every reported cache read including the warm cache inherited from a shared system-prompt prefix.",
        "- TTFT vs prompt tokens: latency scaling as prompt/context grows.",
        "- Per-run request cost timeline: selected-run request sequence with input/cache-read/cache-write/output tokens, estimated request cost, and TTFT/total latency.",
        "- Context source breakdown: estimated per-request context composition by source, including system prompt, tools, MCP/extensions, CLAUDE.md/project instructions, skills, memory, hooks, user input, conversation history, tool results, and subagent summaries.",
    ]

    lines = ["# Experiment Report\n",
             f"Runs analyzed: **{len(runs)}**.  (Build-only subset; narrative filled after the full sweep.)\n",
             "## ECharts chart plan\n",
             *chart_plan,
             "\n## Interactive ECharts dashboard\n",
             f"[Interactive ECharts dashboard]({html_report.name})\n",
             f'<iframe src="{html_report.name}" width="100%" height="1400" title="Interactive ECharts dashboard"></iframe>\n',
             "## Cost and quality scoring\n",
             "Costs are estimated API-equivalent Claude Sonnet 4.6 token costs from the captured token categories: base input, 5m cache writes, 1h cache writes, cache reads, and output. Non-token add-on fees, if any, are not included.\n",
             "Coding quality is the KernelGYM `speedup` for successful runs. Research quality is a deterministic rubric score over required sections, citation balance, length, and lightweight keyword coverage.\n",
             "## Condition-level quality / cost summary\n",
             condition_md, "\n",
             "## Coding ranking by speedup\n",
             coding_md, "\n",
             "## Research ranking by rubric score\n",
             research_md, "\n",
             "## Runs\n", table_md, "\n",
             "## Prefix-cache-hit accumulation (static headline)\n",
             "![cache](../figures/cache_accumulation.png)\n",
             "## Context growth by prompt component (static headline)\n", "![ctx](../figures/context_growth.png)\n",
             "## Latency (TTFT vs total)\n", "![lat](../figures/latency.png)\n",
             "## Success rate & speedup\n", "![ss](../figures/success_speedup.png)\n"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    return report_path


def _condition_summary(runs: pd.DataFrame) -> pd.DataFrame:
    if runs.empty:
        return pd.DataFrame()
    grouped = runs.groupby(["task", "condition"], dropna=False)
    rows = grouped.agg(
        runs=("run_id", "count"),
        mean_speedup=("speedup", "mean"),
        mean_research_rubric_score=("research_rubric_score", "mean"),
        mean_quality_score=("quality_score", "mean"),
        mean_total_cost_usd=("total_cost_usd", "mean"),
        mean_cost_efficiency_score=("cost_efficiency_score", "mean"),
    ).reset_index()
    return rows.sort_values(["task", "mean_quality_score", "mean_total_cost_usd"], ascending=[True, False, True])


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> None:
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA


def _markdown_table(df: pd.DataFrame, cols: list[str]) -> str:
    if df.empty or not cols:
        return "_No rows._"
    out = df[cols].copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].round(4)
    out = out.astype(object).where(pd.notna(out), "")
    return out.to_markdown(index=False)
