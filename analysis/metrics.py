from __future__ import annotations

import pandas as pd


def cache_accumulation(turns: pd.DataFrame) -> pd.DataFrame:
    df = turns.sort_values(["run_id", "request_index"]).copy()
    df["cache_creation"] = df["cache_creation_5m"] + df["cache_creation_1h"]
    if "request_type" not in df.columns:
        df["request_type"] = "main-agent"

    for col in (
        "warm_start_cache_read",
        "run_local_cache_read",
        "cum_cache_read",
        "cum_cache_creation",
        "cum_input",
        "cum_run_local_cache_read",
        "cum_run_local_context_tokens",
        "observed_cum_hit_ratio",
        "cum_hit_ratio",
    ):
        df[col] = 0.0

    for _, group in df.groupby("run_id", sort=False):
        warm_start_by_type: dict[str, float] = {}
        cum_read = 0.0
        cum_creation = 0.0
        cum_input = 0.0
        cum_run_local_read = 0.0
        cum_run_local_creation = 0.0
        cum_run_local_input = 0.0
        for idx, row in group.iterrows():
            request_type = str(row.get("request_type") or "main-agent")
            read = float(row.get("cache_read") or 0)
            creation = float(row.get("cache_creation") or 0)
            input_tokens = float(row.get("input_tokens") or 0)
            if request_type not in warm_start_by_type:
                warm_start_by_type[request_type] = read
            warm_start_read = warm_start_by_type[request_type]
            run_local_read = max(0.0, read - warm_start_read)

            cum_read += read
            cum_creation += creation
            cum_input += input_tokens
            cum_run_local_read += run_local_read
            cum_run_local_creation += creation
            cum_run_local_input += input_tokens
            observed_denom = cum_read + cum_creation + cum_input
            run_local_denom = cum_run_local_read + cum_run_local_creation + cum_run_local_input

            df.loc[idx, "warm_start_cache_read"] = warm_start_read
            df.loc[idx, "run_local_cache_read"] = run_local_read
            df.loc[idx, "cum_cache_read"] = cum_read
            df.loc[idx, "cum_cache_creation"] = cum_creation
            df.loc[idx, "cum_input"] = cum_input
            df.loc[idx, "cum_run_local_cache_read"] = cum_run_local_read
            df.loc[idx, "cum_run_local_context_tokens"] = run_local_denom
            df.loc[idx, "observed_cum_hit_ratio"] = (cum_read / observed_denom) if observed_denom else 0.0
            df.loc[idx, "cum_hit_ratio"] = (cum_run_local_read / run_local_denom) if run_local_denom else 0.0
    return df


def context_growth(components: pd.DataFrame) -> pd.DataFrame:
    df = components.sort_values(["run_id", "component", "request_index"]).copy()
    df["cum_est_tokens"] = df.groupby(["run_id", "component"])["est_tokens"].cumsum()
    return df
