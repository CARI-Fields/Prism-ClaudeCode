from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.build_tables import build_all
from analysis.plots.cache_accumulation import plot_cache_accumulation
from analysis.plots.context_growth import plot_context_growth
from analysis.plots.latency import plot_latency
from analysis.plots.success_speedup import plot_success_speedup


def generate(raw_dir, processed_dir, figures_dir, report_path) -> Path:
    raw_dir, processed_dir = Path(raw_dir), Path(processed_dir)
    figures_dir, report_path = Path(figures_dir), Path(report_path)
    figures_dir.mkdir(parents=True, exist_ok=True)
    build_all(raw_dir, processed_dir)
    turns = pd.read_parquet(processed_dir / "turns.parquet")
    comps = pd.read_parquet(processed_dir / "components.parquet")
    runs = pd.read_parquet(processed_dir / "runs.parquet")

    figs = {
        "cache_accumulation.png": plot_cache_accumulation(turns, figures_dir / "cache_accumulation.png"),
        "context_growth.png": plot_context_growth(comps, figures_dir / "context_growth.png"),
        "latency.png": plot_latency(turns, figures_dir / "latency.png"),
        "success_speedup.png": plot_success_speedup(runs, figures_dir / "success_speedup.png"),
    }
    cols = [c for c in ("run_id", "task", "condition", "success", "speedup",
                        "num_requests", "total_cache_read", "cache_hit_ratio",
                        "completion_time_s") if c in runs.columns]
    table_md = runs[cols].to_markdown(index=False)

    lines = ["# Experiment Report\n",
             f"Runs analyzed: **{len(runs)}**.  (Build-only subset; narrative filled after the full sweep.)\n",
             "## Runs\n", table_md, "\n",
             "## Prefix-cache-hit accumulation (headline)\n",
             "![cache](../figures/cache_accumulation.png)\n",
             "## Context growth by component\n", "![ctx](../figures/context_growth.png)\n",
             "## Latency (TTFT vs total)\n", "![lat](../figures/latency.png)\n",
             "## Success rate & speedup\n", "![ss](../figures/success_speedup.png)\n"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    return report_path
