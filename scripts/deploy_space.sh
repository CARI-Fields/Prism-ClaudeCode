#!/usr/bin/env bash
# Deploy the report API to its public HF Space + push data to the PRIVATE dataset.
#
# The Space is public (so the Vercel frontend can reach the token-gated API), so
# it must contain ONLY code — never the parquet. The data goes to a private HF
# Dataset and is pulled at startup via the Space secrets HF_DATASET_REPO +
# HF_ACCESS_TOKEN (see web/api/data_source.py).
#
# Usage:
#   SPACE_DIR=/path/to/space-clone \
#   HF_DATASET_REPO=your-ns/prism-cc-data HF_ACCESS_TOKEN=hf_xxx \
#   make deploy-space
set -euo pipefail
SPACE_DIR="${SPACE_DIR:?set SPACE_DIR to a local clone of the HF Space git repo}"
: "${HF_DATASET_REPO:?set HF_DATASET_REPO to the private dataset id}"
: "${HF_ACCESS_TOKEN:?set HF_ACCESS_TOKEN to a write token}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
PY="${PY:-$REPO_ROOT/.venv/bin/python}"

# 1. Push the processed parquet to the PRIVATE dataset (NOT into the Space).
"$PY" "$REPO_ROOT/scripts/push_data.py" "$REPO_ROOT/analysis/data/processed"

# 2. Sync ONLY code into the Space clone (mirrors the repo layout: web/api + analysis helpers).
rsync -a --delete "$REPO_ROOT/web/api/" "$SPACE_DIR/web/api/"
cp "$REPO_ROOT/web/__init__.py" "$SPACE_DIR/web/__init__.py"   # package marker so `web.api` imports
mkdir -p "$SPACE_DIR/analysis"
cp "$REPO_ROOT/analysis/__init__.py"        "$SPACE_DIR/analysis/__init__.py"
cp "$REPO_ROOT/analysis/report_variants.py" "$SPACE_DIR/analysis/report_variants.py"
# HF Space expects Dockerfile + README.md + requirements.txt at the repo root.
cp "$REPO_ROOT/web/api/Dockerfile"    "$SPACE_DIR/Dockerfile"
cp "$REPO_ROOT/web/api/README.md"     "$SPACE_DIR/README.md"
cp "$REPO_ROOT/web/api/requirements.txt" "$SPACE_DIR/requirements.txt"

cd "$SPACE_DIR"
git add -A
git commit -m "deploy: sync API code (data lives in the private dataset)" || echo "nothing to commit" >&2
git push origin HEAD
echo "Deployed. Ensure the Space secrets HF_DATASET_REPO + HF_ACCESS_TOKEN + API_TOKEN are set."
