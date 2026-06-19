import json
from pathlib import Path
from harness.capture.collect_ttft import collect_ttft


def test_collect_ttft_filters_window(tmp_path: Path):
    src = tmp_path / "all.jsonl"
    src.write_text(
        json.dumps({"request_id": "a", "t_send_epoch": 100.0, "ttft_s": 0.2}) + "\n"
        + json.dumps({"request_id": "b", "t_send_epoch": 200.0, "ttft_s": 0.3}) + "\n"
    )
    run_dir = tmp_path / "run"
    rows = collect_ttft(run_dir, src, since=150.0, until=250.0)
    assert [r["request_id"] for r in rows] == ["b"]
    out = run_dir / "ttft" / "ttft.jsonl"
    assert out.exists()
    assert json.loads(out.read_text().strip())["request_id"] == "b"
