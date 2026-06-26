from analysis.parse.tokenizer import (
    estimate_tokens, scale_to_total, fit_category_token_rates,
)


def test_estimate_tokens_chars_over_4():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 40) == 10


def test_scale_to_total_sums_to_total():
    parts = {"system": 30.0, "tools": 60.0, "messages": 10.0}
    out = scale_to_total(parts, total=1000)
    assert sum(out.values()) == 1000
    assert out["tools"] > out["system"] > out["messages"]


def test_scale_to_total_zero_parts():
    assert scale_to_total({"a": 0.0, "b": 0.0}, total=100) == {"a": 0, "b": 0}


def test_fit_category_token_rates_recovers_known_densities():
    # Synthesize requests with KNOWN per-category tokens/byte; the fit should recover them.
    rates = {"sys": 0.2, "tools": 0.25, "user": 0.4}
    requests, totals = [], []
    for i in range(40):
        b = {"sys": 1000 + i, "tools": 2000 + 50 * (i % 5), "user": 100 * (i % 7) + 50}
        requests.append(b)
        totals.append(sum(b[c] * rates[c] for c in b))
    coef = fit_category_token_rates(requests, totals)
    assert coef and set(coef) == set(rates)
    for c in rates:
        assert abs(coef[c] - rates[c]) < 0.02, (c, coef[c])


def test_fit_category_token_rates_sparse_returns_empty():
    # Below the minimum request count → empty (caller falls back to uniform scaling).
    assert fit_category_token_rates([{"a": 10.0}], [4.0]) == {}
