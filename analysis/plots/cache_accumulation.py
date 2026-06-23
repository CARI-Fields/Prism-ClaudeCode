from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.metrics import cache_accumulation
from analysis.plots.style import new_fig, plt


def plot_cache_accumulation(turns: pd.DataFrame, out_path: Path) -> Path:
    acc = cache_accumulation(turns)
    # attach condition/task (constant per run_id)
    meta = turns.groupby("run_id")[["condition", "task"]].first()
    acc = acc.merge(meta, on="run_id", how="left", suffixes=("", "_m"))
    task = acc["task"].dropna().iloc[0] if "task" in acc and acc["task"].notna().any() else ""
    fig, ax = new_fig(f"Run-local prefix-cache-hit accumulation ({task})",
                      "request index", "run-local cache hit rate (%)")
    for cond, g in acc.groupby("condition"):
        curve = g.groupby("request_index")["cum_hit_ratio"].mean() * 100
        ax.plot(curve.index + 1, curve.values, marker="o", label=str(cond))
    ax.set_ylim(0, 100)
    ax.legend(title="condition")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)
    return out_path
