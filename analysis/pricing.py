from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelPricing:
    name: str
    input_per_mtok: float
    cache_creation_5m_per_mtok: float
    cache_creation_1h_per_mtok: float
    cache_read_per_mtok: float
    output_per_mtok: float


SONNET_46_PRICING = ModelPricing(
    name="Claude Sonnet 4.6",
    input_per_mtok=3.0,
    cache_creation_5m_per_mtok=3.75,
    cache_creation_1h_per_mtok=6.0,
    cache_read_per_mtok=0.30,
    output_per_mtok=15.0,
)


def pricing_for_model(model: str | None) -> ModelPricing:
    normalized = str(model or "").lower().replace("_", "-")
    if "sonnet" in normalized:
        return SONNET_46_PRICING
    # The experiment config is locked to Sonnet. Keep a deterministic fallback so
    # historical metadata that omits the model can still be analyzed.
    return SONNET_46_PRICING


def enrich_turn_costs(turns: list[dict[str, Any]], model: str | None) -> list[dict[str, Any]]:
    pricing = pricing_for_model(model)
    enriched = []
    for turn in turns:
        row = dict(turn)
        row.update(_cost_parts(row, pricing))
        row["pricing_model"] = pricing.name
        enriched.append(row)
    return enriched


def token_cost_summary(turns: list[dict[str, Any]], model: str | None) -> dict[str, Any]:
    pricing = pricing_for_model(model)
    input_tokens = _sum(turns, "input_tokens")
    cache_read = _sum(turns, "cache_read")
    cache_creation_5m = _sum(turns, "cache_creation_5m")
    cache_creation_1h = _sum(turns, "cache_creation_1h")
    output_tokens = _sum(turns, "output_tokens")

    costs = _cost_parts(
        {
            "input_tokens": input_tokens,
            "cache_read": cache_read,
            "cache_creation_5m": cache_creation_5m,
            "cache_creation_1h": cache_creation_1h,
            "output_tokens": output_tokens,
        },
        pricing,
    )
    return {
        "pricing_model": pricing.name,
        "billable_input_tokens": input_tokens,
        "billable_cache_read_tokens": cache_read,
        "billable_cache_creation_5m_tokens": cache_creation_5m,
        "billable_cache_creation_1h_tokens": cache_creation_1h,
        "billable_output_tokens": output_tokens,
        **costs,
    }


def _cost_parts(row: dict[str, Any], pricing: ModelPricing) -> dict[str, float]:
    input_tokens = _number(row.get("input_tokens"))
    cache_read = _number(row.get("cache_read"))
    cache_creation_5m = _number(row.get("cache_creation_5m"))
    cache_creation_1h = _number(row.get("cache_creation_1h"))
    output_tokens = _number(row.get("output_tokens"))
    input_cost = _mtok_cost(input_tokens, pricing.input_per_mtok)
    cache_read_cost = _mtok_cost(cache_read, pricing.cache_read_per_mtok)
    cache_creation_5m_cost = _mtok_cost(cache_creation_5m, pricing.cache_creation_5m_per_mtok)
    cache_creation_1h_cost = _mtok_cost(cache_creation_1h, pricing.cache_creation_1h_per_mtok)
    output_cost = _mtok_cost(output_tokens, pricing.output_per_mtok)
    return {
        "input_cost_usd": input_cost,
        "cache_read_cost_usd": cache_read_cost,
        "cache_creation_5m_cost_usd": cache_creation_5m_cost,
        "cache_creation_1h_cost_usd": cache_creation_1h_cost,
        "output_cost_usd": output_cost,
        "total_cost_usd": (
            input_cost
            + cache_read_cost
            + cache_creation_5m_cost
            + cache_creation_1h_cost
            + output_cost
        ),
    }


def _sum(turns: list[dict[str, Any]], key: str) -> int:
    return int(sum(_number(turn.get(key)) for turn in turns))


def _number(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _mtok_cost(tokens: float, price_per_mtok: float) -> float:
    return tokens * price_per_mtok / 1_000_000
