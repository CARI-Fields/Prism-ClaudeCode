import json
import sys
from pathlib import Path

SRC = "/home/yubaifeng/e84381970/drkernel-lab/distill/problems/problems_sample.jsonl"
NAME = "76_Gemm_Add_ReLU"
out = Path("tasks/coding")
out.mkdir(parents=True, exist_ok=True)
for line in open(SRC):
    p = json.loads(line)
    if p["name"] == NAME:
        (out / "prompt.md").write_text(p["prompt_text"])
        (out / "reference_code.py").write_text(p["reference_code"])
        print("wrote tasks/coding/{prompt.md,reference_code.py}")
        sys.exit(0)
print("problem not found", file=sys.stderr); sys.exit(1)
