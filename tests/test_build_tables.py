import json, shutil
from pathlib import Path
import pandas as pd
from analysis.build_tables import build_run, build_all


def _make_run(tmp):
    d = tmp / "data/raw/coding__single_agent__01__20260619T210033Z"
    (d / "tap").mkdir(parents=True); (d / "ttft").mkdir(); (d / "transcripts").mkdir()
    shutil.copy("tests/fixtures/real_cell/tap.json", d / "tap/s.json")
    shutil.copy("tests/fixtures/real_cell/ttft.jsonl", d / "ttft/ttft.jsonl")
    shutil.copy("tests/fixtures/real_cell/run_meta.json", d / "run_meta.json")
    return d


def test_build_run(tmp_path):
    d = _make_run(tmp_path)
    turns, comps, run = build_run(d)
    assert turns and all(t["condition"] == "single_agent" for t in turns)
    assert run["num_requests"] == len(turns)
    assert run["total_cache_read"] == sum(t["cache_read"] for t in turns)
    assert 0.0 <= run["cache_hit_ratio"] <= 1.0


def test_build_all_writes_parquet(tmp_path):
    _make_run(tmp_path)
    out = tmp_path / "processed"
    counts = build_all(tmp_path / "data/raw", out)
    assert counts["runs"] == 1 and counts["turns"] > 0
    df = pd.read_parquet(out / "turns.parquet")
    assert {"run_id", "condition", "cache_read", "ttft_s"}.issubset(df.columns)
