from pathlib import Path

from harness.capture.collect_transcripts import (
    encode_project_dir, find_new_sessions, collect,
)


def test_encode_project_dir_replaces_slashes():
    assert encode_project_dir("/home/u/experiments/projects") == \
        "-home-u-experiments-projects"


def _touch(path: Path, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n")
    import os
    os.utime(path, (mtime, mtime))


def test_find_new_sessions_returns_only_recent(tmp_path: Path):
    projects = tmp_path / "projects"
    enc = encode_project_dir("/work/proj")
    old = projects / enc / "old.jsonl"
    new = projects / enc / "new.jsonl"
    _touch(old, 100.0)
    _touch(new, 200.0)
    found = find_new_sessions(projects, "/work/proj", since=150.0)
    assert [p.name for p in found] == ["new.jsonl"]


def test_collect_copies_into_run_dir(tmp_path: Path):
    projects = tmp_path / "projects"
    enc = encode_project_dir("/work/proj")
    _touch(projects / enc / "s.jsonl", 200.0)
    run_dir = tmp_path / "run"
    copied = collect(run_dir, projects, "/work/proj", since=150.0)
    assert (run_dir / "transcripts" / "s.jsonl").exists()
    assert len(copied) == 1
