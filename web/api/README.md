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
See `docs/superpowers/specs/2026-06-25-report-frontend-backend-split-design.md`.

## Build & runtime notes

- **Data is NOT in this (public) image.** This Space is public so the Vercel frontend can reach the
  token-gated API; committing the parquet here would make it directly downloadable and bypass the gate.
  Instead the app pulls the parquet at startup from a **private HF Dataset**.
- **Required Space secrets:** `API_TOKEN` (the shared bearer the frontend sends), `HF_DATASET_REPO`
  (e.g. `your-namespace/prism-cc-data`), `HF_ACCESS_TOKEN` (read token for that dataset), and
  `ALLOWED_ORIGINS` (the Vercel origin). On boot the app downloads the dataset into `DATA_DIR`.
- **Publishing data:** `make deploy-space` first runs `scripts/push_data.py` to upload
  `analysis/data/processed/*` to the private dataset (run `make analyze` first to regenerate it),
  then syncs only the code into the Space.
- **CORS is read at startup.** `ALLOWED_ORIGINS` is captured when the app process starts, so
  changing the Space secret requires a container restart to take effect. (`API_TOKEN` is
  re-read per request and does not.)
