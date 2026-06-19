from __future__ import annotations

import argparse
import os
import shutil
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
from harness.capture.collect_ttft import collect_ttft
from harness.services import ensure_services
from harness.score.score_research import score_research
from harness.score.score_coding import score_kernel
from harness.score.extract import extract_last_code_block


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


def score_run(task: TaskConfig, scratch_dir: Path, exp: ExperimentConfig) -> dict:
    if task.kind == "research":
        return {"score": score_research(scratch_dir / "report.md", task.required_sections)}
    if task.kind == "coding":
        sol = scratch_dir / "solution.py"
        ref = Path("tasks/coding/reference_code.py")
        if sol.exists() and ref.exists():
            res = score_kernel(sol.read_text(), ref.read_text(), exp.kernelgym_url)
        else:
            res = {"success": False, "reason": "no solution.py"}
        return {"score": res}
    return {"score": {"success": None}}


def execute(plan: RunPlan, exp: ExperimentConfig, *, dry_run: bool = False) -> Path:
    run_dir = plan.run_dir
    prompt_file = plan.task.prompt_file

    if dry_run:
        print(f"[dry-run] run_id={plan.run_id}")
        print(f"[dry-run] run_dir={run_dir}")
        print(f"[dry-run] launcher={plan.condition.launcher} "
              f"prompt={prompt_file} model={plan.model}")
        return run_dir

    scratch = run_dir / "workspace"
    scratch.mkdir(parents=True, exist_ok=True)
    for f in plan.task.seed_files:
        shutil.copy2(f, scratch / Path(f).name)

    ensure_services(exp.kernelgym_url)
    (run_dir / "tap").mkdir(parents=True, exist_ok=True)

    start_dt = _now()
    start = start_dt.timestamp()

    env = {**os.environ, "TTFT_PORT": str(exp.ttft_port),
           "KERNELGYM_URL": exp.kernelgym_url, "DRKERNEL_PY": exp.drkernel_python}
    launcher = Path(plan.condition.launcher).resolve()
    subprocess.run(
        [str(launcher), str(Path(prompt_file).resolve()), str(run_dir.resolve()), plan.model],
        cwd=str(scratch), check=True, env=env,
    )
    end_dt = _now()

    transcripts = collect(run_dir, exp.claude_projects, str(scratch.resolve()), since=start)
    tap_files = collect_tap(run_dir, start_dt, end_dt)
    ttft_rows = collect_ttft(run_dir, exp.ttft_log, start, end_dt.timestamp())
    score = score_run(plan.task, scratch, exp)["score"]
    write_run_meta(run_dir, {
        "run_id": plan.run_id,
        "task": plan.task.name,
        "condition": plan.condition.name,
        "rep": plan.rep,
        "model": plan.model,
        "started_utc": start_dt.isoformat(),
        "ended_utc": end_dt.isoformat(),
        "completion_time_s": (end_dt - start_dt).total_seconds(),
        "transcripts": [str(p.relative_to(run_dir)) for p in transcripts],
        "tap": [str(p.relative_to(run_dir)) for p in tap_files],
        "ttft": ttft_rows,
        "success": score.get("success"),
        "score": score,
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
        failures: list[str] = []
        cells = iter_cells(exp)
        for task_name, cond_name, rep in cells:
            task = load_task(Path(f"config/tasks/{task_name}.yaml"))
            cond = load_condition(Path(f"config/conditions/{cond_name}.yaml"))
            plan = plan_run(exp, task, cond, rep, _now())
            print(f"=== {plan.run_id} ===")
            try:
                execute(plan, exp, dry_run=args.dry_run)
            except Exception as exc:
                print(f"!!! FAILED {plan.run_id}: {exc}")
                failures.append(plan.run_id)
                if not args.dry_run:
                    write_run_meta(plan.run_dir, {
                        "run_id": plan.run_id,
                        "task": task.name,
                        "condition": cond.name,
                        "rep": rep,
                        "model": plan.model,
                        "status": "failed",
                        "error": str(exc),
                    })
        if failures:
            print(f"{len(failures)}/{len(cells)} cell(s) failed: {failures}")
        return 0

    task = load_task(Path(f"config/tasks/{args.task}.yaml"))
    cond = load_condition(Path(f"config/conditions/{args.condition}.yaml"))
    plan = plan_run(exp, task, cond, args.rep, _now())
    execute(plan, exp, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
