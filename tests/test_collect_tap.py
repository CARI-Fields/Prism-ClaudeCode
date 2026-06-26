import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

import experiment.harness.capture.collect_tap as ct
from experiment.harness.capture.collect_tap import find_tap_sessions, collect_tap


def _make_db(path: Path, rows):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE sessions (id TEXT, started_at TEXT, client TEXT)")
    con.executemany("INSERT INTO sessions VALUES (?, ?, ?)", rows)
    con.commit()
    con.close()


def test_find_tap_sessions_filters_by_window_and_client(tmp_path: Path):
    db = tmp_path / "t.sqlite3"
    _make_db(db, [
        ("before", "2026-06-19T10:00:00+00:00", "claude"),
        ("inwin", "2026-06-19T12:00:00+00:00", "claude"),
        ("after", "2026-06-19T14:00:00+00:00", "claude"),
        ("other", "2026-06-19T12:00:00+00:00", "codex"),
    ])
    since = datetime(2026, 6, 19, 11, tzinfo=timezone.utc)
    until = datetime(2026, 6, 19, 13, tzinfo=timezone.utc)
    assert find_tap_sessions(db, since, until) == ["inwin"]


def test_find_tap_sessions_missing_db_returns_empty(tmp_path: Path):
    assert find_tap_sessions(tmp_path / "nope.sqlite3",
                             datetime(2026, 1, 1, tzinfo=timezone.utc)) == []


def test_collect_tap_orchestration(tmp_path: Path, monkeypatch):
    db = tmp_path / "t.sqlite3"
    _make_db(db, [("s1", "2026-06-19T12:00:00+00:00", "claude")])
    calls = []

    def fake_export(session_id, out_path, claude_tap_bin=ct.DEFAULT_TAP_BIN):
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps({"session": session_id}))
        calls.append(session_id)

    monkeypatch.setattr(ct, "export_session", fake_export)
    run_dir = tmp_path / "run"
    out = collect_tap(run_dir,
                      datetime(2026, 6, 19, 11, tzinfo=timezone.utc),
                      datetime(2026, 6, 19, 13, tzinfo=timezone.utc),
                      db_path=db)
    assert out == [run_dir / "tap" / "s1.json"]
    assert (run_dir / "tap" / "s1.json").exists()
    assert calls == ["s1"]


def test_find_tap_sessions_rejects_naive_datetime(tmp_path: Path):
    db = tmp_path / "t.sqlite3"
    _make_db(db, [("s", "2026-06-19T12:00:00+00:00", "claude")])
    with pytest.raises(ValueError):
        find_tap_sessions(db, datetime(2026, 6, 19, 11))  # naive datetime
