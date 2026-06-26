from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from pathlib import Path


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


def gauntlet_success(passing_kernels: int | None, num_kernels: int | None) -> bool:
    """A gauntlet run succeeds when every kernel compiled and was correct (no decoys).
    The geomean `target` is reported as a tuning goal but does NOT gate pass/fail — an
    all-passing run is a success regardless of whether the geomean clears the target."""
    if not num_kernels or passing_kernels is None:
        return False
    return passing_kernels == num_kernels


def score_gauntlet(scratch_dir, kernel_url: str, n: int = 4, target: float = 2.0) -> dict:
    """Score the Triton kernel gauntlet: evaluate solution_k.py vs reference_k.py for
    k=1..n, and report per-kernel verdicts plus the geomean speedup over the kernels
    that compiled, were correct, and weren't decoys. `speedup` is set to the geomean
    so the run flows through the normal coding-quality pipeline."""
    scratch = Path(scratch_dir)
    kernels, speeds = [], []
    for k in range(1, n + 1):
        sol, ref = scratch / f"solution_{k}.py", scratch / f"reference_{k}.py"
        if not sol.exists() or not ref.exists():
            kernels.append({"kernel": k, "success": False, "reason": "missing files"})
            continue
        try:
            res = score_kernel(sol.read_text(), ref.read_text(), kernel_url,
                               task_id=task_id_for_kernel(ref.read_text(), sol.read_text(),
                                                          prefix=f"gauntlet{k}"))
        except Exception as exc:
            kernels.append({"kernel": k, "success": False, "reason": f"eval error: {exc}"})
            continue
        kernels.append({"kernel": k, **res})
        if res.get("success") and res.get("speedup"):
            speeds.append(float(res["speedup"]))
    geomean = math.exp(sum(math.log(s) for s in speeds) / len(speeds)) if speeds else 0.0
    success = gauntlet_success(len(speeds), n)
    return {
        "success": success,
        "speedup": geomean,
        "geomean_speedup": geomean,
        "passing_kernels": len(speeds),
        "num_kernels": n,
        "target_speedup": target,
        "kernels": kernels,
    }
