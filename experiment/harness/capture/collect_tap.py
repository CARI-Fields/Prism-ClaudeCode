from __future__ import annotations

import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_DB = Path("~/.local/share/claude-tap/traces.sqlite3").expanduser()
DEFAULT_TAP_BIN = Path(__file__).resolve().parents[2] / ".venv" / "bin" / "claude-tap"


def find_tap_sessions(
    db_path: Path,
    since: datetime,
    until: datetime | None = None,
    client: str = "claude",
) -> list[str]:
    """Return claude-tap session ids whose started_at falls in [since, until], oldest first. since/until must be timezone-aware."""
    if since.tzinfo is None or (until is not None and until.tzinfo is None):
        raise ValueError("since/until must be timezone-aware (e.g. datetime.now(timezone.utc))")
    db = Path(db_path).expanduser()
    if not db.exists():
        return []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT id, started_at FROM sessions WHERE client = ?", (client,)
        ).fetchall()
    finally:
        con.close()
    matched: list[tuple[str, str]] = []
    for sid, started in rows:
        ts = datetime.fromisoformat(started)
        if ts >= since and (until is None or ts <= until):
            matched.append((started, sid))
    matched.sort()
    return [sid for _, sid in matched]


def export_session(
    session_id: str, out_path: Path, claude_tap_bin: Path = DEFAULT_TAP_BIN
) -> None:
    """Export one stored claude-tap session to JSON via the claude-tap CLI."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(claude_tap_bin), "export", "--session-id", session_id,
         "--format", "json", "-o", str(out_path)],
        check=True,
    )


def collect_tap(
    run_dir: Path,
    since: datetime,
    until: datetime | None = None,
    db_path: Path = DEFAULT_DB,
    claude_tap_bin: Path = DEFAULT_TAP_BIN,
    client: str = "claude",
) -> list[Path]:
    """Export every tap session in the run's time window into run_dir/tap/."""
    ids = find_tap_sessions(db_path, since, until, client=client)
    dest = Path(run_dir) / "tap"
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for sid in ids:
        out = dest / f"{sid}.json"
        export_session(sid, out, claude_tap_bin)
        written.append(out)
    return written
