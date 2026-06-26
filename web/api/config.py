from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    data_dir: str
    api_token: str
    allowed_origins: list[str]
    # Optional private data source: when HF_DATASET_REPO is set the API pulls the
    # parquet from that private HF Dataset at startup (so it need not be committed
    # to the public Space). Empty = local mode (DATA_DIR already populated).
    hf_dataset_repo: str
    hf_token: str


def get_settings() -> Settings:
    origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
    return Settings(
        data_dir=os.environ.get("DATA_DIR", "analysis/data/processed"),
        api_token=os.environ.get("API_TOKEN", ""),
        allowed_origins=[o.strip() for o in origins.split(",") if o.strip()],
        hf_dataset_repo=os.environ.get("HF_DATASET_REPO", ""),
        hf_token=os.environ.get("HF_ACCESS_TOKEN", ""),
    )
