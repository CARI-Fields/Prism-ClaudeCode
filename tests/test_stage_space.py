import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_stage_space_builds_clean_context(tmp_path):
    dest = tmp_path / "space"
    subprocess.run(
        ["bash", str(REPO / "scripts" / "stage_space.sh"), str(dest)],
        check=True,
    )
    must_exist = [
        "Dockerfile", "README.md", "requirements.txt",
        "web/__init__.py", "web/api/app.py", "web/api/export.py", "web/api/queries.py",
        "analysis/__init__.py", "analysis/report_variants.py",
        "experiment/tasks/coding/prompt.md", "experiment/tasks/research/prompt.md",
        "experiment/tasks/coding_longhorizon/prompt.md",
        "experiment/tasks/research_longhorizon/prompt.md",
    ]
    for rel in must_exist:
        assert (dest / rel).is_file(), f"missing {rel}"
    # No bytecode artifacts.
    assert not list(dest.rglob("__pycache__")), "staged __pycache__"
    assert not list(dest.rglob("*.pyc")), "staged .pyc"
    # Root files are NOT duplicated under web/api.
    assert not (dest / "web" / "api" / "Dockerfile").exists()


def test_stage_space_clears_stale_modules(tmp_path):
    dest = tmp_path / "space"
    (dest / "web" / "api").mkdir(parents=True)
    stale = dest / "web" / "api" / "old_removed.py"
    stale.write_text("# stale module from a previous deploy\n")
    subprocess.run(
        ["bash", str(REPO / "scripts" / "stage_space.sh"), str(dest)],
        check=True,
    )
    assert not stale.exists(), "stale web/api/*.py should be cleared before staging"
    assert (dest / "web" / "api" / "app.py").is_file()
