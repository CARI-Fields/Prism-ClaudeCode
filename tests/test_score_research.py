from pathlib import Path
from experiment.harness.score.score_research import score_research, count_citations


def test_count_citations_distinct():
    text = "see https://a.com and https://a.com and http://b.org"
    assert count_citations(text) == 2


def test_score_research_success(tmp_path: Path):
    report = tmp_path / "report.md"
    urls = "\n".join(f"https://src{i}.com" for i in range(12))
    report.write_text("# FlashAttention\n# Quantized GEMM\n# KV-cache\n"
                      "# Triton vs CUDA\n# Hardware features\n# Autotuning\n" + urls)
    secs = ["FlashAttention", "Quantized GEMM", "KV-cache", "Triton vs CUDA",
            "Hardware features", "Autotuning"]
    r = score_research(report, secs, min_citations=12)
    assert r["success"] is True
    assert r["citation_count"] == 12 and r["sections_present"] == 6


def test_score_research_missing_report(tmp_path: Path):
    r = score_research(tmp_path / "nope.md", ["A"], min_citations=1)
    assert r["exists"] is False and r["success"] is False
