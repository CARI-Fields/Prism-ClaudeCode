import shutil
from pathlib import Path
from analysis.report import generate


def _make_run(tmp):
    d = tmp / "data/raw/coding__single_agent__01__20260619T210033Z"
    (d / "tap").mkdir(parents=True); (d / "ttft").mkdir(); (d / "transcripts").mkdir()
    shutil.copy("tests/fixtures/real_cell/tap.json", d / "tap/s.json")
    shutil.copy("tests/fixtures/real_cell/ttft.jsonl", d / "ttft/ttft.jsonl")
    shutil.copy("tests/fixtures/real_cell/run_meta.json", d / "run_meta.json")


def test_generate_report(tmp_path):
    _make_run(tmp_path)
    rep = generate(tmp_path / "data/raw", tmp_path / "processed",
                   tmp_path / "figures", tmp_path / "report.md")
    text = Path(rep).read_text()
    assert "Prefix-cache" in text or "cache_accumulation" in text
    assert "| condition |" in text or "condition" in text
    assert (tmp_path / "figures" / "cache_accumulation.png").exists()
