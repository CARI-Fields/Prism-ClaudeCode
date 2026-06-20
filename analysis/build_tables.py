from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from analysis.parse.parse_tap import tap_turns, tap_components
from analysis.parse.parse_ttft import load_ttft, join_ttft
from analysis.parse.parse_meta import run_summary


def build_run(run_dir: Path):
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "run_meta.json").read_text())
    tap_files = sorted((run_dir / "tap").glob("*.json"))
    tap = json.loads(tap_files[0].read_text()) if tap_files else []
    turns = join_ttft(tap_turns(tap), load_ttft(run_dir / "ttft" / "ttft.jsonl"))
    comps = tap_components(tap)
    run_id = run_dir.name
    stamp = {"run_id": run_id, "task": meta.get("task"),
             "condition": meta.get("condition"), "rep": meta.get("rep")}
    for r in turns:
        r.update(stamp)
    for c in comps:
        c.update(stamp)
    summary = run_summary(meta, run_dir)
    summary["run_id"] = run_id
    total_in = sum(t["input_tokens"] for t in turns)
    total_cr = sum(t["cache_read"] for t in turns)
    total_cc = sum(t["cache_creation_5m"] + t["cache_creation_1h"] for t in turns)
    denom = total_in + total_cr + total_cc
    summary.update({
        "num_requests": len(turns),
        "total_input": total_in,
        "total_cache_read": total_cr,
        "total_cache_creation": total_cc,
        "cache_hit_ratio": (total_cr / denom) if denom else 0.0,
        "peak_prompt_tokens": max((t["input_tokens"] + t["cache_read"]
                                   + t["cache_creation_5m"] + t["cache_creation_1h"]
                                   for t in turns), default=0),
        "output_tokens_total": sum(t["output_tokens"] for t in turns),
    })
    return turns, comps, summary


def build_all(raw_dir: Path, out_dir: Path) -> dict:
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_turns, all_comps, all_runs = [], [], []
    for d in sorted(raw_dir.iterdir()):
        if not (d / "run_meta.json").exists():
            continue
        try:
            t, c, r = build_run(d)
        except Exception as exc:
            print(f"skip {d.name}: {exc}")
            continue
        all_turns += t; all_comps += c; all_runs.append(r)
    pd.DataFrame(all_turns).to_parquet(out_dir / "turns.parquet")
    pd.DataFrame(all_comps).to_parquet(out_dir / "components.parquet")
    pd.DataFrame(all_runs).to_parquet(out_dir / "runs.parquet")
    return {"turns": len(all_turns), "components": len(all_comps), "runs": len(all_runs)}
