#!/usr/bin/env bash
# Prints an eval-feedback block for the current solution.py, or "" if none yet.
# Usage: _feedback.sh <scratch_dir>
set -euo pipefail
DIR="$1"
[ -f "$DIR/solution.py" ] || { echo ""; exit 0; }
if [ -x "$DIR/check_kernel.sh" ]; then
  OUT="$("$DIR/check_kernel.sh" "$DIR/solution.py" 2>&1 || true)"
  echo "Previous attempt eval result: $OUT. Improve correctness first, then speedup."
fi
