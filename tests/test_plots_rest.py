import pandas as pd
from analysis.plots.context_growth import plot_context_growth
from analysis.plots.latency import plot_latency
from analysis.plots.success_speedup import plot_success_speedup


def test_context_growth_png(tmp_path):
    df = pd.DataFrame([
        {"run_id": "a", "request_index": i, "component": c, "est_tokens": 10 * (i + 1)}
        for i in range(3) for c in ("system_prompt", "tools", "messages")
    ])
    out = plot_context_growth(df, tmp_path / "ctx.png")
    assert out.exists() and out.stat().st_size > 0


def test_latency_png(tmp_path):
    df = pd.DataFrame([
        {"condition": "single_agent", "prefill_s": 2.9, "ttft_s": 3.0, "total_s": 128.0},
        {"condition": "single_agent", "prefill_s": 3.7, "ttft_s": 3.7, "total_s": 3.9},
        {"condition": "subagents", "prefill_s": None, "ttft_s": None, "total_s": None},
    ])
    out = plot_latency(df, tmp_path / "lat.png")
    assert out.exists() and out.stat().st_size > 0


def test_success_speedup_png(tmp_path):
    df = pd.DataFrame([
        {"condition": "single_agent", "success": False, "speedup": 0.0},
        {"condition": "subagents", "success": True, "speedup": 1.4},
    ])
    out = plot_success_speedup(df, tmp_path / "ss.png")
    assert out.exists() and out.stat().st_size > 0
