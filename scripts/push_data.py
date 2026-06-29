#!/usr/bin/env python
"""Upload the processed parquet to the PRIVATE HF Dataset that backs the report API.

The public Space pulls these files at startup (see web/api/data_source.py); they
are deliberately NOT committed to the public Space repo, so the token-gated API is
the only path to the data.

Env:
  HF_DATASET_REPO   target dataset id, e.g. "your-namespace/prism-cc-data"
  HF_ACCESS_TOKEN   write token for that dataset
Usage:
  .venv/bin/python scripts/push_data.py [DATA_DIR]   # default: analysis/data/processed
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `web.api` importable regardless of how this script is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from huggingface_hub import HfApi  # noqa: E402

from web.api.data_source import DATA_FILES, FULL_TEXT_FILE  # noqa: E402

UPLOAD_FILES = DATA_FILES + (FULL_TEXT_FILE,)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    data_dir = Path(argv[0]) if argv else Path("analysis/data/processed")
    repo = os.environ.get("HF_DATASET_REPO")
    token = os.environ.get("HF_ACCESS_TOKEN")
    if not repo or not token:
        raise SystemExit("set HF_DATASET_REPO and HF_ACCESS_TOKEN")

    missing = [f for f in UPLOAD_FILES if not (data_dir / f).exists()]
    if missing:
        raise SystemExit(f"missing {missing} in {data_dir} — run `make analyze` first")

    api = HfApi(token=token)
    api.create_repo(repo_id=repo, repo_type="dataset", private=True, exist_ok=True)
    for name in UPLOAD_FILES:
        api.upload_file(
            path_or_fileobj=str(data_dir / name),
            path_in_repo=name,
            repo_id=repo,
            repo_type="dataset",
        )
    print(f"uploaded {len(UPLOAD_FILES)} files to private dataset {repo}")


if __name__ == "__main__":
    main()
