from pathlib import Path

import pytest

from web.api.data_source import DATA_FILES, ensure_data


def test_ensure_data_is_noop_without_repo(tmp_path):
    """Local dev: no HF dataset configured → never downloads, returns data_dir as-is."""
    calls = []
    out = ensure_data(
        tmp_path, repo="", token="tok", _download=lambda **k: calls.append(k)
    )
    assert out == tmp_path
    assert calls == []


def test_ensure_data_downloads_every_data_file_from_private_dataset(tmp_path):
    """With a dataset repo set, each required file is fetched into data_dir with the token."""
    seen = []

    def fake_download(repo, filename, token, dest):
        seen.append((repo, filename, token))
        Path(dest).write_text("payload")

    data_dir = tmp_path / "d"
    out = ensure_data(data_dir, repo="acme/ds", token="tok", _download=fake_download)

    assert out == data_dir
    assert {f for _, f, _ in seen} == set(DATA_FILES)
    assert all(repo == "acme/ds" and token == "tok" for repo, _, token in seen)
    assert all((data_dir / f).exists() for f in DATA_FILES)


def test_hf_download_pulls_from_dataset_repo_type_into_data_dir(tmp_path, monkeypatch):
    """The real downloader calls hf_hub_download with repo_type=dataset + local_dir."""
    import web.api.data_source as ds

    captured = {}

    def fake_hf_hub_download(**kwargs):
        captured.update(kwargs)
        p = Path(kwargs["local_dir"]) / kwargs["filename"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("payload")
        return str(p)

    monkeypatch.setattr(ds, "hf_hub_download", fake_hf_hub_download)
    ds._hf_download(
        repo="acme/ds", filename="runs.parquet", token="tok",
        dest=tmp_path / "runs.parquet",
    )

    assert captured["repo_id"] == "acme/ds"
    assert captured["repo_type"] == "dataset"
    assert captured["filename"] == "runs.parquet"
    assert captured["token"] == "tok"
    assert (tmp_path / "runs.parquet").exists()


def test_settings_expose_hf_dataset_config(monkeypatch):
    from web.api.config import get_settings

    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")
    s = get_settings()
    assert s.hf_dataset_repo == "acme/ds"
    assert s.hf_token == "tok"


def test_settings_hf_config_defaults_empty(monkeypatch):
    from web.api.config import get_settings

    monkeypatch.delenv("HF_DATASET_REPO", raising=False)
    monkeypatch.delenv("HF_ACCESS_TOKEN", raising=False)
    s = get_settings()
    assert s.hf_dataset_repo == ""
    assert s.hf_token == ""


def test_app_startup_pulls_data_from_configured_dataset(monkeypatch, tmp_path):
    """On startup the API fetches the data into DATA_DIR using the configured dataset/token."""
    from fastapi.testclient import TestClient

    import web.api.app as appmod

    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    captured = {}

    def fake_ensure(data_dir, repo="", token="", **kw):
        captured["args"] = (str(data_dir), repo, token)

    monkeypatch.setattr(appmod, "ensure_data", fake_ensure)
    with TestClient(appmod.app):
        pass
    assert captured["args"] == (str(tmp_path), "acme/ds", "tok")


def test_full_text_file_is_separate_from_startup_files():
    from web.api.data_source import DATA_FILES, FULL_TEXT_FILE
    assert FULL_TEXT_FILE == "component_texts_full.parquet"
    assert FULL_TEXT_FILE not in DATA_FILES


def test_ensure_full_texts_pulls_only_the_full_file(monkeypatch, tmp_path):
    import web.api.data_source as ds
    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    seen = []

    def fake_download(repo, filename, token, dest):
        seen.append((repo, filename, token))
        Path(dest).write_text("payload")

    ds.ensure_full_texts(_download=fake_download)
    assert [f for _, f, _ in seen] == [ds.FULL_TEXT_FILE]
    assert all(repo == "acme/ds" and token == "tok" for repo, _, token in seen)


def test_ensure_full_texts_noop_without_repo(monkeypatch, tmp_path):
    import web.api.data_source as ds
    monkeypatch.delenv("HF_DATASET_REPO", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    calls = []
    ds.ensure_full_texts(_download=lambda **k: calls.append(k))
    assert calls == []


def test_ensure_full_texts_skips_fetch_when_already_present(monkeypatch, tmp_path):
    import web.api.data_source as ds
    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / ds.FULL_TEXT_FILE).write_text("cached")
    calls = []
    ds.ensure_full_texts(_download=lambda **k: calls.append(k))
    assert calls == []
