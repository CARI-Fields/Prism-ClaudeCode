#!/usr/bin/env bash
# Usage: single_agent.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
"$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$(cat "$PROMPT_FILE")"
