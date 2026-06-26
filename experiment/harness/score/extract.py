from __future__ import annotations

import re

_BLOCK = re.compile(r"```(?:\w+)?\s*\n?(.*?)```", re.DOTALL)


def extract_last_code_block(text: str) -> str | None:
    matches = _BLOCK.findall(text or "")
    return matches[-1].strip() if matches else None
