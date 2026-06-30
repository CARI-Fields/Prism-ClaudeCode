from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from analysis.parse.parse_tap import (
    tap_turns, tap_components, tap_component_texts, drop_empty_turns,
)
from analysis.parse.token_counts import (
    TokenCounter, make_count_tokens_api, load_token_cache, save_token_cache,
)
from analysis.parse.parse_ttft import load_ttft, join_ttft
from analysis.parse.parse_meta import run_summary
from analysis.pricing import enrich_turn_costs, token_cost_summary
from analysis.research_rubric import score_research_report


def cache_summary(turns: list[dict]) -> dict:
    # Hit rate over the raw, as-observed token counts: every reported cache read
    # is counted, including the warm cache inherited from a shared system-prompt
    # prefix on a run's first request. No warm-start baseline is subtracted.
    total_in = sum(t["input_tokens"] for t in turns)
    total_cr = sum(t["cache_read"] for t in turns)
    total_cc = sum(t["cache_creation_5m"] + t["cache_creation_1h"] for t in turns)
    denom = total_in + total_cr + total_cc

    return {
        "total_input": total_in,
        "total_cache_read": total_cr,
        "total_cache_creation": total_cc,
        "cache_hit_ratio": (total_cr / denom) if denom else 0.0,
    }


def build_run(run_dir: Path, token_counter: TokenCounter | None = None):
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "run_meta.json").read_text())
    tap_files = sorted((run_dir / "tap").glob("*.json"))
    tap = []
    for f in tap_files:
        tap.extend(json.loads(f.read_text()))
    tap.sort(key=lambda t: t.get("timestamp") or "")
    # Drop aborted / empty-usage responses before indexing so request_index, num_requests,
    # and every per-request curve count only real (token-bearing) model requests.
    tap = drop_empty_turns(tap)
    turns = join_ttft(tap_turns(tap), load_ttft(run_dir / "ttft" / "ttft.jsonl"))
    turns = enrich_turn_costs(turns, meta.get("model"))
    comps = tap_components(tap, token_counter)
    comp_texts = tap_component_texts(tap)
    comp_texts_full = tap_component_texts(tap, max_chars=None)
    run_id = run_dir.name
    stamp = {"run_id": run_id, "task": meta.get("task"),
             "condition": meta.get("condition"), "rep": meta.get("rep")}
    for r in turns:
        r.update(stamp)
    for c in comps:
        c.update(stamp)
    for x in comp_texts:
        x.update(stamp)
    for x in comp_texts_full:
        x.update(stamp)
    summary = run_summary(meta, run_dir)
    summary["run_id"] = run_id
    cache = cache_summary(turns)
    costs = token_cost_summary(turns, meta.get("model"))
    summary.update({
        "num_requests": len(turns),
        **cache,
        **costs,
        "peak_prompt_tokens": max((t["input_tokens"] + t["cache_read"]
                                   + t["cache_creation_5m"] + t["cache_creation_1h"]
                                   for t in turns), default=0),
        "output_tokens_total": sum(t["output_tokens"] for t in turns),
    })
    if summary.get("task") == "research":
        summary.update(score_research_report(run_dir / "workspace" / "report.md"))
    summary.update(_quality_summary(summary))
    return turns, comps, summary, comp_texts, comp_texts_full


def _quality_summary(summary: dict) -> dict:
    cost = _number(summary.get("total_cost_usd"))
    task = summary.get("task")
    if task == "coding":
        speedup = _number(summary.get("speedup"))
        quality = speedup if bool(summary.get("success")) else 0.0
        return {
            "quality_metric": "speedup",
            "coding_quality_score": quality,
            "quality_score": quality,
            "speedup_per_dollar": _safe_div(quality, cost),
            "cost_efficiency_score": _safe_div(quality, cost),
        }
    if task == "research":
        quality = _number(summary.get("research_rubric_score"))
        return {
            "quality_metric": "research_rubric_score",
            "research_quality_score": quality,
            "quality_score": quality,
            "research_score_per_dollar": _safe_div(quality, cost),
            "cost_efficiency_score": _safe_div(quality, cost),
        }
    return {
        "quality_metric": None,
        "quality_score": None,
        "cost_efficiency_score": None,
    }


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _number(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_model(raw_dir: Path) -> str | None:
    for d in sorted(raw_dir.iterdir()):
        meta = d / "run_meta.json"
        if meta.exists():
            try:
                return json.loads(meta.read_text()).get("model")
            except Exception:
                return None
    return None


def _build_token_counter(raw_dir: Path, out_dir: Path) -> TokenCounter:
    """Counter for a full build: reuse the persisted hash→token cache, and call
    the (free) Claude count_tokens endpoint when CC_COUNT_TOKENS is set and a key
    is available — otherwise fall back to the deterministic byte/char estimate.
    Counts use one tokenizer for the whole dataset (cross-run consistency)."""
    cache = load_token_cache(out_dir / "token_cache.json")
    api = None
    if os.environ.get("CC_COUNT_TOKENS"):
        api = make_count_tokens_api(_first_model(raw_dir) or "claude-opus-4-8")
    return TokenCounter(counter=api, cache=cache)


def build_all(raw_dir: Path, out_dir: Path,
              token_counter: TokenCounter | None = None) -> dict:
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not raw_dir.exists():
        return {"turns": 0, "components": 0, "runs": 0}
    counter = token_counter if token_counter is not None else _build_token_counter(raw_dir, out_dir)
    all_turns, all_comps, all_runs, all_texts, all_texts_full = [], [], [], [], []
    for d in sorted(raw_dir.iterdir()):
        if not (d / "run_meta.json").exists():
            continue
        try:
            t, c, r, x, xf = build_run(d, token_counter=counter)
        except Exception as exc:
            print(f"skip {d.name}: {exc}")
            continue
        all_turns += t; all_comps += c; all_runs.append(r); all_texts += x; all_texts_full += xf
    if not all_runs:
        return {"turns": 0, "components": 0, "runs": 0}
    pd.DataFrame(all_turns).to_parquet(out_dir / "turns.parquet")
    pd.DataFrame(all_comps).to_parquet(out_dir / "components.parquet")
    pd.DataFrame(all_runs).to_parquet(out_dir / "runs.parquet")
    pd.DataFrame(all_texts).to_parquet(out_dir / "component_texts.parquet")
    pd.DataFrame(all_texts_full).to_parquet(out_dir / "component_texts_full.parquet")
    save_token_cache(out_dir / "token_cache.json", counter.cache)
    return {"turns": len(all_turns), "components": len(all_comps),
            "runs": len(all_runs), "component_texts": len(all_texts),
            "component_texts_full": len(all_texts_full)}
