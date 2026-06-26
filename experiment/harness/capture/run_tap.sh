#!/usr/bin/env bash
# Wrap a claude invocation in claude-tap. Traces -> claude-tap global SQLite DB.
# When TTFT_PORT is set, claude-tap forwards upstream THROUGH the TTFT proxy.
# Usage: run_tap.sh -- <claude args...>
set -euo pipefail
if [ "${1:-}" = "--" ]; then shift; fi
HERE="$(cd "$(dirname "$0")" && pwd)"
TAP="$HERE/../../.venv/bin/claude-tap"
TAP_ARGS=(--tap-no-live --tap-no-open)
if [ -n "${TTFT_PORT:-}" ]; then TAP_ARGS+=(--tap-target "http://127.0.0.1:${TTFT_PORT}"); fi
exec "$TAP" "${TAP_ARGS[@]}" -- "$@"
