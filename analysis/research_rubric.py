from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


REQUIRED_SECTIONS = (
    "FlashAttention",
    "Quantized GEMM",
    "KV-cache",
    "Triton vs CUDA",
    "Hardware",
    "Autotuning",
)

SECTION_KEYWORD_GROUPS = {
    "FlashAttention": (
        ("flashattention", "flash attention"),
        ("attention",),
        ("memory", "io", "i/o"),
        ("tile", "tiling", "block"),
    ),
    "Quantized GEMM": (
        ("quant", "int8", "int4"),
        ("gemm", "matmul"),
        ("scale", "zero point", "zero-point", "group"),
    ),
    "KV-cache": (
        ("kv-cache", "kv cache", "key value", "key-value"),
        ("memory", "cache"),
        ("paged", "batch", "attention"),
    ),
    "Triton vs CUDA": (
        ("triton",),
        ("cuda",),
        ("kernel",),
        ("productivity", "performance", "control"),
    ),
    "Hardware": (
        ("gpu", "h100", "a100"),
        ("tensor core", "tensor cores"),
        ("memory bandwidth", "shared memory", "smem"),
    ),
    "Autotuning": (
        ("autotun", "auto-tun", "tune"),
        ("block", "tile"),
        ("benchmark", "search"),
    ),
}

_URL = re.compile(r"https?://[^\s)\]}>\"']+")
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+./-]*")

# Long-horizon research task (LLM inference-serving deep-dive): 8 systems + 2 synthesis.
LONGHORIZON_SECTIONS = (
    "vLLM", "TensorRT-LLM", "SGLang", "TGI", "LMDeploy",
    "DeepSpeed-MII", "llama.cpp", "MLC-LLM",
    "Comparison Matrix", "Tradeoffs & Recommendations",
)
# Each system section should cover these dimensions (coverage groups).
_SERVING_GROUPS = (
    ("kv-cache", "kv cache", "paged", "radix", "prefix cache"),
    ("batch", "batching", "scheduler", "scheduling", "in-flight", "continuous"),
    ("quant", "fp8", "int4", "int8", "awq", "gptq"),
    ("parallel", "tensor parallel", "pipeline", "disaggregat", "speculative"),
)
LONGHORIZON_KEYWORD_GROUPS = {
    s: _SERVING_GROUPS for s in LONGHORIZON_SECTIONS[:8]  # the 8 systems
}

# Rubric profiles. Defaults reproduce the original bounded-research scoring exactly.
PROFILES = {
    "research": dict(
        required_sections=REQUIRED_SECTIONS, keyword_groups=SECTION_KEYWORD_GROUPS,
        word_band=(900, 1400), url_target=12, section_url_exact=True, section_url_min=2,
    ),
    "research_longhorizon": dict(
        required_sections=LONGHORIZON_SECTIONS, keyword_groups=LONGHORIZON_KEYWORD_GROUPS,
        word_band=(3000, 4500), url_target=30, section_url_exact=False, section_url_min=2,
    ),
}


def score_research_report(
    report_path: Path,
    required_sections: Iterable[str] | None = None,
    profile: str = "research",
) -> dict:
    prof = PROFILES.get(profile, PROFILES["research"])
    required = list(required_sections) if required_sections is not None else list(prof["required_sections"])
    path = Path(report_path)
    if not path.exists():
        return _empty_score(False, required)
    return score_research_text(path.read_text(), required, prof=prof)


def score_research_text(
    text: str,
    required_sections: Iterable[str] = REQUIRED_SECTIONS,
    prof: dict | None = None,
) -> dict:
    prof = prof or PROFILES["research"]
    keyword_groups = prof["keyword_groups"]
    word_band = prof["word_band"]
    url_target = prof["url_target"]
    section_url_exact = prof["section_url_exact"]
    section_url_min = prof["section_url_min"]
    required = list(required_sections)
    sections = _extract_sections(text)
    present_sections = [section for section in required if section.lower() in sections]
    section_score = len(present_sections) / len(required) if required else 0.0

    exact_two_url_sections = 0
    coverage_scores = []
    for section in required:
        body = sections.get(section.lower(), "")
        n_urls = len(_unique_urls(body))
        if (n_urls == section_url_min) if section_url_exact else (n_urls >= section_url_min):
            exact_two_url_sections += 1
        if section in keyword_groups:   # only score coverage for sections that define dimensions
            coverage_scores.append(_coverage_score(section, body, keyword_groups) if body else 0.0)

    citation_balance_score = exact_two_url_sections / len(required) if required else 0.0
    coverage_score = sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0
    word_count = len(_WORD.findall(text or ""))
    word_count_score = _word_count_score(word_count, word_band)
    urls = _unique_urls(text)
    unique_url_score = min(1.0, len(urls) / url_target)
    format_score = (
        0.35 * section_score
        + 0.35 * citation_balance_score
        + 0.15 * unique_url_score
        + 0.15 * word_count_score
    )
    rubric_score = 100 * (
        0.35 * section_score
        + 0.30 * citation_balance_score
        + 0.25 * coverage_score
        + 0.10 * word_count_score
    )

    return {
        "research_exists": True,
        "research_word_count": word_count,
        "research_sections_present": len(present_sections),
        "research_unique_url_count": len(urls),
        "research_exact_two_url_sections": exact_two_url_sections,
        "research_section_score": section_score,
        "research_citation_balance_score": citation_balance_score,
        "research_unique_url_score": unique_url_score,
        "research_word_count_score": word_count_score,
        "research_coverage_score": coverage_score,
        "research_format_score": format_score,
        "research_rubric_score": rubric_score,
    }


def _empty_score(exists: bool, required: list[str]) -> dict:
    return {
        "research_exists": exists,
        "research_word_count": 0,
        "research_sections_present": 0,
        "research_unique_url_count": 0,
        "research_exact_two_url_sections": 0,
        "research_section_score": 0.0,
        "research_citation_balance_score": 0.0,
        "research_unique_url_score": 0.0,
        "research_word_count_score": 0.0,
        "research_coverage_score": 0.0,
        "research_format_score": 0.0,
        "research_rubric_score": 0.0,
    }


def _extract_sections(text: str) -> dict[str, str]:
    matches = list(_HEADING.finditer(text or ""))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        title = match.group(1).strip().strip("`").lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[title] = text[start:end]
    return sections


def _unique_urls(text: str) -> set[str]:
    return {match.rstrip(".,") for match in _URL.findall(text or "")}


def _coverage_score(section: str, text: str, keyword_groups: dict = SECTION_KEYWORD_GROUPS) -> float:
    groups = keyword_groups.get(section, ())
    if not groups:
        return 0.0
    lower = (text or "").lower()
    hits = sum(1 for group in groups if any(keyword in lower for keyword in group))
    return hits / len(groups)


def _word_count_score(word_count: int, band: tuple[int, int] = (900, 1400)) -> float:
    lo, hi = band
    if lo <= word_count <= hi:
        return 1.0
    if word_count < lo:
        return max(0.0, word_count / lo)
    return max(0.0, 1.0 - ((word_count - hi) / (hi * 0.5)))
