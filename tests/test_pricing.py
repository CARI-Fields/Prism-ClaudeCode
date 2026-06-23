import math

from analysis.pricing import enrich_turn_costs, token_cost_summary


def test_token_cost_summary_uses_sonnet_token_categories():
    turns = [
        {
            "input_tokens": 1_000_000,
            "cache_read": 2_000_000,
            "cache_creation_5m": 1_000_000,
            "cache_creation_1h": 500_000,
            "output_tokens": 100_000,
        }
    ]

    summary = token_cost_summary(turns, "claude-sonnet-4-6")

    assert summary["pricing_model"] == "Claude Sonnet 4.6"
    assert summary["billable_input_tokens"] == 1_000_000
    assert summary["billable_cache_read_tokens"] == 2_000_000
    assert summary["billable_cache_creation_5m_tokens"] == 1_000_000
    assert summary["billable_cache_creation_1h_tokens"] == 500_000
    assert summary["billable_output_tokens"] == 100_000
    assert math.isclose(summary["input_cost_usd"], 3.0)
    assert math.isclose(summary["cache_read_cost_usd"], 0.6)
    assert math.isclose(summary["cache_creation_5m_cost_usd"], 3.75)
    assert math.isclose(summary["cache_creation_1h_cost_usd"], 3.0)
    assert math.isclose(summary["output_cost_usd"], 1.5)
    assert math.isclose(summary["total_cost_usd"], 11.85)


def test_enrich_turn_costs_adds_per_request_costs_without_mutating_input():
    turns = [{"input_tokens": 1000, "cache_read": 1000, "output_tokens": 1000}]

    enriched = enrich_turn_costs(turns, "claude-sonnet-4-6")

    assert "total_cost_usd" not in turns[0]
    assert math.isclose(enriched[0]["input_cost_usd"], 0.003)
    assert math.isclose(enriched[0]["cache_read_cost_usd"], 0.0003)
    assert math.isclose(enriched[0]["output_cost_usd"], 0.015)
    assert math.isclose(enriched[0]["total_cost_usd"], 0.0183)
