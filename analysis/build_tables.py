from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from analysis.parse.parse_tap import (
    tap_turns, tap_components, tap_component_texts, drop_empty_turns,
)
from analysis.parse.parse_ttft import load_ttft, join_ttft
from analysis.parse.parse_meta import run_summary
from analysis.parse.tokenizer import fit_category_token_rates, scale_to_total
from analysis.pricing import enrich_turn_costs, token_cost_summary
from analysis.research_rubric import score_research_report
from harness.score.score_coding import gauntlet_success


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


def build_run(run_dir: Path):
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
    comps = tap_components(tap)
    comp_texts = tap_component_texts(tap)
    run_id = run_dir.name
    stamp = {"run_id": run_id, "task": meta.get("task"),
             "condition": meta.get("condition"), "rep": meta.get("rep")}
    for r in turns:
        r.update(stamp)
    for c in comps:
        c.update(stamp)
    for x in comp_texts:
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
    task_name = summary.get("task") or ""
    if task_name.startswith("research"):
        summary.update(score_research_report(run_dir / "workspace" / "report.md", profile=task_name))
    # Gauntlet runs (score carries num_kernels) no longer gate on the geomean target:
    # success == every kernel correct. Recompute from the stored per-kernel verdicts so
    # the report reflects the current criterion without re-scoring against KernelGYM.
    score = meta.get("score") or {}
    if score.get("num_kernels") is not None:
        summary["success"] = gauntlet_success(score.get("passing_kernels"), score.get("num_kernels"))
    summary.update(_quality_summary(summary))
    return turns, comps, summary, comp_texts


def _quality_summary(summary: dict) -> dict:
    cost = _number(summary.get("total_cost_usd"))
    task = summary.get("task") or ""
    if task.startswith("coding"):
        speedup = _number(summary.get("speedup"))
        quality = speedup if bool(summary.get("success")) else 0.0
        return {
            "quality_metric": "speedup",
            "coding_quality_score": quality,
            "quality_score": quality,
            "speedup_per_dollar": _safe_div(quality, cost),
            "cost_efficiency_score": _safe_div(quality, cost),
        }
    if task.startswith("research"):
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


def build_all(raw_dir: Path, out_dir: Path) -> dict:
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not raw_dir.exists():
        return {"turns": 0, "components": 0, "runs": 0}
    all_turns, all_comps, all_runs, all_texts = [], [], [], []
    for d in sorted(raw_dir.iterdir()):
        if not (d / "run_meta.json").exists():
            continue
        try:
            t, c, r, x = build_run(d)
        except Exception as exc:
            print(f"skip {d.name}: {exc}")
            continue
        all_turns += t; all_comps += c; all_runs.append(r); all_texts += x
    if not all_runs:
        return {"turns": 0, "components": 0, "runs": 0}
    comps_df = pd.DataFrame(all_comps)
    comps_df, token_rates = _recompute_est_tokens(comps_df)
    if token_rates:
        (out_dir / "token_rates.json").write_text(json.dumps(token_rates, indent=2))
    pd.DataFrame(all_turns).to_parquet(out_dir / "turns.parquet")
    comps_df.to_parquet(out_dir / "components.parquet")
    pd.DataFrame(all_runs).to_parquet(out_dir / "runs.parquet")
    pd.DataFrame(all_texts).to_parquet(out_dir / "component_texts.parquet")
    return {"turns": len(all_turns), "components": len(all_comps),
            "runs": len(all_runs), "component_texts": len(all_texts)}


def _recompute_est_tokens(comps_df: pd.DataFrame):
    """Replace the uniform byte-proportional `est_tokens` with a density-weighted split.

    Fits per-category tokens-per-byte across every request (the exact total is the sum
    of the existing uniform-scaled `est_tokens`), then for each request re-distributes
    that exact total by ``bytes × coef`` — keeping per-request totals exact while making
    the split density-aware. Falls back to the uniform values when the fit is degenerate
    (e.g. the sparse long-horizon framework). Returns (comps_df, token_rates)."""
    if comps_df.empty or not {"run_id", "request_index", "component", "bytes",
                              "est_tokens"} <= set(comps_df.columns):
        return comps_df, {}
    bytes_by_req: dict[tuple, dict[str, float]] = {}
    totals: dict[tuple, float] = {}
    for row in comps_df.itertuples():
        key = (row.run_id, row.request_index)
        bytes_by_req.setdefault(key, {})[row.component] = float(row.bytes or 0)
        totals[key] = totals.get(key, 0.0) + float(row.est_tokens or 0)
    keys = list(bytes_by_req)
    coef = fit_category_token_rates([bytes_by_req[k] for k in keys],
                                    [totals[k] for k in keys])
    if not coef:
        return comps_df, {}
    new_est: dict[tuple, int] = {}
    for key in keys:
        parts = bytes_by_req[key]
        weighted = {c: parts[c] * coef.get(c, 0.0) for c in parts}
        if sum(weighted.values()) <= 0:
            weighted = dict(parts)  # category has no fitted density — keep raw bytes
        for comp, val in scale_to_total(weighted, int(round(totals[key]))).items():
            new_est[(key[0], key[1], comp)] = val
    comps_df = comps_df.copy()
    comps_df["est_tokens"] = [
        new_est.get((r.run_id, r.request_index, r.component), r.est_tokens)
        for r in comps_df.itertuples()
    ]
    return comps_df, {c: round(v, 6) for c, v in coef.items()}
