import json
from pathlib import Path
from analysis.parse.parse_meta import run_summary


def test_run_summary_fields(tmp_path):
    meta = json.loads(Path("tests/fixtures/real_cell/run_meta.json").read_text())
    s = run_summary(meta, tmp_path)  # tmp_path has no subagents
    assert s["task"] == "coding" and s["condition"] == "single_agent"
    assert "success" in s and "speedup" in s and "correctness" in s
    assert s["num_subagents"] == 0


def test_run_summary_counts_subagents(tmp_path):
    meta = {"task": "coding", "condition": "subagents", "rep": 1, "model": "m",
            "success": False, "score": {"correctness": False, "speedup": 0.0}}
    sub = tmp_path / "transcripts" / "u" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-1.jsonl").write_text("{}")
    (sub / "agent-2.jsonl").write_text("{}")
    s = run_summary(meta, tmp_path)
    assert s["num_subagents"] == 2
