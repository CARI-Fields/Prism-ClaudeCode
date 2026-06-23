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


def test_cache_accumulation_counts_warm_cache_as_observed():
    # The warm cache inherited from a shared system-prompt prefix is a real hit and
    # is counted as-observed; no warm-start baseline is subtracted.
    df = pd.DataFrame([
        {"run_id": "r", "request_index": 0, "request_type": "main-agent",
         "cache_read": 100, "cache_creation_5m": 50, "cache_creation_1h": 0,
         "input_tokens": 10},
        {"run_id": "r", "request_index": 1, "request_type": "main-agent",
         "cache_read": 150, "cache_creation_5m": 10, "cache_creation_1h": 0,
         "input_tokens": 10},
        {"run_id": "r", "request_index": 2, "request_type": "workflow-subagent",
         "cache_read": 20, "cache_creation_5m": 30, "cache_creation_1h": 0,
         "input_tokens": 5},
    ])

    out = cache_accumulation(df).sort_values("request_index")

    assert list(out["cum_cache_read"]) == [100, 250, 270]
    assert out.iloc[0]["cum_hit_ratio"] == 100 / 160
    assert out.iloc[2]["cum_hit_ratio"] == 270 / 385


def test_context_growth_cumulative_by_component():
    df = pd.DataFrame([
        {"run_id": "r", "request_index": 0, "component": "tools", "est_tokens": 50},
        {"run_id": "r", "request_index": 1, "component": "tools", "est_tokens": 60},
    ])
    out = context_growth(df)
    row = out[(out.request_index == 1) & (out.component == "tools")].iloc[0]
    assert row["cum_est_tokens"] == 110


def test_cache_accumulation_resets_per_run():
    df = pd.DataFrame([
        {"run_id": "r1", "request_index": 0, "cache_read": 50,
         "cache_creation_5m": 0, "cache_creation_1h": 50, "input_tokens": 10},
        {"run_id": "r2", "request_index": 0, "cache_read": 0,
         "cache_creation_5m": 0, "cache_creation_1h": 20, "input_tokens": 5},
    ])
    out = cache_accumulation(df)
    r2 = out[out.run_id == "r2"].iloc[0]
    assert r2["cum_cache_read"] == 0        # must not carry over from r1
    assert r2["cum_cache_creation"] == 20


def test_context_growth_resets_per_run():
    df = pd.DataFrame([
        {"run_id": "r1", "request_index": 0, "component": "tools", "est_tokens": 100},
        {"run_id": "r2", "request_index": 0, "component": "tools", "est_tokens": 7},
    ])
    out = context_growth(df)
    r2 = out[(out.run_id == "r2") & (out.component == "tools")].iloc[0]
    assert r2["cum_est_tokens"] == 7         # not 107
