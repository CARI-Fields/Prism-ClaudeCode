import json
from pathlib import Path
from analysis.parse.parse_ttft import load_ttft, join_ttft
from analysis.parse.parse_tap import tap_turns


def test_load_ttft():
    rows = load_ttft(Path("tests/fixtures/real_cell/ttft.jsonl"))
    assert rows and "t_send_epoch" in rows[0] and "ttft_s" in rows[0]


def test_join_matches_by_start_time():
    tap = json.loads(Path("tests/fixtures/real_cell/tap.json").read_text())
    turns = tap_turns(tap)
    ttft = load_ttft(Path("tests/fixtures/real_cell/ttft.jsonl"))
    joined = join_ttft(turns, ttft)
    # at least one turn got a real latency match
    assert any(j["ttft_s"] is not None for j in joined)
    # a matched turn's total_s is close to its duration
    for j in joined:
        if j["ttft_s"] is not None:
            assert abs(j["total_s"] - j["duration_ms"] / 1000) < 2.0
            break


def test_join_null_when_no_match():
    turns = [{"request_index": 0, "ts_start_epoch": 1000.0, "duration_ms": 10}]
    ttft = [{"t_send_epoch": 5000.0, "ttft_s": 1.0, "prefill_s": 0.5, "total_s": 2.0}]
    j = join_ttft(turns, ttft)
    assert j[0]["ttft_s"] is None
