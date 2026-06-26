#!/usr/bin/env bash
# Usage: dynamic_workflow.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
SELFTEST=""; [ -x ./check_kernel.sh ] && SELFTEST="
Write your solution to solution.py and run: bash check_kernel.sh solution.py to test it."
PROMPT="You MUST use the Workflow tool exactly once before writing the final answer. The workflow must be lightweight: launch exactly one short agent that returns only a compact implementation sketch or sanity-check note, wait for that workflow result, then write and test solution.py yourself. Do not launch broad background workflows, parallel agent fleets, or more than one workflow agent. $(cat "$PROMPT_FILE")$SELFTEST"
"$HERE/../capture/run_tap.sh" -- --model "$MODEL" -p "$PROMPT"
