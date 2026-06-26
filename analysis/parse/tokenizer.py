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


def fit_category_token_rates(
    bytes_by_request: list[dict[str, float]],
    totals: list[float],
    min_requests: int = 8,
) -> dict[str, float]:
    """Reverse-engineer per-category tokens-per-byte from captured ground truth.

    Each request gives a vector of per-category byte sizes and its EXACT total token
    count (from the API usage). A non-negative least-squares fit over all requests
    recovers a tokens-per-byte coefficient per category — capturing that, e.g., dense
    tool-definition JSON tokenizes at a different rate than English prose. Callers then
    weight each category's bytes by its coefficient before `scale_to_total`, so the
    per-request total stays exact while the split reflects real density.

    Returns ``{category: tokens_per_byte}``; an empty dict when the data is too sparse
    or the fit is degenerate, signalling the caller to fall back to uniform scaling.
    """
    pairs = [(r, t) for r, t in zip(bytes_by_request, totals)
             if t and sum(r.values()) > 0]
    if len(pairs) < min_requests:
        return {}
    categories = sorted({c for r, _ in pairs for c in r})
    if not categories:
        return {}
    try:
        import numpy as np
    except Exception:
        return {}
    X = np.array([[float(r.get(c, 0.0)) for c in categories] for r, _ in pairs], dtype=float)
    y = np.array([float(t) for _, t in pairs], dtype=float)
    try:
        from scipy.optimize import nnls
        coef, _ = nnls(X, y)
    except Exception:
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        coef = np.clip(coef, 0.0, None)  # clamp collinearity-driven negatives
    if not np.any(coef > 0):
        return {}
    return {c: float(v) for c, v in zip(categories, coef)}
