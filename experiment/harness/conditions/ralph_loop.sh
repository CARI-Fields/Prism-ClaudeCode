#!/usr/bin/env bash
# Usage: ralph_loop.sh <prompt_file> <run_dir> <model>
set -euo pipefail
PROMPT_FILE="$1"; RUN_DIR="$2"; MODEL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ITERS="${RALPH_ITERS:-2}"
RALPH_PLUGIN_DIR="${RALPH_PLUGIN_DIR:-$HOME/.claude/plugins/cache/claude-plugins-official/ralph-loop/1.0.0}"
SELFTEST=""; [ -x ./check_kernel.sh ] && SELFTEST="
Write your solution to solution.py and run: bash check_kernel.sh solution.py to test it."
PROMPT_BODY="$(cat "$PROMPT_FILE")$SELFTEST

When the task is complete and the stated checks have passed, finish with exactly:
<promise>RALPH_DONE</promise>"

# The plugin command is expanded through a shell-backed slash command, so quote
# the multiline experiment prompt as one argument and escape shell metacharacters.
ESCAPED_PROMPT="$PROMPT_BODY"
ESCAPED_PROMPT="${ESCAPED_PROMPT//\\/\\\\}"
ESCAPED_PROMPT="${ESCAPED_PROMPT//\"/\\\"}"
ESCAPED_PROMPT="${ESCAPED_PROMPT//\$/\\$}"
ESCAPED_PROMPT="${ESCAPED_PROMPT//\`/\\\`}"

PROMPT="/ralph-loop \"$ESCAPED_PROMPT\" --max-iterations $ITERS --completion-promise RALPH_DONE"
"$HERE/../capture/run_tap.sh" -- --plugin-dir "$RALPH_PLUGIN_DIR" --model "$MODEL" -p "$PROMPT"
