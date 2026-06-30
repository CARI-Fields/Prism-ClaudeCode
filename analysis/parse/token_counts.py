"""Per-block token counts, deduplicated by content hash.

Context blocks repeat heavily across a run's requests (the system prompt, tool
definitions, CLAUDE.md, … are byte-identical every turn). Counting tokens per
*unique* block — keyed by a content hash — turns ~180k block occurrences into a
few thousand distinct counts. A ``TokenCounter`` wraps an optional exact counter
(e.g. the Claude ``count_tokens`` endpoint); on a cache miss it calls the counter,
and if that fails (offline, no key) it falls back to a deterministic byte/char
estimate so the pipeline always produces stable, repeatable numbers.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from analysis.parse.tokenizer import estimate_tokens

COUNT_TOKENS_URL = "https://api.anthropic.com/v1/messages/count_tokens"


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


class TokenCounter:
    """Resolve token counts for text blocks, deduped by content hash.

    ``counter`` is an optional ``(text) -> int`` callable (typically the Claude
    token-counting API). Results are memoized by hash; a preloaded ``cache`` lets
    a build reuse counts persisted from earlier runs. If ``counter`` is absent or
    raises, a deterministic ``estimate_tokens`` (≈ chars / 4) is used instead.
    """

    def __init__(self, counter=None, cache: dict | None = None):
        self._counter = counter
        self._cache: dict[str, int] = dict(cache or {})
        self.api_calls = 0  # underlying-counter invocations (telemetry / tests)

    def count(self, text: str) -> int:
        if not text:
            return 0
        h = text_hash(text)
        if h in self._cache:
            return self._cache[h]
        if self._counter is not None:
            try:
                self.api_calls += 1
                n = int(self._counter(text))
                self._cache[h] = n  # cache only exact counts, never the fallback
                return n
            except Exception:
                pass  # network/credential failure → deterministic fallback
        return estimate_tokens(text)

    @property
    def cache(self) -> dict[str, int]:
        return dict(self._cache)


def make_count_tokens_api(model: str, api_key: str | None = None):
    """Build a ``(text) -> int`` counter backed by the Claude ``count_tokens``
    endpoint, or ``None`` when no API key is available (caller falls back to the
    deterministic estimate). The endpoint is free; counts are model-specific."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    import httpx

    client = httpx.Client(timeout=30.0)

    def counter(text: str) -> int:
        resp = client.post(
            COUNT_TOKENS_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": model, "messages": [{"role": "user", "content": text}]},
        )
        resp.raise_for_status()
        return int(resp.json()["input_tokens"])

    return counter


def load_token_cache(path) -> dict[str, int]:
    p = Path(path)
    if not p.exists():
        return {}
    return {k: int(v) for k, v in json.loads(p.read_text()).items()}


def save_token_cache(path, cache: dict[str, int]) -> None:
    Path(path).write_text(json.dumps(cache))


def load_dotenv(path) -> None:
    """Populate ``os.environ`` from a simple ``KEY=VALUE`` ``.env`` file without
    overwriting variables already set in the real environment. Dependency-free:
    skips blank lines and ``#`` comments, tolerates an ``export`` prefix, and
    strips one layer of matching surrounding quotes. A missing file is a no-op."""
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key:
            os.environ.setdefault(key, val)
