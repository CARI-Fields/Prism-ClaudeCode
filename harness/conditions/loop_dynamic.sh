#!/usr/bin/env bash
# Usage: loop_dynamic.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${LOOP_ITERS:-2}"
# NOTE: --continue resumes the most-recent session for this cwd. Cells MUST run sequentially.
SELFTEST=""; [ -x ./check_kernel.sh ] && SELFTEST="
Write your solution to solution.py and run: bash check_kernel.sh solution.py to test it."
"$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$(cat "$PROMPT_FILE")$SELFTEST"
for i in $(seq 2 "$ITERS"); do
  FB="$("$HERE/_feedback.sh" "$PWD")"
  "$HERE/../capture/run_tap.sh" -- --model "$MODEL" --continue -p "$FB
This is the final lightweight continuation step. If the previous self-test already had compiled=True correctness=True decoy=False, keep the existing approach and make at most one small targeted speed tweak. Do not rewrite the solution, do not run broad experiments, and do not produce a long explanation. Run the self-test once and report only the final result.$SELFTEST"
done
