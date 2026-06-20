from __future__ import annotations

import pandas as pd


def cache_accumulation(turns: pd.DataFrame) -> pd.DataFrame:
    df = turns.sort_values(["run_id", "request_index"]).copy()
    df["cache_creation"] = df["cache_creation_5m"] + df["cache_creation_1h"]
    g = df.groupby("run_id")
    df["cum_cache_read"] = g["cache_read"].cumsum()
    df["cum_cache_creation"] = g["cache_creation"].cumsum()
    df["cum_input"] = g["input_tokens"].cumsum()
    denom = df["cum_cache_read"] + df["cum_cache_creation"] + df["cum_input"]
    df["cum_hit_ratio"] = (df["cum_cache_read"] / denom).fillna(0.0)
    return df


def context_growth(components: pd.DataFrame) -> pd.DataFrame:
    df = components.sort_values(["run_id", "component", "request_index"]).copy()
    df["cum_est_tokens"] = df.groupby(["run_id", "component"])["est_tokens"].cumsum()
    return df
