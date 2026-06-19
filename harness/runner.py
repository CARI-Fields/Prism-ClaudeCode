from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from harness.config import (
    ExperimentConfig, TaskConfig, ConditionConfig,
    load_experiment, load_task, load_condition,
)
from harness.run_meta import make_run_id, write_run_meta, gather_versions
from harness.capture.collect_transcripts import collect
from harness.workspace import restore_workspace


@dataclass(frozen=True)
class RunPlan:
    run_id: str
    run_dir: Path
    task: TaskConfig
    condition: ConditionConfig
    rep: int
    model: str


def plan_run(exp: ExperimentConfig, task: TaskConfig, condition: ConditionConfig,
             rep: int, ts: datetime) -> RunPlan:
    run_id = make_run_id(task.name, condition.name, rep, ts)
    return RunPlan(run_id, exp.data_raw / run_id, task, condition, rep, exp.model)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def execute(plan: RunPlan, exp: ExperimentConfig, *, dry_run: bool = False) -> Path:
    run_dir = plan.run_dir
    prompt_file = plan.task.prompt_file
    cwd = Path.cwd()

    if plan.task.workspace and plan.task.workspace_seed:
        restore_workspace(plan.task.workspace_seed, plan.task.workspace)
        cwd = plan.task.workspace

    if dry_run:
        print(f"[dry-run] run_id={plan.run_id}")
        print(f"[dry-run] run_dir={run_dir}")
        print(f"[dry-run] launcher={plan.condition.launcher} "
              f"prompt={prompt_file} model={plan.model} cwd={cwd}")
        return run_dir

    (run_dir / "tap").mkdir(parents=True, exist_ok=True)
    (run_dir / "transcripts").mkdir(parents=True, exist_ok=True)
    start = _now().timestamp()

    launcher = Path(plan.condition.launcher).resolve()
    subprocess.run(
        [str(launcher), str(Path(prompt_file).resolve()), str(run_dir.resolve()), plan.model],
        cwd=str(cwd), check=True,
    )

    transcripts = collect(run_dir, exp.claude_projects, str(Path(cwd).resolve()), since=start)
    write_run_meta(run_dir, {
        "run_id": plan.run_id,
        "task": plan.task.name,
        "condition": plan.condition.name,
        "rep": plan.rep,
        "model": plan.model,
        "started_utc": datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
        "transcripts": [p.name for p in transcripts],
        "versions": gather_versions(),
    })
    return run_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--config", default="config/experiment.yaml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    exp = load_experiment(Path(args.config))
    task = load_task(Path(f"config/tasks/{args.task}.yaml"))
    cond = load_condition(Path(f"config/conditions/{args.condition}.yaml"))
    plan = plan_run(exp, task, cond, args.rep, _now())
    execute(plan, exp, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
