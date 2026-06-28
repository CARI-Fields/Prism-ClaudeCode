Optimize a **gauntlet of four Triton kernels** of increasing difficulty. This is
a long-horizon task: you are expected to profile, iterate, and tune across many
rounds until all four kernels are correct and fast — not to make a single fix.

For each kernel `k`, a reference PyTorch module `Model` is provided in
`reference_k.py`. Write a Triton-accelerated `Model` (same class name, same
`get_inputs` / `get_init_inputs` contract) to `solution_k.py`:

- `solution_1.py` — fused elementwise `relu(x * scale + bias)`  (warm-up)
- `solution_2.py` — row-wise LayerNorm over the feature dim (reduction + numerical stability)
- `solution_3.py` — tiled GEMM `x @ W`  (the hard one — use shared-memory tiling)
- `solution_4.py` — fused GEMM epilogue `relu(x @ W + bias)`

Rules:
- The core math of each kernel MUST be a real `@triton.jit` kernel. PyTorch is
  allowed only for parameters, output allocation, and launch plumbing — not for
  the fused compute itself.
- `decoy_kernel` must be False for every kernel (no trivial/degenerate kernels).
- You ARE encouraged to profile and autotune here (block sizes, num_warps,
  tiling) — this is a performance task, iterate until the targets are met.

Self-test tool: run `bash check_all.sh` from this directory. It evaluates each
`solution_k.py` against `reference_k.py` via KernelGYM and prints, per kernel,
`compiled / correctness / decoy / speedup`, then a final
`GEOMEAN=<x> ... ALL_PASS=<true|false>` line.

Completion criteria — finish only when `check_all.sh` reports `ALL_PASS=true`,
which requires ALL of:
- all four `solution_k.py` exist;
- every kernel: `compiled=True`, `correctness=True`, `decoy=False`;
- geometric-mean speedup across the four kernels **≥ 2.0×**.

Work incrementally: get each kernel compiling and correct first, then tune for
speed. Re-run `check_all.sh` after changes and only stop when `ALL_PASS=true`.
