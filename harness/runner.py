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
from harness.capture.collect_tap import collect_tap
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
    start_dt = _now()
    start = start_dt.timestamp()

    launcher = Path(plan.condition.launcher).resolve()
    subprocess.run(
        [str(launcher), str(Path(prompt_file).resolve()), str(run_dir.resolve()), plan.model],
        cwd=str(cwd), check=True,
    )
    end_dt = _now()

    transcripts = collect(run_dir, exp.claude_projects, str(Path(cwd).resolve()), since=start)
    tap_files = collect_tap(run_dir, start_dt, end_dt)
    write_run_meta(run_dir, {
        "run_id": plan.run_id,
        "task": plan.task.name,
        "condition": plan.condition.name,
        "rep": plan.rep,
        "model": plan.model,
        "started_utc": start_dt.isoformat(),
        "ended_utc": end_dt.isoformat(),
        "transcripts": [p.name for p in transcripts],
        "tap": [p.name for p in tap_files],
        "versions": gather_versions(),
    })
    return run_dir


def iter_cells(exp: ExperimentConfig) -> list[tuple[str, str, int]]:
    cells: list[tuple[str, str, int]] = []
    for task in exp.tasks:
        for condition in exp.conditions:
            for rep in range(1, exp.reps + 1):
                cells.append((task, condition, rep))
    return cells


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task")
    ap.add_argument("--condition")
    ap.add_argument("--rep", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--config", default="config/experiment.yaml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    exp = load_experiment(Path(args.config))

    if args.all:
        for task_name, cond_name, rep in iter_cells(exp):
            task = load_task(Path(f"config/tasks/{task_name}.yaml"))
            cond = load_condition(Path(f"config/conditions/{cond_name}.yaml"))
            plan = plan_run(exp, task, cond, rep, _now())
            print(f"=== {plan.run_id} ===")
            execute(plan, exp, dry_run=args.dry_run)
        return 0

    task = load_task(Path(f"config/tasks/{args.task}.yaml"))
    cond = load_condition(Path(f"config/conditions/{args.condition}.yaml"))
    plan = plan_run(exp, task, cond, args.rep, _now())
    execute(plan, exp, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
