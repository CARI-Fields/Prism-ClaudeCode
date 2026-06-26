from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    data_dir: str
    api_token: str
    allowed_origins: list[str]


def get_settings() -> Settings:
    origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
    return Settings(
        data_dir=os.environ.get("DATA_DIR", "analysis/data/processed"),
        api_token=os.environ.get("API_TOKEN", ""),
        allowed_origins=[o.strip() for o in origins.split(",") if o.strip()],
    )
