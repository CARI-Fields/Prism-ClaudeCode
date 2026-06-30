import json, shutil
from pathlib import Path
import pandas as pd
from analysis.build_tables import build_run, build_all, cache_summary
from analysis.parse.parse_tap import drop_empty_turns, tap_turns
from analysis.parse.token_counts import TokenCounter, load_token_cache


def test_drop_empty_turns_removes_aborted_responses_and_reindexes():
    tap = [
        {"response": {"usage": {}, "content": [], "stop_reason": None}},          # aborted
        {"response": {"usage": {"input_tokens": 5, "cache_read_input_tokens": 100}}},
        {"response": {}},                                                          # no usage at all
        {"response": {"usage": {"input_tokens": 7, "cache_read_input_tokens": 200}}},
    ]
    kept = drop_empty_turns(tap)
    assert len(kept) == 2
    rows = tap_turns(kept)
    # request_index is contiguous over the real requests only
    assert [r["request_index"] for r in rows] == [0, 1]
    assert [r["cache_read"] for r in rows] == [100, 200]


def _make_run(tmp):
    d = tmp / "data/raw/coding__single_agent__01__20260619T210033Z"
    (d / "tap").mkdir(parents=True); (d / "ttft").mkdir(); (d / "transcripts").mkdir()
    shutil.copy("tests/fixtures/real_cell/tap.json", d / "tap/s.json")
    shutil.copy("tests/fixtures/real_cell/ttft.jsonl", d / "ttft/ttft.jsonl")
    shutil.copy("tests/fixtures/real_cell/run_meta.json", d / "run_meta.json")
    return d


def test_build_run(tmp_path):
    d = _make_run(tmp_path)
    turns, comps, run, comp_texts, comp_texts_full = build_run(d)
    assert turns and all(t["condition"] == "single_agent" for t in turns)
    assert run["num_requests"] == len(turns)
    assert run["total_cache_read"] == sum(t["cache_read"] for t in turns)
    assert 0.0 <= run["cache_hit_ratio"] <= 1.0
    assert "total_cost_usd" in run
    assert all("total_cost_usd" in turn for turn in turns)
    assert run["quality_score"] == 0.0
    assert comp_texts and all({"component", "text", "stable"} <= set(x) for x in comp_texts)
    assert comp_texts_full and all(x["truncated"] is False for x in comp_texts_full)


def test_build_run_threads_token_counter(tmp_path):
    d = _make_run(tmp_path)
    tc = TokenCounter(counter=lambda t: 1)  # exact count for every unique block
    _, comps, _, _, _ = build_run(d, token_counter=tc)
    assert tc.api_calls > 0          # the counter was actually consulted
    assert len(tc.cache) > 0         # and unique blocks were memoized
    assert comps                     # components still produced


def test_build_all_shares_and_persists_token_cache(tmp_path):
    _make_run(tmp_path)
    out = tmp_path / "processed"
    build_all(tmp_path / "data/raw", out, token_counter=TokenCounter(counter=lambda t: 2))
    cache = load_token_cache(out / "token_cache.json")
    assert cache and all(v == 2 for v in cache.values())


def test_cache_summary_counts_warm_cache_as_observed():
    summary = cache_summary([
        {
            "request_index": 0,
            "request_type": "main-agent",
            "input_tokens": 10,
            "cache_read": 100,
            "cache_creation_5m": 50,
            "cache_creation_1h": 0,
        },
        {
            "request_index": 1,
            "request_type": "main-agent",
            "input_tokens": 10,
            "cache_read": 150,
            "cache_creation_5m": 10,
            "cache_creation_1h": 0,
        },
        {
            "request_index": 2,
            "request_type": "workflow-subagent",
            "input_tokens": 5,
            "cache_read": 20,
            "cache_creation_5m": 30,
            "cache_creation_1h": 0,
        },
    ])

    assert summary["total_cache_read"] == 270
    # observed rate over raw counts: 270 read / (25 input + 270 read + 90 write)
    assert summary["cache_hit_ratio"] == 270 / 385


def test_build_all_writes_parquet(tmp_path):
    _make_run(tmp_path)
    out = tmp_path / "processed"
    counts = build_all(tmp_path / "data/raw", out)
    assert counts["runs"] == 1 and counts["turns"] > 0
    assert counts["component_texts_full"] > 0
    df = pd.read_parquet(out / "turns.parquet")
    assert {"run_id", "condition", "cache_read", "ttft_s"}.issubset(df.columns)
    full = pd.read_parquet(out / "component_texts_full.parquet")
    assert not full.empty and not full["truncated"].any()
    assert {"run_id", "component", "text", "stable", "truncated"}.issubset(full.columns)


def test_build_run_adds_research_rubric_fields(tmp_path):
    d = tmp_path / "data/raw/research__single_agent__01__20260621T185216Z"
    (d / "tap").mkdir(parents=True)
    (d / "ttft").mkdir()
    (d / "transcripts").mkdir()
    (d / "workspace").mkdir()
    shutil.copy("tests/fixtures/real_cell/tap.json", d / "tap/s.json")
    shutil.copy("tests/fixtures/real_cell/ttft.jsonl", d / "ttft/ttft.jsonl")
    meta = {
        "run_id": d.name,
        "task": "research",
        "condition": "single_agent",
        "rep": 1,
        "model": "claude-sonnet-4-6",
        "success": True,
        "score": {"success": True},
        "completion_time_s": 10.0,
    }
    (d / "run_meta.json").write_text(json.dumps(meta))
    sections = []
    for i, section in enumerate([
        "FlashAttention", "Quantized GEMM", "KV-cache",
        "Triton vs CUDA", "Hardware", "Autotuning",
    ], start=1):
        sections.append(
            f"## {section}\n\nFlashAttention attention memory tile quantized GEMM matmul int8 scale "
            f"KV-cache key value memory Triton CUDA kernel GPU H100 tensor core autotuning block benchmark.\n"
            f"https://example.com/{i}/a\nhttps://example.com/{i}/b\n"
        )
    (d / "workspace" / "report.md").write_text("\n".join(sections))

    _, _, run, _, _ = build_run(d)

    assert run["research_sections_present"] == 6
    assert run["research_exact_two_url_sections"] == 6
    assert run["research_rubric_score"] > 0
    assert run["quality_score"] == run["research_rubric_score"]
