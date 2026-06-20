from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough local token estimate (~4 chars/token). Used for relative composition;
    callers anchor totals to reported usage via scale_to_total."""
    return len(text or "") // 4


def scale_to_total(parts: dict[str, float], total: int) -> dict[str, int]:
    """Scale part sizes so they sum to `total` (largest-remainder rounding)."""
    s = sum(parts.values())
    if s <= 0:
        return {k: 0 for k in parts}
    raw = {k: v / s * total for k, v in parts.items()}
    out = {k: int(v) for k, v in raw.items()}
    rem = total - sum(out.values())
    for k in sorted(parts, key=lambda k: raw[k] - out[k], reverse=True):
        if rem <= 0:
            break
        out[k] += 1
        rem -= 1
    return out
