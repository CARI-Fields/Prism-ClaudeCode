#!/usr/bin/env bash
# Usage: start_ttft.sh <port> <out_jsonl>
set -euo pipefail
PORT="$1"; OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/../../.venv/bin/python"
nohup "$PY" -m harness.capture.ttft_proxy --port "$PORT" --out "$OUT" >/tmp/ttft_proxy.log 2>&1 &
echo "ttft_proxy pid $! on :$PORT -> $OUT"
