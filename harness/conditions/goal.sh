#!/usr/bin/env bash
# Usage: goal.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
SELFTEST=""; [ -x ./check_kernel.sh ] && SELFTEST="
Write your solution to solution.py and run: bash check_kernel.sh solution.py to test it."
PROMPT="/goal Complete this bounded experiment task before stopping: produce the required artifact, run any task-specific check, and verify the task's stated completion criteria.

$(cat "$PROMPT_FILE")$SELFTEST"
"$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$PROMPT"
