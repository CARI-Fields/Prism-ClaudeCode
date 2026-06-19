from pathlib import Path
from harness.config import ExperimentConfig
from harness.runner import iter_cells
import harness.runner as R


def test_iter_cells_full_factorial():
    exp = ExperimentConfig(
        model="claude-sonnet-4-6", reps=3,
        conditions=["single_agent", "subagents", "ralph_loop",
                    "dynamic_workflow", "loop_dynamic"],
        tasks=["coding", "research"],
        data_raw=Path("data/raw"), claude_projects=Path("~/.claude/projects"),
        proxy_host="127.0.0.1", proxy_port=8080,
    )
    cells = iter_cells(exp)
    assert len(cells) == 30
    assert ("coding", "single_agent", 1) in cells
    assert ("research", "loop_dynamic", 3) in cells
    # reps are 1-indexed
    assert min(r for _, _, r in cells) == 1
    assert max(r for _, _, r in cells) == 3


def test_main_all_isolates_cell_failures(monkeypatch):
    import harness.runner as R
    written = []

    def fake_execute(plan, exp, *, dry_run=False):
        if plan.task.name == "coding" and plan.condition.name == "subagents" and plan.rep == 1:
            raise RuntimeError("boom")
        return plan.run_dir

    monkeypatch.setattr(R, "execute", fake_execute)
    monkeypatch.setattr(R, "write_run_meta", lambda rd, meta: written.append(meta) or rd)

    rc = R.main(["--all"])
    assert rc == 0
    assert any(m.get("status") == "failed" for m in written)
    assert any(m.get("run_id", "").startswith("coding__subagents__01__") for m in written)
