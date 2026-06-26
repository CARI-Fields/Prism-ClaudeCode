---
title: CC Experiment Report API
emoji: 📊
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# CC Experiment Report API

FastAPI + DuckDB read-only API over the processed experiment Parquet.
Set the `API_TOKEN` and `ALLOWED_ORIGINS` secrets in Space settings.
See `docs/superpowers/specs/2026-06-25-report-frontend-backend-split-design.md`.

## Build & runtime notes

- **Data must exist before building.** The Docker build COPYs `analysis/data/processed/` and the
  app reads it at `DATA_DIR`. Run `make analyze` (which regenerates `analysis/data/processed/*.parquet`)
  before `docker build` or `make deploy-space`. `analysis/data/processed/` is not tracked in this repo.
- **CORS is read at startup.** `ALLOWED_ORIGINS` is captured when the app process starts, so
  changing the Space secret requires a container restart to take effect. (`API_TOKEN` is
  re-read per request and does not.)
