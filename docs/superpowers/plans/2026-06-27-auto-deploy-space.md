# Auto-deploy HF Space Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-deploy the report API *code* to the public HF Space `nasa718/prism-api` on qualifying merges to `master`, via a shared staging script reused by the existing manual deploy and a new GitHub Actions workflow.

**Architecture:** A new `scripts/stage_space.sh <DEST>` is the single source of truth for the Space build-context file list; `scripts/deploy_space.sh` is refactored to call it; `.github/workflows/deploy-space.yml` stages the context and `upload_folder`s it to the Space using an `HF_ACCESS_TOKEN` secret. Code only — data stays in the private dataset.

**Tech Stack:** Bash · GitHub Actions · Python 3.12 · `huggingface_hub` · pytest.

## Global Constraints

- Bash scripts use `set -euo pipefail` and resolve the repo root from the script's own location (`ROOT="$(cd "$(dirname "$0")/.." && pwd)"`), so they work regardless of cwd.
- **Single source of truth:** the Space build-context file list lives ONLY in `scripts/stage_space.sh`. `deploy_space.sh` and the workflow MUST call it — do not duplicate the list.
- The Space build context (CODE ONLY, no parquet) is exactly:
  - root: `Dockerfile`, `README.md`, `requirements.txt` (copied from `web/api/`)
  - `web/__init__.py`, `web/api/*.py`
  - `analysis/__init__.py`, `analysis/report_variants.py`
  - `experiment/tasks/{coding,research,coding_longhorizon,research_longhorizon}/prompt.md`
  - NO `__pycache__`/`*.pyc`; the 3 root files are NOT duplicated under `web/api/`.
- CI target Space: `nasa718/prism-api` (`repo_type=space`), hardcoded. Auth via the `HF_ACCESS_TOKEN` Actions secret, passed by ENV (never argv).
- Workflow triggers: `push` to `master` filtered to the build-context paths (+ `scripts/stage_space.sh`), plus `workflow_dispatch`. `concurrency: group=deploy-space, cancel-in-progress=false`.
- Run the staging test from the worktree root: `/home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_stage_space.py -q`.
- Do NOT change `push_data.py`, the runtime data flow, or `deploy_space.sh`'s data-push / git-push behavior.

---

## File Structure

**Created:** `scripts/stage_space.sh`, `tests/test_stage_space.py`, `.github/workflows/deploy-space.yml`.
**Modified:** `scripts/deploy_space.sh` (call the shared stager instead of inline copies).

---

## Task 1: `scripts/stage_space.sh` + test

**Files:**
- Create: `scripts/stage_space.sh`
- Create: `tests/test_stage_space.py`

**Interfaces:**
- Produces: `stage_space.sh DEST` — populates `DEST` with the Space build context (see Global Constraints); exits non-zero on any missing source. Run as `bash scripts/stage_space.sh <dir>`.

- [ ] **Step 1: Write the failing test**

`tests/test_stage_space.py`:
```python
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_stage_space_builds_clean_context(tmp_path):
    dest = tmp_path / "space"
    subprocess.run(
        ["bash", str(REPO / "scripts" / "stage_space.sh"), str(dest)],
        check=True,
    )
    must_exist = [
        "Dockerfile", "README.md", "requirements.txt",
        "web/__init__.py", "web/api/app.py", "web/api/export.py", "web/api/queries.py",
        "analysis/__init__.py", "analysis/report_variants.py",
        "experiment/tasks/coding/prompt.md", "experiment/tasks/research/prompt.md",
        "experiment/tasks/coding_longhorizon/prompt.md",
        "experiment/tasks/research_longhorizon/prompt.md",
    ]
    for rel in must_exist:
        assert (dest / rel).is_file(), f"missing {rel}"
    # No bytecode artifacts.
    assert not list(dest.rglob("__pycache__")), "staged __pycache__"
    assert not list(dest.rglob("*.pyc")), "staged .pyc"
    # Root files are NOT duplicated under web/api.
    assert not (dest / "web" / "api" / "Dockerfile").exists()


def test_stage_space_clears_stale_modules(tmp_path):
    dest = tmp_path / "space"
    (dest / "web" / "api").mkdir(parents=True)
    stale = dest / "web" / "api" / "old_removed.py"
    stale.write_text("# stale module from a previous deploy\n")
    subprocess.run(
        ["bash", str(REPO / "scripts" / "stage_space.sh"), str(dest)],
        check=True,
    )
    assert not stale.exists(), "stale web/api/*.py should be cleared before staging"
    assert (dest / "web" / "api" / "app.py").is_file()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_stage_space.py -q`
