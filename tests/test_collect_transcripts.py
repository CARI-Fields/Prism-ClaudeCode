import os
from pathlib import Path

from experiment.harness.capture.collect_transcripts import (
    encode_project_dir, find_new_sessions, collect,
)


def test_encode_project_dir_replaces_slashes():
    assert encode_project_dir("/home/u/experiments/projects") == \
        "-home-u-experiments-projects"


def _touch(path: Path, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n")
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


def test_find_new_sessions_fallback_scans_all_dirs_when_encoded_absent(tmp_path: Path):
    projects = tmp_path / "projects"
    # encoded dir for "/work/proj" is "-work-proj"; create a DIFFERENT subdir name
    _touch(projects / "-some-other-encoding" / "new.jsonl", 200.0)
    found = find_new_sessions(projects, "/work/proj", since=150.0)
    assert [p.name for p in found] == ["new.jsonl"]


def test_find_new_sessions_missing_root_returns_empty(tmp_path: Path):
    assert find_new_sessions(tmp_path / "nonexistent", "/any", since=0.0) == []


def test_collect_copies_into_run_dir(tmp_path: Path):
    projects = tmp_path / "projects"
    enc = encode_project_dir("/work/proj")
    _touch(projects / enc / "s.jsonl", 200.0)
    run_dir = tmp_path / "run"
    copied = collect(run_dir, projects, "/work/proj", since=150.0)
    assert (run_dir / "transcripts" / enc / "s.jsonl").exists()
    assert len(copied) == 1


def test_collect_recurses_and_preserves_subagent_paths(tmp_path: Path):
    projects = tmp_path / "projects"
    enc = encode_project_dir("/work/proj")
    _touch(projects / enc / "sess.jsonl", 200.0)
    _touch(projects / enc / "sess" / "subagents" / "agent-1.jsonl", 200.0)
    run_dir = tmp_path / "run"
    copied = collect(run_dir, projects, "/work/proj", since=150.0)
    assert (run_dir / "transcripts" / enc / "sess.jsonl").exists()
    assert (run_dir / "transcripts" / enc / "sess" / "subagents" / "agent-1.jsonl").exists()
    assert len(copied) == 2
