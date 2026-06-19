#!/usr/bin/env bash
# Usage: ralph_loop.sh <prompt_file> <run_dir> <model>   (external loop, fresh context each iteration)
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${RALPH_ITERS:-5}"
PROMPT="$(cat "$PROMPT_FILE")
Work incrementally: read PROGRESS.md if it exists, do one step, append your progress to PROGRESS.md."
for i in $(seq 1 "$ITERS"); do
  "$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$PROMPT"
done
