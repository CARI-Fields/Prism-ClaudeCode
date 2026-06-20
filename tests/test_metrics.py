import pandas as pd
from analysis.metrics import cache_accumulation, context_growth


def test_cache_accumulation_cumsum_and_ratio():
    df = pd.DataFrame([
        {"run_id": "r", "request_index": 0, "cache_read": 0, "cache_creation_5m": 0,
         "cache_creation_1h": 100, "input_tokens": 10},
        {"run_id": "r", "request_index": 1, "cache_read": 90, "cache_creation_5m": 0,
         "cache_creation_1h": 0, "input_tokens": 10},
    ])
    out = cache_accumulation(df).sort_values("request_index")
    assert list(out["cum_cache_read"]) == [0, 90]
    assert list(out["cum_cache_creation"]) == [100, 100]
    # ratio at row 1 = 90 / (90+100+20)
    assert abs(out.iloc[1]["cum_hit_ratio"] - 90 / 210) < 1e-9


def test_context_growth_cumulative_by_component():
    df = pd.DataFrame([
        {"run_id": "r", "request_index": 0, "component": "tools", "est_tokens": 50},
        {"run_id": "r", "request_index": 1, "component": "tools", "est_tokens": 60},
    ])
    out = context_growth(df)
    row = out[(out.request_index == 1) & (out.component == "tools")].iloc[0]
    assert row["cum_est_tokens"] == 110
