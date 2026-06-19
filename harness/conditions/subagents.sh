#!/usr/bin/env bash
# Usage: subagents.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
PROMPT="Use the Task tool to delegate work to subagents running in parallel where possible. $(cat "$PROMPT_FILE")"
"$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$PROMPT"
