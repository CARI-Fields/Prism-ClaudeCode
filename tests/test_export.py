import io
import json
import zipfile
from datetime import datetime, timezone

import pandas as pd
import pytest


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    pd.DataFrame({"run_id": ["r1", "r2"], "task": ["coding", "research"],
                  "condition": ["single_agent", "subagents"], "rep": [1, 1]}
                 ).to_parquet(tmp_path / "runs.parquet")
    pd.DataFrame({"run_id": ["r1", "r1"], "request_index": [1, 0],
                  "request_type": ["main-agent", "main-agent"],
                  "input_tokens": [20, 10]}).to_parquet(tmp_path / "turns.parquet")
    pd.DataFrame({"run_id": ["r1", "r1"], "request_index": [0, 0],
                  "component": ["base system prompt", "user input"],
                  "est_tokens": [25, 5], "bytes": [100, 20]}
                 ).to_parquet(tmp_path / "components.parquet")
    pd.DataFrame({"run_id": ["r1", "r2"], "request_index": [0, 0],
                  "component": ["base system prompt", "base system prompt"],
                  "text": ["hi", "yo"], "truncated": [False, False],
                  "bytes": [2, 2], "stable": [True, True]}
                 ).to_parquet(tmp_path / "component_texts.parquet")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return tmp_path


def _zip(data: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(data))


def test_known_run_ids(data_dir):
    from web.api import export
    assert export.known_run_ids() == {"r1", "r2"}


def test_run_jsonl_one_line_per_request_ordered_with_components(data_dir):
    from web.api import export
    lines = [json.loads(l) for l in export.run_jsonl("r1").splitlines()]
    assert [l["request_index"] for l in lines] == [0, 1]  # ordered by request_index
    first = lines[0]
    assert first["input_tokens"] == 10
    assert {c["component"] for c in first["components"]} == {"base system prompt", "user input"}
    assert first["components"][0].keys() >= {"component", "est_tokens", "bytes"}
    assert lines[1]["components"] == []  # request 1 has no components


def test_build_zip_structure_without_texts(data_dir):
    from web.api import export
    z = _zip(export.build_zip(["r1"], include_texts=False,
                              now=datetime(2026, 1, 2, tzinfo=timezone.utc)))
    names = set(z.namelist())
    assert "manifest.json" in names and "README.md" in names
    assert "runs/r1.jsonl" in names
    assert "runs/r1.texts.jsonl" not in names
    m = json.loads(z.read("manifest.json"))
    assert m["run_ids"] == ["r1"] and m["include_texts"] is False
    assert m["generated_at"] == "2026-01-02T00:00:00+00:00"


def test_build_zip_with_texts(data_dir):
    from web.api import export
    z = _zip(export.build_zip(["r1"], include_texts=True))
    assert "runs/r1.texts.jsonl" in set(z.namelist())
    texts = [json.loads(l) for l in z.read("runs/r1.texts.jsonl").decode().splitlines()]
    assert texts[0]["text"] == "hi"


def test_build_zip_drops_unknown_and_dedupes(data_dir):
    from web.api import export
    z = _zip(export.build_zip(["r1", "bogus", "r1"], include_texts=False))
    assert "runs/r1.jsonl" in set(z.namelist())
    assert "runs/bogus.jsonl" not in set(z.namelist())
    assert json.loads(z.read("manifest.json"))["run_ids"] == ["r1"]


def test_build_zip_empty_raises(data_dir):
    from web.api import export
    with pytest.raises(ValueError):
        export.build_zip(["bogus"], include_texts=False)
