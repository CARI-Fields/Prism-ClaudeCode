#!/usr/bin/env bash
# Usage: ralph_loop.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${RALPH_ITERS:-2}"
SELFTEST=""; [ -x ./check_kernel.sh ] && SELFTEST="
Write your solution to solution.py and run: bash check_kernel.sh solution.py to test it."
BASE="$(cat "$PROMPT_FILE")"
for i in $(seq 1 "$ITERS"); do
  FB="$("$HERE/_feedback.sh" "$PWD")"
  "$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$BASE
$FB$SELFTEST"
done
