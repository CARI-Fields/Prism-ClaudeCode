from __future__ import annotations

import json
from pathlib import Path


def load_ttft(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def join_ttft(turn_rows: list[dict], ttft_rows: list[dict], tol: float = 0.5) -> list[dict]:
    out = []
    for turn in turn_rows:
        start = turn.get("ts_start_epoch")
        best, best_d = None, tol
        if start is not None:
            for t in ttft_rows:
                d = abs(t["t_send_epoch"] - start)
                if d <= best_d:
                    best, best_d = t, d
        row = dict(turn)
        row["ttft_s"] = best["ttft_s"] if best else None
        row["prefill_s"] = best["prefill_s"] if best else None
        row["total_s"] = best["total_s"] if best else None
        out.append(row)
    return out
