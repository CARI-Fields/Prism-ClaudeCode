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
