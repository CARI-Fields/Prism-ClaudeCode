#!/usr/bin/env bash
# Sync the API source + processed parquet into the HF Space repo clone and push.
# Usage: SPACE_DIR=/path/to/space-clone make deploy-space
set -euo pipefail
SPACE_DIR="${SPACE_DIR:?set SPACE_DIR to a local clone of the HF Space git repo}"
REPO_ROOT="$(git rev-parse --show-toplevel)"

rsync -a --delete "$REPO_ROOT/serve/" "$SPACE_DIR/serve/"
mkdir -p "$SPACE_DIR/analysis" "$SPACE_DIR/data/processed"
cp "$REPO_ROOT/analysis/__init__.py"        "$SPACE_DIR/analysis/__init__.py"
cp "$REPO_ROOT/analysis/report_variants.py" "$SPACE_DIR/analysis/report_variants.py"
shopt -s nullglob
parquets=("$REPO_ROOT"/data/processed/*.parquet)
[[ ${#parquets[@]} -gt 0 ]] || { echo "ERROR: no parquet files in data/processed/ — run 'make analyze' first" >&2; exit 1; }
cp "${parquets[@]}" "$SPACE_DIR/data/processed/"
cp "$REPO_ROOT/data/processed/token_rates.json" "$SPACE_DIR/data/processed/"
# HF Space expects Dockerfile + README.md + requirements.txt at the repo root.
cp "$REPO_ROOT/serve/Dockerfile"    "$SPACE_DIR/Dockerfile"
cp "$REPO_ROOT/serve/README.md"     "$SPACE_DIR/README.md"
cp "$REPO_ROOT/serve/requirements.txt" "$SPACE_DIR/requirements.txt"

cd "$SPACE_DIR"
git add -A
git commit -m "deploy: sync API + data" || echo "nothing to commit" >&2
git push origin HEAD
