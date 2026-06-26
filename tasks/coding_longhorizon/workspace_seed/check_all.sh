#!/usr/bin/env bash
# Self-test for the Triton kernel gauntlet. Usage: bash check_all.sh
# Evaluates solution_k.py against reference_k.py (k=1..4) via KernelGYM and prints
# per-kernel verdicts plus the geomean speedup and an ALL_PASS flag.
set -euo pipefail
DRPY="${DRKERNEL_PY:-/home/yubaifeng/e84381970/envs/drkernel310/bin/python3.10}"
URL="${KERNELGYM_URL:-http://127.0.0.1:10908}"
HERE="$(cd "$(dirname "$0")" && pwd)"
"$DRPY" - "$HERE" "$URL" <<'PY'
import hashlib, json, math, os, sys, urllib.request
here, url = sys.argv[1], sys.argv[2]
KERNELS = [
    ("1", "fused elementwise relu(x*scale+bias)"),
    ("2", "row-wise LayerNorm"),
    ("3", "tiled GEMM x@W"),
    ("4", "fused GEMM epilogue relu(x@W+bias)"),
]
TARGET = 2.0
speeds, all_ok = [], True
for k, desc in KERNELS:
    ref_path = os.path.join(here, f"reference_{k}.py")
    sol_path = f"solution_{k}.py"
    if not os.path.exists(sol_path):
        print(f"[{k}] {desc}: MISSING solution_{k}.py")
        all_ok = False
        continue
    rc, kc = open(ref_path).read(), open(sol_path).read()
    d = hashlib.sha256(); d.update(rc.encode()); d.update(b"\0"); d.update(kc.encode())
    body = json.dumps({
        "task_id": f"gauntlet_{k}_{d.hexdigest()[:12]}",
        "reference_code": rc, "kernel_code": kc,
        "entry_point": "Model", "backend": "triton", "workflow": "kernelbench",
    }).encode()
    req = urllib.request.Request(url + "/evaluate", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=900).read())
    except Exception as exc:
        print(f"[{k}] {desc}: EVAL_ERROR {exc}")
        all_ok = False
        continue
    comp, corr = r.get("compiled"), r.get("correctness")
    decoy, sp = r.get("decoy_kernel"), r.get("speedup")
    print(f"[{k}] {desc}: compiled={comp} correctness={corr} decoy={decoy} speedup={sp}")
    if comp and corr and not decoy and sp:
        speeds.append(float(sp))
    else:
        all_ok = False
geo = math.exp(sum(math.log(s) for s in speeds) / len(speeds)) if speeds else 0.0
done = all_ok and len(speeds) == len(KERNELS) and geo >= TARGET
print(f"GEOMEAN={geo:.3f} over {len(speeds)}/{len(KERNELS)} passing kernels (target {TARGET})")
print(f"ALL_PASS={'true' if done else 'false'}")
PY
