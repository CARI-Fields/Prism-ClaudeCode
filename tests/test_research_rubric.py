from pathlib import Path

from analysis.research_rubric import REQUIRED_SECTIONS, score_research_report


def _report_text() -> str:
    bodies = {
        "FlashAttention": "FlashAttention improves attention by tiling blocks to reduce memory IO.",
        "Quantized GEMM": "Quantized GEMM uses int8 matmul with group scales and zero points.",
        "KV-cache": "KV-cache stores key value tensors to reduce attention memory work with paged batching.",
        "Triton vs CUDA": "Triton and CUDA both produce kernels; CUDA exposes lower-level control while Triton improves productivity and performance iteration.",
        "Hardware": "GPU hardware such as H100 tensor cores depends on memory bandwidth and shared memory.",
        "Autotuning": "Autotuning searches block sizes and tile choices with benchmarks.",
    }
    sections = []
    for i, section in enumerate(REQUIRED_SECTIONS, start=1):
        sections.append(
            f"## {section}\n\n{bodies[section]}\n"
            f"https://example.com/{i}/a\nhttps://example.com/{i}/b\n"
        )
    return "\n".join(sections)


def test_score_research_report_counts_structure_citations_and_coverage(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text(_report_text())

    score = score_research_report(report)

    assert score["research_sections_present"] == 6
    assert score["research_unique_url_count"] == 12
    assert score["research_exact_two_url_sections"] == 6
    assert score["research_coverage_score"] == 1.0
    assert 0 < score["research_rubric_score"] <= 100


def test_score_research_report_penalizes_missing_sections(tmp_path: Path):
    report = tmp_path / "report.md"
    text = _report_text().replace("## Autotuning", "## Tuning")
    report.write_text(text)

    score = score_research_report(report)

    assert score["research_sections_present"] == 5
    assert score["research_exact_two_url_sections"] == 5
    assert score["research_rubric_score"] < 90
