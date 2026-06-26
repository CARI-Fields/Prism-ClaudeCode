import math
import harness.score.score_coding as SC
from harness.score.score_coding import score_gauntlet
from analysis.research_rubric import score_research_text, LONGHORIZON_SECTIONS, PROFILES


def _seed_gauntlet(tmp_path, n=4):
    for k in range(1, n + 1):
        (tmp_path / f"reference_{k}.py").write_text(f"# ref {k}\n")
        (tmp_path / f"solution_{k}.py").write_text(f"# sol {k}\n")
    return tmp_path


def test_gauntlet_geomean_and_pass(tmp_path, monkeypatch):
    _seed_gauntlet(tmp_path)
    speeds = {1: 1.5, 2: 2.0, 3: 4.0, 4: 3.0}  # geomean ~2.45, all 4 correct -> pass
    monkeypatch.setattr(SC, "score_kernel", lambda kc, rc, url, task_id=None: {
        "success": True, "correctness": True, "decoy_kernel": False,
        "speedup": speeds[int(task_id[8])] if task_id else 2.0,
    })
    out = score_gauntlet(tmp_path, "http://x")
    assert out["passing_kernels"] == 4
    assert math.isclose(out["geomean_speedup"], (1.5 * 2.0 * 4.0 * 3.0) ** 0.25, rel_tol=1e-9)
    assert out["speedup"] == out["geomean_speedup"]      # flows through coding-quality pipeline
    assert out["success"] is True


def test_gauntlet_passes_when_all_correct_below_target(tmp_path, monkeypatch):
    # Every kernel compiles + is correct but the geomean (1.72) is below the 2.0 target.
    # Success no longer gates on the target: a net speedup with all kernels passing wins.
    _seed_gauntlet(tmp_path)
    speeds = {1: 2.183, 2: 3.175, 3: 0.953, 4: 1.318}  # geomean ~1.72 (the goal r1 case)
    monkeypatch.setattr(SC, "score_kernel", lambda kc, rc, url, task_id=None: {
        "success": True, "correctness": True, "decoy_kernel": False,
        "speedup": speeds[int(task_id[8])] if task_id else 1.0,
    })
    out = score_gauntlet(tmp_path, "http://x")
    assert out["passing_kernels"] == 4 and out["num_kernels"] == 4
    assert out["geomean_speedup"] < out["target_speedup"]   # below the displayed 2.0 target
    assert out["success"] is True                           # ...but still a success


def test_gauntlet_fails_if_any_kernel_bad(tmp_path, monkeypatch):
    _seed_gauntlet(tmp_path)
    def fake(kc, rc, url, task_id=None):
        k = int(task_id[8])
        return {"success": k != 3, "correctness": k != 3, "decoy_kernel": False,
                "speedup": 5.0 if k != 3 else None}
    monkeypatch.setattr(SC, "score_kernel", fake)
    out = score_gauntlet(tmp_path, "http://x")
    assert out["passing_kernels"] == 3 and out["success"] is False  # not all 4 passed


def test_gauntlet_missing_solution(tmp_path, monkeypatch):
    _seed_gauntlet(tmp_path)
    (tmp_path / "solution_2.py").unlink()
    monkeypatch.setattr(SC, "score_kernel", lambda kc, rc, url, task_id=None: {
        "success": True, "correctness": True, "decoy_kernel": False, "speedup": 3.0})
    out = score_gauntlet(tmp_path, "http://x")
    assert out["success"] is False and out["passing_kernels"] == 3


def test_longhorizon_rubric_profile_scores_new_sections():
    body = ("paged kv-cache continuous batching fp8 quantization tensor parallel "
            "speculative decoding. https://a.test/1 https://a.test/2\n")
    text = "".join(f"## {s}\n\n{body}\n" for s in LONGHORIZON_SECTIONS)
    out = score_research_text(text, LONGHORIZON_SECTIONS, prof=PROFILES["research_longhorizon"])
    assert out["research_sections_present"] == len(LONGHORIZON_SECTIONS)
    assert out["research_coverage_score"] > 0.9          # system sections hit all dimension groups
    assert out["research_rubric_score"] > 0
