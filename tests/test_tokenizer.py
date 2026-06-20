from analysis.parse.tokenizer import estimate_tokens, scale_to_total


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
