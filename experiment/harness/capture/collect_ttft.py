from __future__ import annotations

import json
from pathlib import Path


def collect_ttft(run_dir: Path, src: Path, since: float, until: float) -> list[dict]:
    src = Path(src)
    kept: list[dict] = []
    if src.exists():
        for line in src.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ts = row.get("t_send_epoch")
            if ts is not None and since <= ts <= until:
                kept.append(row)
    dest = Path(run_dir) / "ttft"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "ttft.jsonl").write_text("".join(json.dumps(r) + "\n" for r in kept), encoding="utf-8")
    return kept
