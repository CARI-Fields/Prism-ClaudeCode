from __future__ import annotations

import re
from pathlib import Path

_URL = re.compile(r"https?://[^\s)\]}>\"']+")


def count_citations(text: str) -> int:
    return len({m.rstrip(".,") for m in _URL.findall(text or "")})


def score_research(report_path: Path, required_sections: list[str],
                   min_citations: int = 12) -> dict:
    p = Path(report_path)
    if not p.exists():
        return {"exists": False, "sections_present": 0, "citation_count": 0, "success": False}
    text = p.read_text()
    low = text.lower()
    present = sum(1 for s in required_sections if s.lower() in low)
    cites = count_citations(text)
    success = present == len(required_sections) and cites >= min_citations
    return {"exists": True, "sections_present": present,
            "citation_count": cites, "success": success}
