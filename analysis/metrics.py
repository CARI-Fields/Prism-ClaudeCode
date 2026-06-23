from __future__ import annotations

import pandas as pd


def cache_accumulation(turns: pd.DataFrame) -> pd.DataFrame:
    """Accumulated prefix-cache hit rate per run from the raw, as-observed token
    counts. Every cache read the API reported is counted, including the warm cache
    inherited on the first request from a shared system-prompt prefix — that hit is
    real, so no warm-start baseline is subtracted."""
    df = turns.sort_values(["run_id", "request_index"]).copy()
    df["cache_creation"] = df["cache_creation_5m"] + df["cache_creation_1h"]

    for col in (
        "cum_cache_read",
        "cum_cache_creation",
        "cum_input",
        "cum_context_tokens",
        "cum_hit_ratio",
    ):
        df[col] = 0.0

    for _, group in df.groupby("run_id", sort=False):
        cum_read = 0.0
        cum_creation = 0.0
        cum_input = 0.0
        for idx, row in group.iterrows():
            cum_read += float(row.get("cache_read") or 0)
            cum_creation += float(row.get("cache_creation") or 0)
            cum_input += float(row.get("input_tokens") or 0)
            denom = cum_read + cum_creation + cum_input

            df.loc[idx, "cum_cache_read"] = cum_read
            df.loc[idx, "cum_cache_creation"] = cum_creation
            df.loc[idx, "cum_input"] = cum_input
            df.loc[idx, "cum_context_tokens"] = denom
            df.loc[idx, "cum_hit_ratio"] = (cum_read / denom) if denom else 0.0
    return df


def context_growth(components: pd.DataFrame) -> pd.DataFrame:
    df = components.sort_values(["run_id", "component", "request_index"]).copy()
    df["cum_est_tokens"] = df.groupby(["run_id", "component"])["est_tokens"].cumsum()
    return df
