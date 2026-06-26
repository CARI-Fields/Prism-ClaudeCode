from __future__ import annotations

import shutil
from pathlib import Path


def restore_workspace(seed: Path, live: Path) -> None:
    """Reset the live working dir to a pristine copy of the seed."""
    live = Path(live)
    if live.exists():
        shutil.rmtree(live)
    shutil.copytree(Path(seed), live)
