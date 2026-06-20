from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # no display
import matplotlib.pyplot as plt  # noqa: E402


def new_fig(title: str, xlabel: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    return fig, ax
