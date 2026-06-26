import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient


def test_get_settings_reads_env(monkeypatch):
    from serve.config import get_settings
    monkeypatch.setenv("DATA_DIR", "/tmp/x")
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.app, https://b.app")
    s = get_settings()
    assert s.data_dir == "/tmp/x"
    assert s.api_token == "abc"
    assert s.allowed_origins == ["https://a.app", "https://b.app"]


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    pd.DataFrame({
        "run_id": ["r1", "r2"], "task": ["coding", "research"],
        "condition": ["single_agent", "subagents"], "rep": [1, 1],
        "success": [True, False], "speedup": [1.5, float("nan")],
    }).to_parquet(tmp_path / "runs.parquet")
    pd.DataFrame({
        "run_id": ["r1", "r1"], "request_index": [0, 1],
        "task": ["coding", "coding"], "condition": ["single_agent", "single_agent"],
        "rep": [1, 1], "input_tokens": [10, 20],
    }).to_parquet(tmp_path / "turns.parquet")
    pd.DataFrame({
        "run_id": ["r1"], "request_index": [0], "component": ["base system prompt"],
        "bytes": [100], "est_tokens": [25], "request_type": ["main-agent"],
        "task": ["coding"], "condition": ["single_agent"], "rep": [1],
    }).to_parquet(tmp_path / "components.parquet")
    pd.DataFrame({
        "run_id": ["r1", "r2"], "request_index": [0, 0],
        "component": ["base system prompt", "base system prompt"],
        "request_type": ["main-agent", "main-agent"], "text": ["hi", "yo"],
        "truncated": [False, False], "bytes": [2, 2], "stable": [True, True],
        "task": ["coding", "research"], "condition": ["single_agent", "subagents"],
        "rep": [1, 1],
    }).to_parquet(tmp_path / "component_texts.parquet")
    (tmp_path / "token_rates.json").write_text(json.dumps({"base system prompt": 0.21}))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("API_TOKEN", "secret123")
    return tmp_path


def test_get_runs(data_dir):
    from serve import queries
    rows = queries.get_runs()
    assert len(rows) == 2
    assert {r["run_id"] for r in rows} == {"r1", "r2"}


def test_nan_serialized_as_null(data_dir):
    from serve import queries
    rows = {r["run_id"]: r for r in queries.get_runs()}
    assert rows["r2"]["speedup"] is None  # NaN must become JSON null, not float('nan')


def test_component_texts_filters_by_run(data_dir):
    from serve import queries
    rows = queries.get_component_texts("r1")
    assert len(rows) == 1
    assert rows[0]["run_id"] == "r1"
    assert rows[0]["text"] == "hi"


def test_manifest_reuses_variants(data_dir):
    from serve import queries
    m = queries.get_manifest()
    assert {v["key"] for v in m["variants"]} == {"multi_agent", "long_horizon"}
    assert {a["condition"] for a in m["available"]} == {"single_agent", "subagents"}
    assert "single_agent" in m["strategy_desc"]


def test_require_token_rejects_missing(monkeypatch):
    from fastapi import HTTPException
    from serve.auth import require_token
    monkeypatch.setenv("API_TOKEN", "secret123")
    with pytest.raises(HTTPException) as exc:
        require_token(authorization=None)
    assert exc.value.status_code == 401


def test_require_token_accepts_match(monkeypatch):
    from serve.auth import require_token
    monkeypatch.setenv("API_TOKEN", "secret123")
    assert require_token(authorization="Bearer secret123") is None


def test_require_token_disabled_when_unset(monkeypatch):
    from serve.auth import require_token
    monkeypatch.setenv("API_TOKEN", "")
    assert require_token(authorization=None) is None


@pytest.fixture
def client(data_dir):
    from serve.app import app
    return TestClient(app)


def test_healthz_open(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_requires_token(client):
    assert client.get("/api/runs").status_code == 401


@pytest.mark.parametrize("path,params", [
    ("/api/manifest", {}),
    ("/api/runs", {}),
    ("/api/turns", {}),
    ("/api/components", {}),
    ("/api/component-texts", {"run_id": "r1"}),
    ("/api/token-rates", {}),
])
def test_all_api_routes_require_token(client, path, params):
    assert client.get(path, params=params).status_code == 401


def test_runs_endpoint_with_token(client):
    r = client.get("/api/runs", headers={"Authorization": "Bearer secret123"})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_component_texts_query_param(client):
    r = client.get(
        "/api/component-texts",
        params={"run_id": "r1"},
        headers={"Authorization": "Bearer secret123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1 and body[0]["run_id"] == "r1"


def test_manifest_endpoint(client):
    r = client.get("/api/manifest", headers={"Authorization": "Bearer secret123"})
    assert r.status_code == 200
    assert {v["key"] for v in r.json()["variants"]} == {"multi_agent", "long_horizon"}


def test_clean_recurses_into_nested():
    from serve.queries import _clean
    assert _clean(float("nan")) is None
    assert _clean(1.5) == 1.5
    assert _clean([1.0, float("inf"), 2.0]) == [1.0, None, 2.0]
    assert _clean({"a": float("nan"), "b": 2}) == {"a": None, "b": 2}


def test_get_turns(data_dir):
    from serve import queries
    rows = queries.get_turns()
    assert len(rows) == 2 and rows[0]["run_id"] == "r1"


def test_get_components(data_dir):
    from serve import queries
    rows = queries.get_components()
    assert len(rows) == 1 and rows[0]["component"] == "base system prompt"


def test_get_token_rates(data_dir):
    from serve import queries
    rates = queries.get_token_rates()
    assert rates == {"base system prompt": 0.21}
