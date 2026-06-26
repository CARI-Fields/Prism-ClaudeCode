"""Fetch the processed dataset from a PRIVATE source at runtime.

The HF Space that hosts this API is public (so the Vercel frontend can reach it
with its bearer token), so the data must NOT be committed into the Space repo —
public Space files are directly downloadable and would bypass the token gate.
Instead the parquet lives in a private HF Dataset and is pulled in at startup
using the `HF_ACCESS_TOKEN` Space secret. The token gate then becomes the only
path to the data.

Local dev needs no dataset: leave `HF_DATASET_REPO` unset and `DATA_DIR` keeps
pointing at `make analyze` output.
"""
from __future__ import annotations

from pathlib import Path

from huggingface_hub import hf_hub_download

# The files queries.py reads from DATA_DIR.
DATA_FILES = (
    "runs.parquet",
    "turns.parquet",
    "components.parquet",
    "component_texts.parquet",
    "token_rates.json",
)


def _hf_download(repo: str, filename: str, token: str, dest: Path) -> None:
    hf_hub_download(
        repo_id=repo,
        repo_type="dataset",
        filename=filename,
        token=token or None,
        local_dir=str(Path(dest).parent),
    )


def ensure_data(data_dir, repo: str = "", token: str = "", files=DATA_FILES, _download=None) -> Path:
    """Populate `data_dir` with the data files from the private dataset `repo`.

    No-op (returns `data_dir`) when `repo` is empty — local dev relies on the
    files already being there. `_download` is injectable for tests.
    """
    data_dir = Path(data_dir)
    if not repo:
        return data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    download = _download or _hf_download
    for name in files:
        download(repo=repo, filename=name, token=token, dest=data_dir / name)
    return data_dir
