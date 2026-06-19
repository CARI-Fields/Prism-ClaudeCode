Write a comprehensive technical report to `report.md` surveying GPU kernel
optimization for LLM inference (2023–2026). Include these six sections, each
with at least two cited sources (URLs) and concrete numbers where available,
plus a comparison table:

1. FlashAttention family (v1 → v3 and variants) — ideas and performance
2. Quantized GEMM kernels (FP8 / INT8 / INT4) for LLM matmuls
3. KV-cache / paged-attention kernels (e.g. PagedAttention)
4. Triton vs CUDA C++ vs CUTLASS / CuTe — productivity and performance tradeoffs
5. Hardware-specific features (Hopper TMA / wgmma, Blackwell FP4 / FP8, async copy)
6. Autotuning and compilers (Triton autotune, TVM, torch.compile / Inductor)

Use web search and cite at least 12 distinct source URLs total. Finish only
after `report.md` contains all six sections, the comparison table, and the citations.
