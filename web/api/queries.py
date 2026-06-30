from __future__ import annotations

import json
import math
from pathlib import Path

import duckdb

from analysis.report_variants import STRATEGY_DESC, TASK_META, VARIANTS, read_prompt
from web.api.config import get_settings


def _data_dir() -> Path:
    return Path(get_settings().data_dir)


def _parquet(name: str) -> str:
    # Path is trusted config (DATA_DIR + fixed filename), safe to format into SQL.
    return str(_data_dir() / name)


def _clean(v):
    # Starlette's JSONResponse uses allow_nan=False, so NaN/Inf (common in the
    # research_* columns for coding runs) would 500 the endpoint. Coerce to None,
    # recursing into list/struct columns DuckDB returns as native list/dict.
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    return v


def _rows(sql: str, params: list | None = None) -> list[dict]:
    con = duckdb.connect()
    try:
        cur = con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [{c: _clean(v) for c, v in zip(cols, row)} for row in cur.fetchall()]
    finally:
        con.close()


def get_runs() -> list[dict]:
    return _rows(f"SELECT * FROM read_parquet('{_parquet('runs.parquet')}')")


def get_turns() -> list[dict]:
    return _rows(f"SELECT * FROM read_parquet('{_parquet('turns.parquet')}')")


def get_components() -> list[dict]:
    return _rows(f"SELECT * FROM read_parquet('{_parquet('components.parquet')}')")


def get_component_texts(run_id: str, request_index: int | None = None) -> list[dict]:
    path = _parquet("component_texts.parquet")
    if request_index is None:
        return _rows(
            f"SELECT * FROM read_parquet('{path}') WHERE run_id = ?", [run_id]
        )
    return _rows(
        f"SELECT * FROM read_parquet('{path}') WHERE run_id = ? AND request_index = ?",
        [run_id, request_index],
    )


def get_token_rates() -> dict:
    return json.loads((_data_dir() / "token_rates.json").read_text())


def get_manifest() -> dict:
    available = _rows(
        f"SELECT task, condition, COUNT(*) AS runs "
        f"FROM read_parquet('{_parquet('runs.parquet')}') "
        f"GROUP BY task, condition ORDER BY task, condition"
    )
    return {
        "variants": VARIANTS,
        "strategy_desc": STRATEGY_DESC,
        "task_meta": TASK_META,
        # Full task spec per task (empty string when no prompt.md exists, e.g. the
        # long-horizon tasks). Read from experiment/tasks/<task>/prompt.md.
        "task_prompts": {task: read_prompt(task) for task in TASK_META},
        "available": available,
    }
