from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def make_run_id(task: str, condition: str, rep: int, ts: datetime) -> str:
    stamp = ts.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{task}__{condition}__{rep:02d}__{stamp}"


def write_run_meta(run_dir: Path, meta: dict) -> Path:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run_meta.json"
    path.write_text(json.dumps(meta, indent=2, sort_keys=True))
    return path


def _cmd(args: list[str]) -> str:
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except Exception as exc:  # tool missing / non-zero — record, don't crash
        return f"<error: {exc}>"


def gather_versions() -> dict:
    return {
        "claude": _cmd(["claude", "--version"]),
        "claude_tap": _cmd(["claude-tap", "--version"]),
        "git_sha": _cmd(["git", "rev-parse", "HEAD"]),
    }
