Write a compact technical report to `report.md` surveying GPU kernel
optimization for LLM inference. This is a bounded experiment task: finish in
one foreground pass and avoid any long-running or background deep-research
workflow.

Operational constraints:
- Write `report.md` early, then update it in place.
- Keep the report concise: about 900-1400 words.
- Do not launch background research workflows. If this experiment condition
  asks you to use subagents or a workflow, use at most two short foreground
  delegated tasks, wait for them, then synthesize the report yourself.
- Use only enough source lookup to provide citations. If search is slow or
  unnecessary, cite well-known public URLs from memory rather than doing
  exhaustive verification.
- Do not spend time adversarially verifying sources.

`report.md` must contain these exact six section headings, each with a short
paragraph or 2-3 bullets and exactly two source URLs:

1. `## FlashAttention`
2. `## Quantized GEMM`
3. `## KV-cache`
4. `## Triton vs CUDA`
5. `## Hardware`
6. `## Autotuning`

Before finishing, check that `report.md` exists and contains:
- all six required section headings above,
- at least 12 distinct `http` or `https` source URLs total.
