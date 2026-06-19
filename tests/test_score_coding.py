from harness.score.score_coding import build_eval_request, normalize_eval_result


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
