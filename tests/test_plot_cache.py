import pandas as pd
from pathlib import Path
from analysis.plots.cache_accumulation import plot_cache_accumulation


def test_plot_writes_png(tmp_path):
    df = pd.DataFrame([
        {"run_id": "a", "condition": "single_agent", "task": "coding", "request_index": i,
         "cache_read": 100 * i, "cache_creation_5m": 0, "cache_creation_1h": 10,
         "input_tokens": 5} for i in range(4)
    ])
    out = plot_cache_accumulation(df, tmp_path / "cache.png")
    assert out.exists() and out.stat().st_size > 0
