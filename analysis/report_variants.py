"""Report variants: the two condition-scoped reads shown in the single-page report.

`report.html` is one self-contained page with a masthead switcher that flips between two
focused reads (built by ``echarts_report.render_combined_report``):

- **Multi-agent orchestration** — single_agent vs subagents vs dynamic_workflow, on the
  two bounded tasks (data already captured).
- **Long-horizon persistence** — goal vs ralph_loop, on the genuine long-horizon tasks.

This module defines those variants and builds each one's `page` payload (masthead copy +
the §0 "Tasks & strategies" band).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "experiment" / "tasks"

# One-line plain-language description of each orchestration strategy, written from the
# operator's side ("what it does"), used in each dashboard's strategy legend.
STRATEGY_DESC = {
    "single_agent": "One agent, one context window. No delegation — the baseline every overhead is measured against.",
    "subagents": "The main agent spawns Task subagents that work in parallel and hand back summaries.",
    "dynamic_workflow": "A workflow script orchestrates subagents deterministically — fan-out, pipeline, verify.",
    "goal": "A persistent goal file the agent re-reads every turn to hold the thread across a long task.",
    "ralph_loop": "The same prompt is re-invoked in a loop, each pass resuming where the last left off, until done.",
}

# Title + what-it-measures for every task that can appear in a report, keyed by the task
# directory name under experiment/tasks/.
TASK_META = {
    "coding": {
        "title": "Fused Triton kernel",
        "measures": "Write one @triton.jit kernel for relu(x·scale + bias), self-test once. Quality = KernelGYM speedup.",
    },
    "research": {
        "title": "GPU-inference survey",
        "measures": "A ~900-word, six-section survey with 12+ citations in one foreground pass. Quality = rubric score.",
    },
    "coding_longhorizon": {
        "title": "Kernel gauntlet · four kernels",
        "measures": "Four Triton kernels of rising difficulty; profile and tune toward a 2.0× geomean target. Success = all four kernels correct; quality = geomean speedup.",
    },
    "research_longhorizon": {
        "title": "Inference-serving deep-dive",
        "measures": "Eight serving systems, 3000–4500 words, 30+ primary sources, many research turns. Quality = rubric / coverage.",
    },
}

VARIANTS: list[dict[str, Any]] = [
    {
        "key": "multi_agent",
        "eyebrow": "Claude Code · orchestration experiment",
        "title": "Multi-agent orchestration",
        "lede": (
            "Does spreading one bounded task across more agents pay for itself? "
            "Single agent vs. subagents vs. a dynamic workflow, on a coding and a research task, "
            "three runs each &mdash; cost, latency, cache, and quality side by side."
        ),
        "conditions": ["single_agent", "subagents", "dynamic_workflow"],
        "tasks": ["coding", "research"],
    },
    {
        "key": "long_horizon",
        "eyebrow": "Claude Code · orchestration experiment",
        "title": "Long-horizon persistence",
        "lede": (
            "Which strategy holds a task together over many turns? "
            "A persistent goal file vs. a ralph loop vs. a dynamic workflow, on the long-horizon "
            "kernel gauntlet and the inference-serving deep-dive &mdash; cost, latency, cache, and quality "
            "side by side."
        ),
        "conditions": ["goal", "ralph_loop", "dynamic_workflow"],
        "tasks": ["coding_longhorizon", "research_longhorizon"],
    },
]


def _read_prompt(task: str) -> str:
    path = TASKS_DIR / task / "prompt.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _task_has_runs(runs: pd.DataFrame, task: str, conditions: list[str]) -> bool:
    if runs.empty or "task" not in runs.columns:
        return False
    scope = runs[runs["task"] == task]
    if "condition" in scope.columns:
        scope = scope[scope["condition"].isin(conditions)]
    return not scope.empty


def build_page(variant: dict[str, Any], runs: pd.DataFrame) -> dict[str, Any]:
    """Assemble the `page` payload (masthead copy + §0 brief band) for one variant."""
    briefs = []
    for i, task in enumerate(variant["tasks"], start=1):
        meta = TASK_META.get(task, {"title": task, "measures": ""})
        briefs.append({
            "n": f"{i:02d}",
            "task": task,
            "title": meta["title"],
            "measures": meta["measures"],
            "source": f"experiment/tasks/{task}/prompt.md",
            "prompt": _read_prompt(task) or "Prompt not found — this task's spec will appear once it is added under experiment/tasks/.",
            "has_data": _task_has_runs(runs, task, variant["conditions"]),
        })
    strategies = [{
        "condition": c,
        "label": c.replace("_", " "),
        "desc": STRATEGY_DESC.get(c, ""),
        "baseline": c == "single_agent",
    } for c in variant["conditions"]]
    return {
        "eyebrow": variant["eyebrow"],
        "title": variant["title"],
        "lede": variant["lede"],
        "scope_gradient": True,
        "task_briefs": briefs,
        "strategies": strategies,
    }