Expected: FAIL (`scripts/stage_space.sh` does not exist → `bash` returns non-zero → `subprocess.run(check=True)` raises).

- [ ] **Step 3: Implement `scripts/stage_space.sh`**

```bash
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
```

Then make it executable:
```bash
chmod +x scripts/stage_space.sh
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_stage_space.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**
```bash
git add scripts/stage_space.sh tests/test_stage_space.py
git commit -m "feat(deploy): scripts/stage_space.sh — single source for the Space build context"
```

---

## Task 2: refactor `scripts/deploy_space.sh` to use the stager

**Files:**
- Modify: `scripts/deploy_space.sh`

**Interfaces:**
- Consumes: `scripts/stage_space.sh` (Task 1).

- [ ] **Step 1: Replace the inline code-sync block**

In `scripts/deploy_space.sh`, replace the entire step-2 block (the `rsync`/`cp`/`for`/`cp` lines that copy code into `$SPACE_DIR`, starting at the `# 2. Sync ONLY code into the Space clone ...` comment and ending at the `cp "$REPO_ROOT/web/api/requirements.txt" "$SPACE_DIR/requirements.txt"` line) with:

```bash
# 2. Sync ONLY code into the Space clone (shared with the CI workflow — the file
#    list lives in stage_space.sh so the two deploy paths never drift).
bash "$REPO_ROOT/scripts/stage_space.sh" "$SPACE_DIR"
```

Leave step 1 (`push_data.py`) and step 3 (`cd "$SPACE_DIR"; git add -A; git commit ...; git push ...`) unchanged.

> Behavior note: the old block also rsynced `web/api/` wholesale into `$SPACE_DIR/web/api/`, which left duplicate `Dockerfile`/`README.md`/`requirements.txt` *inside* `web/api/`. The stager places those three only at the Space root (where HF needs them). The next manual deploy will therefore show those three duplicates removed from `web/api/` — an intended, benign cleanup; the Space build is unaffected (the root copies are what HF uses, and `COPY web/api/` still includes all the `.py` code).

- [ ] **Step 2: Verify the script is still valid and uses the stager**

Run: `bash -n scripts/deploy_space.sh` → Expected: no output (syntax OK).
Run: `grep -c 'stage_space.sh' scripts/deploy_space.sh` → Expected: `1`.
Run: `grep -c 'rsync' scripts/deploy_space.sh` → Expected: `0` (the inline copy block is gone).
Run: `grep -c 'push_data.py' scripts/deploy_space.sh` → Expected: `1` (data push preserved).

- [ ] **Step 3: Run the staging test (still green)**

Run: `/home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -m pytest tests/test_stage_space.py -q` → Expected: PASS.

- [ ] **Step 4: Commit**
```bash
git add scripts/deploy_space.sh
git commit -m "refactor(deploy): deploy_space.sh stages via stage_space.sh (no duplicated list)"
```

---

## Task 3: `.github/workflows/deploy-space.yml`

**Files:**
- Create: `.github/workflows/deploy-space.yml`

**Interfaces:**
- Consumes: `scripts/stage_space.sh` (Task 1); the `HF_ACCESS_TOKEN` repo Actions secret (operator-provided).

- [ ] **Step 1: Create the workflow**

