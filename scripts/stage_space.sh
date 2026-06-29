#!/usr/bin/env bash
# Assemble the HF Space build context (CODE ONLY) into DEST.
#
# Single source of truth for "which files the Space needs" — used by both
# scripts/deploy_space.sh (manual) and .github/workflows/deploy-space.yml (CI).
# The processed parquet is NOT part of this: it lives in a private HF Dataset and
# is pulled at Space startup (see web/api/data_source.py).
#
# Usage: stage_space.sh DEST
set -euo pipefail
DEST="${1:?usage: stage_space.sh DEST}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$DEST/web/api" "$DEST/analysis"
# Clear stale API modules so a renamed/removed file does not linger in the Space.
rm -f "$DEST"/web/api/*.py

# HF Space expects Dockerfile + README.md + requirements.txt at the repo root.
cp "$ROOT/web/api/Dockerfile"       "$DEST/Dockerfile"
cp "$ROOT/web/api/README.md"        "$DEST/README.md"
cp "$ROOT/web/api/requirements.txt" "$DEST/requirements.txt"

# API code (importable as web.api).
cp "$ROOT/web/__init__.py" "$DEST/web/__init__.py"
find "$ROOT/web/api" -maxdepth 1 -name '*.py' -exec cp {} "$DEST/web/api/" \;

# Analysis helpers the API imports (report_variants powers /api/manifest).
cp "$ROOT/analysis/__init__.py"        "$DEST/analysis/__init__.py"
cp "$ROOT/analysis/report_variants.py" "$DEST/analysis/report_variants.py"

# Task spec files served by /api/manifest (the Dockerfile COPYs them into the image).
for t in coding research coding_longhorizon research_longhorizon; do
  mkdir -p "$DEST/experiment/tasks/$t"
  cp "$ROOT/experiment/tasks/$t/prompt.md" "$DEST/experiment/tasks/$t/prompt.md"
done

echo "staged Space build context -> $DEST"
