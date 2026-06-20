from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.plots.style import new_fig, plt


def plot_success_speedup(runs: pd.DataFrame, out_path: Path) -> Path:
    g = runs.groupby("condition").agg(
        success_rate=("success", lambda s: float(pd.Series(s).fillna(False).mean())),
        mean_speedup=("speedup", lambda s: float(pd.Series(s).fillna(0).mean())),
    )
    fig, ax = new_fig("Success rate & mean speedup by condition", "condition", "value")
    x = range(len(g)); w = 0.35
    ax.bar([i - w / 2 for i in x], g["success_rate"], w, label="success rate")
    ax.bar([i + w / 2 for i in x], g["mean_speedup"], w, label="mean speedup")
    ax.set_xticks(list(x)); ax.set_xticklabels(list(g.index), rotation=20); ax.legend()
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)
    return out_path
