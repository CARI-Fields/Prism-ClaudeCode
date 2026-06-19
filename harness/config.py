from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ExperimentConfig:
    model: str
    reps: int
    conditions: list[str]
    tasks: list[str]
    data_raw: Path
    claude_projects: Path
    proxy_host: str
    proxy_port: int


def load_experiment(path: Path) -> ExperimentConfig:
    data = yaml.safe_load(Path(path).read_text())
    paths = data.get("paths", {})
    proxy = data.get("proxy", {})
    return ExperimentConfig(
        model=data["model"],
        reps=int(data["reps"]),
        conditions=list(data["conditions"]),
        tasks=list(data["tasks"]),
        data_raw=Path(paths.get("data_raw", "data/raw")),
        claude_projects=Path(paths.get("claude_projects", "~/.claude/projects")).expanduser(),
        proxy_host=proxy.get("host", "127.0.0.1"),
        proxy_port=int(proxy.get("port", 8080)),
    )


@dataclass(frozen=True)
class TaskConfig:
    name: str
    prompt_file: Path
    workspace: Path | None
    workspace_seed: Path | None


def load_task(path: Path) -> TaskConfig:
    data = yaml.safe_load(Path(path).read_text())
    ws = data.get("workspace")
    seed = data.get("workspace_seed")
    return TaskConfig(
        name=data["name"],
        prompt_file=Path(data["prompt_file"]),
        workspace=Path(ws) if ws else None,
        workspace_seed=Path(seed) if seed else None,
    )


@dataclass(frozen=True)
class ConditionConfig:
    name: str
    launcher: Path
    description: str


def load_condition(path: Path) -> ConditionConfig:
    data = yaml.safe_load(Path(path).read_text())
    return ConditionConfig(
        name=data["name"],
        launcher=Path(data["launcher"]),
        description=data.get("description", ""),
    )
