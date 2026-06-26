import json
from pathlib import Path

from experiment.harness.score.score_coding import (
    build_eval_request,
    normalize_eval_result,
    score_kernel,
    task_id_for_kernel,
)


def test_build_eval_request_shape():
    req = build_eval_request("REF", "KERN", "t1")
    assert req == {"task_id": "t1", "reference_code": "REF", "kernel_code": "KERN",
                   "entry_point": "Model", "backend": "triton", "workflow": "kernelbench"}


def test_normalize_success_rule():
    r = normalize_eval_result({"compiled": True, "correctness": True, "decoy_kernel": False,
                               "speedup": 1.8, "reference_runtime": 2.0, "kernel_runtime": 1.1})
    assert r["success"] is True and r["speedup"] == 1.8
    r2 = normalize_eval_result({"correctness": True, "decoy_kernel": True})
    assert r2["success"] is False


def test_task_id_for_kernel_is_content_addressed():
    first = task_id_for_kernel("REF", "KERN_A", prefix="exp")
    second = task_id_for_kernel("REF", "KERN_A", prefix="exp")
    changed = task_id_for_kernel("REF", "KERN_B", prefix="exp")

    assert first == second
    assert first.startswith("exp_")
    assert first != changed


def test_score_kernel_defaults_to_content_addressed_task_id(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps({
                "compiled": True,
                "correctness": True,
                "decoy_kernel": False,
                "speedup": 1.0,
            }).encode()

    def fake_urlopen(req, timeout):
        captured["payload"] = json.loads(req.data.decode())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    score_kernel("KERN", "REF", "http://kernelgym")

    assert captured["payload"]["task_id"] == task_id_for_kernel("REF", "KERN")
    assert captured["payload"]["task_id"] != "exp"


def test_check_kernel_uses_content_addressed_selftest_task_id():
    text = Path("experiment/tasks/coding/check_kernel.sh").read_text()

    assert '"task_id":"selftest"' not in text
    assert "hashlib.sha256" in text
    assert "selftest_" in text
