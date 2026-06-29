from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from web.api.config import get_settings
from web.api.data_source import FULL_TEXT_FILE
from web.api.queries import _clean

_README = """# CC experiment trace export

Each selected run has one file under `runs/`:

- `runs/<run_id>.jsonl` — one JSON object per request (a "turn"), ordered by
  `request_index`, with that request's context-source breakdown nested under
  `components` (`{component, est_tokens, bytes}`).
- `runs/<run_id>.texts.jsonl` — present only when raw text was requested; one
  JSON object per captured context part with the FULL, untruncated `text`
  (`component_texts_full`). Static parts (system prompt, tool definitions) appear
  once per run (`stable: true`); volatile parts (messages, tool results) per request.

`manifest.json` lists the included runs and the export options.

Load (Python):

    import pandas as pd
    df = pd.read_json("runs/<run_id>.jsonl", lines=True)

Inspect (shell):

    jq . runs/<run_id>.jsonl
"""


def _data_dir() -> Path:
    return Path(get_settings().data_dir)


def _parquet(name: str) -> str:
    # Trusted config path (DATA_DIR + fixed filename), safe to format into SQL.
    return str(_data_dir() / name)


def _rows(sql: str, params: list) -> list[dict]:
    con = duckdb.connect()
    try:
        cur = con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [{c: _clean(v) for c, v in zip(cols, row)} for row in cur.fetchall()]
    finally:
        con.close()


def known_run_ids() -> set[str]:
    rows = _rows(
        f"SELECT DISTINCT run_id FROM read_parquet('{_parquet('runs.parquet')}')", []
    )
    return {r["run_id"] for r in rows}


def run_jsonl(run_id: str) -> str:
    turns = _rows(
        f"SELECT * FROM read_parquet('{_parquet('turns.parquet')}') "
        f"WHERE run_id = ? ORDER BY request_index",
        [run_id],
    )
    comps = _rows(
        f"SELECT * FROM read_parquet('{_parquet('components.parquet')}') WHERE run_id = ?",
        [run_id],
    )
    by_req: dict = {}
    for c in comps:
        by_req.setdefault(c.get("request_index"), []).append(
            {k: c.get(k) for k in ("component", "est_tokens", "bytes")}
        )
    out = []
    for t in turns:
        row = dict(t)
        row["components"] = by_req.get(row.get("request_index"), [])
        out.append(json.dumps(row, ensure_ascii=False))
    return ("\n".join(out) + "\n") if out else ""


def texts_jsonl(run_id: str) -> str:
    path = _parquet(FULL_TEXT_FILE)
    if not Path(path).exists():
        raise FileNotFoundError(
            "component_texts_full.parquet not present — run `make analyze` "
            "locally or configure HF_DATASET_REPO so the Space can fetch it"
        )
    rows = _rows(
        f"SELECT * FROM read_parquet('{path}') "
        f"WHERE run_id = ? ORDER BY request_index",
        [run_id],
    )
    return ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n") if rows else ""


def build_zip(run_ids, include_texts: bool, now: datetime | None = None) -> bytes:
    known = known_run_ids()
    valid: list[str] = []
    for rid in run_ids:
        if rid in known and rid not in valid:
            valid.append(rid)
    if not valid:
        raise ValueError("no valid run_ids")
    manifest = {
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "run_ids": valid,
        "include_texts": include_texts,
        "source": "cc-orchestration-report",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("README.md", _README)
        for rid in valid:
            z.writestr(f"runs/{rid}.jsonl", run_jsonl(rid))
            if include_texts:
                z.writestr(f"runs/{rid}.texts.jsonl", texts_jsonl(rid))
    return buf.getvalue()
