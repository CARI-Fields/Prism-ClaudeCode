#!/usr/bin/env bash
# Usage: subagents.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
SELFTEST=""; [ -x ./check_kernel.sh ] && SELFTEST="
Write your solution to solution.py and run: bash check_kernel.sh solution.py to test it."
PROMPT="Use the Task tool to delegate work to subagents running in parallel where possible. $(cat "$PROMPT_FILE")$SELFTEST"
"$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$PROMPT"
