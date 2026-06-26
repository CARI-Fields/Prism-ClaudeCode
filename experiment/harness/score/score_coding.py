from __future__ import annotations

import hashlib
import json
import urllib.request


def task_id_for_kernel(reference_code: str, kernel_code: str, prefix: str = "exp") -> str:
    digest = hashlib.sha256()
    digest.update(reference_code.encode())
    digest.update(b"\0")
    digest.update(kernel_code.encode())
    return f"{prefix}_{digest.hexdigest()[:16]}"


def build_eval_request(reference_code: str, kernel_code: str, task_id: str) -> dict:
    return {
        "task_id": task_id,
        "reference_code": reference_code,
        "kernel_code": kernel_code,
        "entry_point": "Model",
        "backend": "triton",
        "workflow": "kernelbench",
    }


def normalize_eval_result(raw: dict) -> dict:
    correctness = bool(raw.get("correctness"))
    decoy = bool(raw.get("decoy_kernel"))
    return {
        "compiled": bool(raw.get("compiled", raw.get("correctness", False))),
        "correctness": correctness,
        "decoy_kernel": decoy,
        "speedup": raw.get("speedup"),
        "reference_runtime_ms": raw.get("reference_runtime"),
        "kernel_runtime_ms": raw.get("kernel_runtime"),
        "success": correctness and not decoy,
    }


def score_kernel(kernel_code: str, reference_code: str, kernel_url: str,
                 task_id: str | None = None) -> dict:
    task_id = task_id or task_id_for_kernel(reference_code, kernel_code)
    body = json.dumps(build_eval_request(reference_code, kernel_code, task_id)).encode()
    req = urllib.request.Request(f"{kernel_url}/evaluate", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=900) as resp:
        return normalize_eval_result(json.loads(resp.read()))
