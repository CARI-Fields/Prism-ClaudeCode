import json
from pathlib import Path
from experiment.harness.capture.collect_ttft import collect_ttft


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


def test_collect_ttft_missing_src(tmp_path: Path):
    rows = collect_ttft(tmp_path / "run", tmp_path / "nonexistent.jsonl", 0.0, 1e9)
    assert rows == []
    assert (tmp_path / "run" / "ttft" / "ttft.jsonl").exists()


def test_collect_ttft_skips_rows_without_t_send_epoch(tmp_path: Path):
    src = tmp_path / "all.jsonl"
    src.write_text(
        json.dumps({"request_id": "x", "ttft_s": 0.1}) + "\n"
        + json.dumps({"request_id": "y", "t_send_epoch": 100.0, "ttft_s": 0.2}) + "\n"
    )
    rows = collect_ttft(tmp_path / "run", src, 0.0, 1e9)
    assert [r["request_id"] for r in rows] == ["y"]
