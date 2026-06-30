import importlib.util

import pytest


def _load_push_data():
    spec = importlib.util.spec_from_file_location("push_data", "scripts/push_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_push_uploads_data_files_plus_full_text(monkeypatch, tmp_path):
    from web.api.data_source import DATA_FILES, FULL_TEXT_FILE
    pd_mod = _load_push_data()
    for f in DATA_FILES + (FULL_TEXT_FILE,):
        (tmp_path / f).write_text("payload")

    uploaded = []

    class FakeApi:
        def __init__(self, token=None):
            pass

        def create_repo(self, **kwargs):
            pass

        def upload_file(self, path_or_fileobj, path_in_repo, repo_id, repo_type):
            uploaded.append(path_in_repo)

    monkeypatch.setattr(pd_mod, "HfApi", FakeApi)
    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")

    pd_mod.main([str(tmp_path)])

    assert FULL_TEXT_FILE in uploaded
    assert set(uploaded) == set(DATA_FILES) | {FULL_TEXT_FILE}


def test_push_errors_when_full_text_missing(monkeypatch, tmp_path):
    from web.api.data_source import DATA_FILES
    pd_mod = _load_push_data()
    for f in DATA_FILES:  # full-text file deliberately absent
        (tmp_path / f).write_text("payload")
    monkeypatch.setattr(pd_mod, "HfApi", lambda token=None: None)
    monkeypatch.setenv("HF_DATASET_REPO", "acme/ds")
    monkeypatch.setenv("HF_ACCESS_TOKEN", "tok")
    with pytest.raises(SystemExit):
        pd_mod.main([str(tmp_path)])
