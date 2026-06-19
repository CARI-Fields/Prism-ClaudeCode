from __future__ import annotations

import shutil
from pathlib import Path


def encode_project_dir(cwd: str) -> str:
    """Claude Code stores transcripts under ~/.claude/projects/<encoded>, where
    <encoded> is the absolute cwd with each '/' replaced by '-'. (Confirm against
    pilot-notes.md whether '.' / '_' are also replaced; extend here if so.)"""
    return cwd.replace("/", "-")


def find_new_sessions(projects_dir: Path, project_cwd: str, since: float) -> list[Path]:
    root = Path(projects_dir).expanduser()
    if not root.is_dir():
        return []
    encoded = root / encode_project_dir(project_cwd)
    search_dirs = [encoded] if encoded.is_dir() else [d for d in root.iterdir() if d.is_dir()]
    found: list[Path] = []
    for d in search_dirs:
        found.extend(p for p in d.glob("*.jsonl") if p.stat().st_mtime >= since)
    return sorted(found)


def collect(run_dir: Path, projects_dir: Path, project_cwd: str, since: float) -> list[Path]:
    dest = Path(run_dir) / "transcripts"
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in find_new_sessions(projects_dir, project_cwd, since):
        out = dest / src.name
        shutil.copy2(src, out)
        copied.append(out)
    return copied
