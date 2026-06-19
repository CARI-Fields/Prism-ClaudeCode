from datetime import datetime, timezone
from pathlib import Path

from harness.config import (
    ExperimentConfig, TaskConfig, ConditionConfig,
)
from harness.runner import plan_run


def _exp(tmp):
    return ExperimentConfig(
        model="claude-sonnet-4-6", reps=3,
        conditions=["single_agent"], tasks=["coding"],
        data_raw=Path(tmp) / "data/raw",
        claude_projects=Path(tmp) / "projects",
        proxy_host="127.0.0.1", proxy_port=8080,
    )


def test_plan_run_builds_run_id_and_dir(tmp_path):
    exp = _exp(tmp_path)
    task = TaskConfig("coding", Path("tasks/coding/prompt.md"), None, None)
    cond = ConditionConfig("single_agent", Path("harness/conditions/single_agent.sh"), "")
    ts = datetime(2026, 6, 18, 21, 0, 0, tzinfo=timezone.utc)
    plan = plan_run(exp, task, cond, rep=1, ts=ts)
    assert plan.run_id == "coding__single_agent__01__20260618T210000Z"
    assert plan.run_dir == exp.data_raw / plan.run_id
    assert plan.model == "claude-sonnet-4-6"
