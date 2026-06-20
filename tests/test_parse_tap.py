import json
from pathlib import Path
from analysis.parse.parse_tap import parse_iso, tap_turns, tap_components

FIX = Path("tests/fixtures/real_cell/tap.json")


def test_parse_iso_to_epoch():
    assert abs(parse_iso("2026-06-19T21:02:44.554578+00:00") - 1781902964.554578) < 1e-3


def test_tap_turns_shape_and_start_time():
    tap = json.loads(FIX.read_text())
    rows = tap_turns(tap)
    assert len(rows) == len(tap)
    r0 = rows[0]
    for k in ("request_index", "ts_start_epoch", "input_tokens", "output_tokens",
              "cache_read", "cache_creation_5m", "cache_creation_1h", "duration_ms", "model"):
        assert k in r0
    assert r0["request_index"] == 0
    # start = completion timestamp - duration
    assert r0["ts_start_epoch"] == parse_iso(tap[0]["timestamp"]) - tap[0]["duration_ms"] / 1000


def test_tap_components_anchored_to_prompt_tokens():
    tap = json.loads(FIX.read_text())
    comps = tap_components(tap)
    # all three components present for request 0
    c0 = [c for c in comps if c["request_index"] == 0]
    assert {c["component"] for c in c0} == {"system_prompt", "tools", "messages"}
    # est_tokens for a request sum to its prompt tokens (input+cache_read+cache_creation)
    u = tap[0]["response"]["usage"]
    prompt = u["input_tokens"] + u["cache_read_input_tokens"] + u["cache_creation_input_tokens"]
    assert sum(c["est_tokens"] for c in c0) == prompt
