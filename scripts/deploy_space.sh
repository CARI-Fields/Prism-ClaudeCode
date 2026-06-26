#!/usr/bin/env bash
# Sync the API source + processed parquet into the HF Space repo clone and push.
# Usage: SPACE_DIR=/path/to/space-clone make deploy-space
# The Space mirrors the repo layout: web/api/ (app), analysis/ (report metadata),
# analysis/data/processed/ (parquet). Dockerfile/README/requirements live at the Space root.
set -euo pipefail
SPACE_DIR="${SPACE_DIR:?set SPACE_DIR to a local clone of the HF Space git repo}"
REPO_ROOT="$(git rev-parse --show-toplevel)"

rsync -a --delete "$REPO_ROOT/web/api/" "$SPACE_DIR/web/api/"
cp "$REPO_ROOT/web/__init__.py" "$SPACE_DIR/web/__init__.py"   # package marker so `web.api` imports
mkdir -p "$SPACE_DIR/analysis" "$SPACE_DIR/analysis/data/processed"
cp "$REPO_ROOT/analysis/__init__.py"        "$SPACE_DIR/analysis/__init__.py"
cp "$REPO_ROOT/analysis/report_variants.py" "$SPACE_DIR/analysis/report_variants.py"
shopt -s nullglob
parquets=("$REPO_ROOT"/analysis/data/processed/*.parquet)
[[ ${#parquets[@]} -gt 0 ]] || { echo "ERROR: no parquet files in analysis/data/processed/ — run 'make analyze' first" >&2; exit 1; }
cp "${parquets[@]}" "$SPACE_DIR/analysis/data/processed/"
cp "$REPO_ROOT/analysis/data/processed/token_rates.json" "$SPACE_DIR/analysis/data/processed/"
# HF Space expects Dockerfile + README.md + requirements.txt at the repo root.
cp "$REPO_ROOT/web/api/Dockerfile"    "$SPACE_DIR/Dockerfile"
cp "$REPO_ROOT/web/api/README.md"     "$SPACE_DIR/README.md"
cp "$REPO_ROOT/web/api/requirements.txt" "$SPACE_DIR/requirements.txt"

cd "$SPACE_DIR"
git add -A
git commit -m "deploy: sync API + data" || echo "nothing to commit" >&2
git push origin HEAD
