#!/usr/bin/env bash
# Usage: loop_dynamic.sh <prompt_file> <run_dir> <model>   (single session, retained context via --continue)
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${LOOP_ITERS:-5}"
# Iteration 1 starts the session; later iterations --continue the SAME session (context retained).
"$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$(cat "$PROMPT_FILE")"
for i in $(seq 2 "$ITERS"); do
  "$HERE/../capture/run_tap.sh" -- --model "$MODEL" --continue -p "Continue toward the goal. Do the next step."
done
