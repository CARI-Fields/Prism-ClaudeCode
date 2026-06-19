from __future__ import annotations

from dataclasses import dataclass, field
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
    # instrumentation block — all defaulted so Plan A tests that omit these still work
    kernelgym_url: str = "http://127.0.0.1:10908"
    drkernel_python: str = "/home/yubaifeng/e84381970/envs/drkernel310/bin/python3.10"
    ttft_port: int = 8770
    ttft_log: Path = field(default=Path("/tmp/cc-exp-ttft.jsonl"))


def load_experiment(path: Path) -> ExperimentConfig:
    data = yaml.safe_load(Path(path).read_text())
    paths = data.get("paths", {})
    proxy = data.get("proxy", {})
    instr = data.get("instrumentation", {})
    return ExperimentConfig(
        model=data["model"],
        reps=int(data["reps"]),
        conditions=list(data["conditions"]),
        tasks=list(data["tasks"]),
        data_raw=Path(paths.get("data_raw", "data/raw")),
        claude_projects=Path(paths.get("claude_projects", "~/.claude/projects")).expanduser(),
        proxy_host=proxy.get("host", "127.0.0.1"),
        proxy_port=int(proxy.get("port", 8080)),
        kernelgym_url=instr.get("kernelgym_url", "http://127.0.0.1:10908"),
        drkernel_python=instr.get("drkernel_python", "/home/yubaifeng/e84381970/envs/drkernel310/bin/python3.10"),
        ttft_port=int(instr.get("ttft_port", 8770)),
        ttft_log=Path(instr.get("ttft_log", "/tmp/cc-exp-ttft.jsonl")),
    )


@dataclass(frozen=True)
class TaskConfig:
    name: str
    prompt_file: Path
    workspace: Path | None
    workspace_seed: Path | None
    # new fields — all defaulted so existing tests still work
    kind: str = ""
    required_sections: list[str] = field(default_factory=list)
    seed_files: list[Path] = field(default_factory=list)


def load_task(path: Path) -> TaskConfig:
    data = yaml.safe_load(Path(path).read_text())
    ws = data.get("workspace")
    seed = data.get("workspace_seed")
    return TaskConfig(
        name=data["name"],
        prompt_file=Path(data["prompt_file"]),
        workspace=Path(ws) if ws else None,
        workspace_seed=Path(seed) if seed else None,
        kind=data.get("kind", ""),
        required_sections=list(data.get("required_sections", [])),
        seed_files=[Path(p) for p in data.get("seed_files", [])],
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
