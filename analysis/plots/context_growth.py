from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.plots.style import new_fig, plt


def plot_context_growth(components: pd.DataFrame, out_path: Path) -> Path:
    run_id = components["run_id"].iloc[0]
    g = components[components.run_id == run_id]
    pivot = g.pivot_table(index="request_index", columns="component",
                          values="est_tokens", aggfunc="sum").fillna(0)
    fig, ax = new_fig(f"Context window by component ({str(run_id)[:24]})",
                      "request index", "est. tokens (per request)")
    ax.stackplot(pivot.index, *[pivot[c] for c in pivot.columns], labels=list(pivot.columns))
    ax.legend(loc="upper left")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
