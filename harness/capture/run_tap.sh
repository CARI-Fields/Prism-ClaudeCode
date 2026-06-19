#!/usr/bin/env bash
# Wrap a claude invocation in claude-tap. Traces are written to claude-tap's
# global SQLite DB (~/.local/share/claude-tap/traces.sqlite3); Task 9 extracts
# per-run traces from there by time window.
# Usage: run_tap.sh -- <claude args...>
set -euo pipefail
[ "${1:-}" = "--" ] && shift
HERE="$(cd "$(dirname "$0")" && pwd)"
TAP="$HERE/../../.venv/bin/claude-tap"
exec "$TAP" --tap-no-live --tap-no-open -- "$@"
