import json
from datetime import datetime, timezone
from pathlib import Path

import harness.runner as R
from harness.config import ExperimentConfig, TaskConfig, ConditionConfig
from harness.runner import plan_run, execute


def _exp(tmp):
    return ExperimentConfig(
        model="claude-sonnet-4-6", reps=1,
        conditions=["single_agent"], tasks=["research"],
        data_raw=tmp / "data" / "raw", claude_projects=tmp / "projects",
        proxy_host="127.0.0.1", proxy_port=8080,
    )


def test_execute_runs_launcher_collects_both_and_writes_meta(tmp_path, monkeypatch):
    exp = _exp(tmp_path)
    prompt = tmp_path / "prompt.md"
    prompt.write_text("do the thing")
    task = TaskConfig("research", prompt, None, None)
    cond = ConditionConfig("single_agent", tmp_path / "launcher.sh", "")
    plan = plan_run(exp, task, cond, 1, datetime(2026, 6, 19, 12, tzinfo=timezone.utc))

    run_dir = plan.run_dir
    calls = {}
    monkeypatch.setattr(R.subprocess, "run", lambda *a, **k: calls.setdefault("launched", a))
    monkeypatch.setattr(R, "collect",
                        lambda *a, **k: [run_dir / "transcripts" / "-enc" / "u" / "subagents" / "agent-1.jsonl"])
    monkeypatch.setattr(R, "collect_tap", lambda rd, since, until: [run_dir / "tap" / "abc.json"])
    monkeypatch.setattr(R, "gather_versions", lambda: {"claude": "test"})

    out = execute(plan, exp, dry_run=False)

    assert "launched" in calls
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["task"] == "research" and meta["condition"] == "single_agent"
    assert meta["transcripts"] == ["transcripts/-enc/u/subagents/agent-1.jsonl"]
    assert meta["tap"] == ["tap/abc.json"]
    assert "started_utc" in meta and "ended_utc" in meta
