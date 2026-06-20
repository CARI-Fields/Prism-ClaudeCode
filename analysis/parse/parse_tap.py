from __future__ import annotations

import json
from datetime import datetime

from analysis.parse.tokenizer import scale_to_total


def parse_iso(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def _usage(turn: dict) -> dict:
    return (turn.get("response") or {}).get("usage") or {}


def tap_turns(tap: list) -> list[dict]:
    rows = []
    for i, turn in enumerate(tap):
        u = _usage(turn)
        cc = u.get("cache_creation") or {}
        ts = turn.get("timestamp")
        dur = turn.get("duration_ms") or 0
        start = parse_iso(ts) - dur / 1000 if ts else None
        rows.append({
            "request_index": i,
            "ts_start_epoch": start,
            "input_tokens": u.get("input_tokens", 0),
            "output_tokens": u.get("output_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "cache_creation_5m": cc.get("ephemeral_5m_input_tokens", 0),
            "cache_creation_1h": cc.get("ephemeral_1h_input_tokens", 0),
            "duration_ms": dur,
            "model": turn.get("model"),
        })
    return rows


def _component_bytes(value) -> int:
    """Size of a request component (system/tools/messages). Handles inline content
    and claude-tap blob references (which carry a 'bytes' field)."""
    if value is None:
        return 0
    if isinstance(value, dict) and "__claude_tap_blob_ref__" in value:
        return int(value["__claude_tap_blob_ref__"].get("bytes", 0))
    if isinstance(value, list):
        return sum(_component_bytes(v) for v in value)
    return len(json.dumps(value, ensure_ascii=False))


def tap_components(tap: list) -> list[dict]:
    rows = []
    for i, turn in enumerate(tap):
        u = _usage(turn)
        prompt = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                  + u.get("cache_creation_input_tokens", 0))
        sizes = {
            "system_prompt": float(_component_bytes(turn.get("system"))),
            "tools": float(_component_bytes(turn.get("tools"))),
            "messages": float(_component_bytes(turn.get("messages"))),
        }
        est = scale_to_total(sizes, prompt)
        for comp in ("system_prompt", "tools", "messages"):
            rows.append({"request_index": i, "component": comp,
                         "bytes": int(sizes[comp]), "est_tokens": est[comp]})
    return rows
