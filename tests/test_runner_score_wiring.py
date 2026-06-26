import json
from datetime import datetime, timezone
from pathlib import Path

import experiment.harness.runner as R
from experiment.harness.config import ExperimentConfig, TaskConfig, ConditionConfig
from experiment.harness.runner import plan_run, execute


def _exp(tmp):
    return ExperimentConfig(
        model="claude-sonnet-4-6", reps=1, conditions=["single_agent"], tasks=["research"],
        data_raw=tmp / "data/raw", claude_projects=tmp / "projects",
        proxy_host="127.0.0.1", proxy_port=8080,
        kernelgym_url="http://127.0.0.1:10908",
        drkernel_python="/usr/bin/true", ttft_port=8770, ttft_log=tmp / "ttft.jsonl",
    )


def test_execute_scores_research_and_writes_meta(tmp_path, monkeypatch):
    exp = _exp(tmp_path)
    prompt = tmp_path / "prompt.md"; prompt.write_text("write report.md")
    task = TaskConfig("research", prompt, None, None, kind="research",
                      required_sections=["A"], seed_files=[])
    cond = ConditionConfig("single_agent", tmp_path / "l.sh", "")
    plan = plan_run(exp, task, cond, 1, datetime(2026, 6, 19, 12, tzinfo=timezone.utc))

    monkeypatch.setattr(R.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(R, "collect", lambda *a, **k: [])
    monkeypatch.setattr(R, "collect_tap", lambda *a, **k: [])
    monkeypatch.setattr(R, "collect_ttft", lambda *a, **k: [{"ttft_s": 0.3}])
    monkeypatch.setattr(R, "ensure_services", lambda *a, **k: {"kernelgym": True})
    monkeypatch.setattr(R, "gather_versions", lambda: {})
    # research scorer sees no report.md in the scratch dir -> success False, but recorded
    out = execute(plan, exp, dry_run=False)
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["task"] == "research"
    assert "success" in meta and "ttft" in meta


def test_execute_skips_coding_when_kernelgym_down(tmp_path, monkeypatch):
    exp = _exp(tmp_path)
    prompt = tmp_path / "prompt.md"; prompt.write_text("write a kernel")
    task = TaskConfig("coding", prompt, None, None, kind="coding",
                      required_sections=[], seed_files=[])
    cond = ConditionConfig("single_agent", tmp_path / "l.sh", "")
    plan = plan_run(exp, task, cond, 1, datetime(2026, 6, 19, 12, tzinfo=timezone.utc))
    launched = {}
    monkeypatch.setattr(R.subprocess, "run", lambda *a, **k: launched.setdefault("ran", True))
    monkeypatch.setattr(R, "ensure_services", lambda *a, **k: {"kernelgym": False})
    out = execute(plan, exp, dry_run=False)
    import json
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["status"] == "skipped" and meta["reason"] == "kernelgym down"
    assert "ran" not in launched  # launcher/model never invoked
