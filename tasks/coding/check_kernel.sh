#!/usr/bin/env bash
# Self-test tool given to the agent. Usage: check_kernel.sh <solution.py>
# Scores the kernel against the task reference via KernelGYM and prints the verdict.
set -euo pipefail
SOL="$1"
DRPY="${DRKERNEL_PY:-/home/yubaifeng/e84381970/envs/drkernel310/bin/python3.10}"
URL="${KERNELGYM_URL:-http://127.0.0.1:10908}"
REF="$(dirname "$0")/reference_code.py"
"$DRPY" - "$SOL" "$REF" "$URL" <<'PY'
import json, sys, urllib.request
sol, ref, url = sys.argv[1], sys.argv[2], sys.argv[3]
body = json.dumps({"task_id":"selftest","reference_code":open(ref).read(),
    "kernel_code":open(sol).read(),"entry_point":"Model","backend":"triton",
    "workflow":"kernelbench"}).encode()
req = urllib.request.Request(url+"/evaluate", data=body,
    headers={"Content-Type":"application/json"}, method="POST")
r = json.loads(urllib.request.urlopen(req, timeout=900).read())
print(f"compiled={r.get('compiled')} correctness={r.get('correctness')} "
      f"decoy={r.get('decoy_kernel')} speedup={r.get('speedup')}")
PY
