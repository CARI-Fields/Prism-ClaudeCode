# Auto-deploy the HF Space on master (design)

Date: 2026-06-27
Status: approved (pending spec review)
Scope: CI/deploy tooling (`scripts/`, `.github/workflows/`)

## 1. Context

The report API runs on a **public, Docker** HF Space `nasa718/prism-api` (the
Vercel frontend reaches its token-gated endpoints). The Space is updated
**manually** by running `make deploy-space` → `scripts/deploy_space.sh`, which
(a) pushes the processed parquet to a PRIVATE HF Dataset (`push_data.py`) and
(b) syncs the API *code* into a local clone of the Space repo and `git push`es
it. There is **no CI**. This caused a production bug: the `/api/export` endpoint
shipped in the frontend while the Space stayed on a pre-export image, so
`/api/export` returned 404 until a manual redeploy. The Space build context is
defined by `web/api/Dockerfile` (`COPY web/api/` + task prompts) and the file
list inside `deploy_space.sh`.

## 2. Goal

Auto-deploy the Space **code** whenever a merge to `master` changes the API, so
the backend never drifts behind the frontend again — without duplicating the
"which files go to the Space" list across two deploy paths.

## 3. Decisions (locked)

- **Shared staging script** (`scripts/stage_space.sh`) is the single source of
  truth for the Space build-context file list; both the manual deploy and CI use it.
- CI deploys **code only** (no data push — the parquet isn't in the repo; the
  Space pulls it from the private dataset at startup).
- Upload via `huggingface_hub` using an **`HF_ACCESS_TOKEN`** GitHub Actions
  secret (a write token). Target Space `nasa718/prism-api` is hardcoded.
- Trigger: **push to `master`** filtered to build-context paths, **plus manual
  `workflow_dispatch`**.

## 4. Components

### 4.1 `scripts/stage_space.sh <DEST>` (new)
Assembles the clean Space build context into `<DEST>` (creating it):
- root: `Dockerfile`, `README.md`, `requirements.txt` (copied from `web/api/`)
- `web/__init__.py`, `web/api/*.py` (the API code, incl. `export.py`)
- `analysis/__init__.py`, `analysis/report_variants.py`
- `experiment/tasks/{coding,research,coding_longhorizon,research_longhorizon}/prompt.md`
- excludes `__pycache__`/`*.pyc`; clears stale `web/api/*.py` in `<DEST>` first so
  a renamed/removed module doesn't linger. `set -euo pipefail`, run from repo root.

This is the exact layout already validated against the live Space (the
`/api/export` fix was deployed from it).

### 4.2 `scripts/deploy_space.sh` (refactored, behavior-preserving)
Replace the inline code-copy block (the `rsync`/`cp` lines that build the Space
clone's contents) with a single `bash "$REPO_ROOT/scripts/stage_space.sh" "$SPACE_DIR"`.
Keep everything else: the `push_data.py` data push, and the `git add/commit/push`
in `$SPACE_DIR`. `make deploy-space` keeps working the same.

### 4.3 `.github/workflows/deploy-space.yml` (new)
```
name: Deploy HF Space
on:
  push:
    branches: [master]
    paths: [web/api/**, web/__init__.py, analysis/__init__.py,
            analysis/report_variants.py, experiment/tasks/**/prompt.md]
  workflow_dispatch:
concurrency: { group: deploy-space, cancel-in-progress: false }
```
One `ubuntu-latest` job: `actions/checkout@v4` → `actions/setup-python@v5`
(3.12) → `pip install "huggingface_hub>=0.25"` → `scripts/stage_space.sh
"$RUNNER_TEMP/space"` → a Python step calling `HfApi(token=$HF_ACCESS_TOKEN)
.upload_folder(folder_path=$RUNNER_TEMP/space, repo_id="nasa718/prism-api",
repo_type="space", commit_message="deploy: <sha> (auto)",
ignore_patterns=["__pycache__","*.pyc"])`. The token comes from
`secrets.HF_ACCESS_TOKEN` (env, not argv). `cancel-in-progress: false` so a
running deploy finishes rather than being interrupted mid-push.

## 5. Operator step (one-time)
Add repo **Actions secret `HF_ACCESS_TOKEN`** (HF *write* token) in GitHub →
Settings → Secrets and variables → Actions. Documented in a workflow comment and
the deploy README/Makefile note. Without it the upload step fails (red CI).

## 6. Error handling / safety
- `set -euo pipefail` in `stage_space.sh`; missing source file → non-zero exit
  (fails the job loudly).
- `concurrency: deploy-space` serializes deploys (no overlapping pushes).
- Path filter avoids deploying on frontend-only / docs changes.
- Push-to-`master` trigger runs in the trusted context (secrets available);
  no fork-PR exposure.

## 7. Testing
- `tests/test_stage_space.py` (pytest, matches the repo's suite): run
  `scripts/stage_space.sh <tmp>` and assert the staged tree contains the expected
  files — `Dockerfile`, `README.md`, `requirements.txt` at root, `web/api/app.py`,
  `web/api/export.py`, `analysis/report_variants.py`, all four `prompt.md` — and
  contains **no** `__pycache__`/`*.pyc`.
- The workflow YAML is validated by its first real run: after the secret is added
  and this merges, the user can trigger `workflow_dispatch` (or it fires on the
  next API change). The upload path itself is already proven (the manual
  `/api/export` redeploy used the identical staging + `upload_folder`).

## 8. Non-goals
- No data push in CI; no change to `push_data.py` or the runtime data flow.
- No deploy of the frontend (Vercel handles that).
- No secrets management beyond the one Actions secret.
- Space id not parameterized (single project Space).

## 9. Success criteria
- `stage_space.sh` produces the correct build context (tested); `deploy_space.sh`
  uses it with unchanged behavior; the workflow exists and, once the
  `HF_ACCESS_TOKEN` secret is set, auto-deploys the Space on qualifying merges to
  `master` (and on manual dispatch). The 404-drift class of bug is prevented.
