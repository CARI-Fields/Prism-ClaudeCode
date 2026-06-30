import os

from analysis.parse.token_counts import (
    TokenCounter, text_hash, make_count_tokens_api,
    load_token_cache, save_token_cache, load_dotenv,
)
from analysis.parse.tokenizer import estimate_tokens


def test_dedups_by_content_hash():
    calls = []

    def counter(text):
        calls.append(text)
        return 42

    tc = TokenCounter(counter=counter)
    assert tc.count("hello world") == 42
    assert tc.count("hello world") == 42  # second time served from cache
    assert len(calls) == 1  # underlying counter invoked only once


def test_falls_back_to_estimate_when_counter_raises():
    def boom(text):
        raise RuntimeError("no network")

    tc = TokenCounter(counter=boom)
    assert tc.count("a" * 40) == estimate_tokens("a" * 40)  # char//4 fallback


def test_uses_preloaded_cache_without_calling_counter():
    def counter(text):
        raise AssertionError("should not be called")

    h = text_hash("cached text")
    tc = TokenCounter(counter=counter, cache={h: 999})
    assert tc.count("cached text") == 999


def test_empty_text_is_zero():
    tc = TokenCounter(counter=lambda t: 7)
    assert tc.count("") == 0


def test_cache_property_exposes_resolved_counts_for_persistence():
    tc = TokenCounter(counter=lambda t: 5)
    tc.count("x")
    assert tc.cache == {text_hash("x"): 5}


def test_no_counter_uses_deterministic_estimate():
    tc = TokenCounter()  # no API counter -> pure offline fallback
    assert tc.count("a" * 80) == estimate_tokens("a" * 80)


def test_fallback_results_are_not_cached():
    # A later build with a real counter must not be served a stale estimate.
    tc = TokenCounter()  # no counter -> fallback path
    tc.count("abcd" * 10)
    assert tc.cache == {}


def test_make_count_tokens_api_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert make_count_tokens_api("claude-opus-4-8") is None


def test_token_cache_round_trip(tmp_path):
    path = tmp_path / "tc.json"
    save_token_cache(path, {"abc": 12, "def": 34})
    assert load_token_cache(path) == {"abc": 12, "def": 34}


def test_load_token_cache_missing_file_is_empty(tmp_path):
    assert load_token_cache(tmp_path / "nope.json") == {}


def test_load_dotenv_populates_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("FOO_X", raising=False)
    (tmp_path / ".env").write_text("FOO_X=bar\n")
    load_dotenv(tmp_path / ".env")
    assert os.environ["FOO_X"] == "bar"


def test_load_dotenv_does_not_overwrite_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("FOO_Y", "keep")
    (tmp_path / ".env").write_text("FOO_Y=changed\n")
    load_dotenv(tmp_path / ".env")
    assert os.environ["FOO_Y"] == "keep"


def test_load_dotenv_ignores_comments_blanks_and_strips_quotes(tmp_path, monkeypatch):
    for k in ("FOO_A", "FOO_B"):
        monkeypatch.delenv(k, raising=False)
    (tmp_path / ".env").write_text(
        "# a comment\n\nexport FOO_A='hello'\nFOO_B=\"world\"\nnot a var line\n"
    )
    load_dotenv(tmp_path / ".env")
    assert os.environ["FOO_A"] == "hello"
    assert os.environ["FOO_B"] == "world"


def test_load_dotenv_missing_file_is_noop(tmp_path):
    load_dotenv(tmp_path / "nope.env")  # must not raise
