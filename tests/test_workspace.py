from pathlib import Path
from harness.workspace import restore_workspace

def test_restore_workspace_replaces_live_with_seed(tmp_path: Path):
    seed = tmp_path / "seed"; seed.mkdir()
    (seed / "stack.py").write_text("# TODO")
    live = tmp_path / "live"; live.mkdir()
    (live / "stack.py").write_text("done by a previous run")
    (live / "junk.txt").write_text("stale")
    restore_workspace(seed, live)
    assert (live / "stack.py").read_text() == "# TODO"
    assert not (live / "junk.txt").exists()
