from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.plots.style import new_fig, plt


def plot_latency(turns: pd.DataFrame, out_path: Path) -> Path:
    df = turns.dropna(subset=["ttft_s"]).copy()
    fig, ax = new_fig("Latency: TTFT vs total by condition", "condition", "seconds")
    conds = list(df["condition"].dropna().unique()) or ["(none)"]
    for i, cond in enumerate(conds):
        sub = df[df["condition"] == cond]
        ax.scatter([i - 0.1] * len(sub), sub["ttft_s"], alpha=0.6, label="ttft_s" if i == 0 else None, color="tab:blue")
        ax.scatter([i + 0.1] * len(sub), sub["total_s"], alpha=0.6, label="total_s" if i == 0 else None, color="tab:red")
    ax.set_xticks(range(len(conds))); ax.set_xticklabels(conds, rotation=20)
    ax.set_yscale("symlog"); ax.legend()
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)
    return out_path