`.github/workflows/deploy-space.yml`:
```yaml
name: Deploy HF Space

# Auto-deploy the report API *code* to the public HF Space (nasa718/prism-api)
# whenever a merge to master changes the API build context. Data is NOT deployed
# here — it lives in a private HF Dataset, pulled at Space startup.
#
# REQUIRES a repo Actions secret HF_ACCESS_TOKEN (an HF *write* token):
#   GitHub → Settings → Secrets and variables → Actions → New repository secret.

on:
  push:
    branches: [master]
    paths:
      - 'web/api/**'
      - 'web/__init__.py'
      - 'analysis/__init__.py'
      - 'analysis/report_variants.py'
      - 'experiment/tasks/**/prompt.md'
      - 'scripts/stage_space.sh'
  workflow_dispatch:

concurrency:
  group: deploy-space
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install "huggingface_hub>=0.25"
      - name: Stage Space build context
        run: bash scripts/stage_space.sh "$RUNNER_TEMP/space"
      - name: Upload code to the HF Space
        env:
          HF_TOKEN: ${{ secrets.HF_ACCESS_TOKEN }}
        run: |
          python - <<'PY'
          import os
          from huggingface_hub import HfApi
          tok = os.environ.get("HF_TOKEN")
          if not tok:
              raise SystemExit(
                  "HF_ACCESS_TOKEN secret is not set — add it in "
                  "repo Settings → Secrets and variables → Actions"
              )
          sha = os.environ.get("GITHUB_SHA", "")[:7]
          HfApi(token=tok).upload_folder(
              folder_path=os.path.join(os.environ["RUNNER_TEMP"], "space"),
              repo_id="nasa718/prism-api",
              repo_type="space",
              commit_message=f"deploy: {sha} (auto from master)",
              ignore_patterns=["__pycache__", "*.pyc"],
          )
          print("deployed nasa718/prism-api")
          PY
```

- [ ] **Step 2: Validate the workflow YAML**

Run: `/home/yubaifeng/experiments/projects/claude-code/.venv/bin/python -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/deploy-space.yml')); print('jobs:', list(d['jobs'])); print('triggers:', list(d['on']))"`
Expected: prints `jobs: ['deploy']` and `triggers: ['push', 'workflow_dispatch']` (no YAML error).
> Note: PyYAML parses the `on:` key as the boolean `True` in some setups; if the second print shows `True`-keyed access fails, instead assert the file parses without error and `d['jobs']['deploy']['steps']` has 5 steps. The first print (jobs) is the reliable check.

- [ ] **Step 3: Sanity-check the staged upload path locally (no network)**

Run: `bash scripts/stage_space.sh /tmp/space-ci-check && ls /tmp/space-ci-check/web/api/export.py && rm -rf /tmp/space-ci-check`
Expected: lists `export.py` (confirms the workflow's stage step produces the export endpoint).

- [ ] **Step 4: Commit**
```bash
git add .github/workflows/deploy-space.yml
git commit -m "ci: auto-deploy the HF Space code on master (workflow_dispatch + path-filtered push)"
```

---

## Self-Review

**Spec coverage:**
- Shared `stage_space.sh` single source of truth → Task 1. ✓
- `deploy_space.sh` refactored to use it, behavior preserved (data push + git push) → Task 2. ✓
- Workflow: path-filtered push to master + workflow_dispatch, concurrency, code-only upload to `nasa718/prism-api` via `HF_ACCESS_TOKEN` env → Task 3. ✓
- Build context exactly the canonical list; no pycache; root files not duplicated under web/api → Task 1 (impl + both tests). ✓
- Testing: `test_stage_space.py` asserts the staged tree + stale-clear → Task 1. ✓
- Operator step (add `HF_ACCESS_TOKEN`) → documented in the workflow comment + error message (Task 3). ✓
- No data push in CI; push_data.py untouched → Task 2 (grep checks) + Task 3 (code-only). ✓

**Placeholder scan:** No TBD/TODO; scripts, YAML, and tests are complete.

**Type/consistency:** `stage_space.sh DEST` invoked identically in Task 1 (def), Task 2 (`bash "$REPO_ROOT/scripts/stage_space.sh" "$SPACE_DIR"`), and Task 3 (`bash scripts/stage_space.sh "$RUNNER_TEMP/space"`). The canonical file list is written once (Task 1) and asserted by the test; Tasks 2 & 3 never restate it. Space id `nasa718/prism-api` and secret `HF_ACCESS_TOKEN` are consistent between the spec and Task 3.
