from __future__ import annotations

from pathlib import Path


def run_summary(meta: dict, run_dir: Path) -> dict:
    score = meta.get("score") or {}
    transcript_dir = Path(run_dir) / "transcripts"
    subs = [
        path for path in transcript_dir.rglob("agent*.jsonl")
        if "subagents" in path.parts
    ]
    return {
        "task": meta.get("task"),
        "condition": meta.get("condition"),
        "rep": meta.get("rep"),
        "model": meta.get("model"),
        "success": meta.get("success"),
        "correctness": score.get("correctness"),
        "speedup": score.get("speedup"),
        "completion_time_s": meta.get("completion_time_s"),
        "num_subagents": len(subs),
    }
