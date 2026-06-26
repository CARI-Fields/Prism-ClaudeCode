import json
from datetime import datetime, timezone
from pathlib import Path

from experiment.harness.run_meta import make_run_id, write_run_meta


def test_make_run_id_pads_rep_and_uses_utc():
    ts = datetime(2026, 6, 18, 21, 0, 0, tzinfo=timezone.utc)
    assert make_run_id("coding", "subagents", 1, ts) == \
        "coding__subagents__01__20260618T210000Z"


def test_write_run_meta_roundtrips(tmp_path: Path):
    meta = {"task": "coding", "condition": "single_agent", "rep": 2}
    out = write_run_meta(tmp_path / "run", meta)
    assert out.name == "run_meta.json"
    assert json.loads(out.read_text())["condition"] == "single_agent"
    data = json.loads(out.read_text())
    assert data == meta
