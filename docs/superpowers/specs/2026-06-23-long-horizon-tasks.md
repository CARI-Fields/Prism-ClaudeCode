# Long-horizon tasks for the goal / ralph_loop re-run

Recorded 2026-06-23. Purpose: re-run the `goal` and `ralph_loop` conditions on
**harder, long-horizon** workloads that exercise long trajectories and make the
**context cycle** (Claude Code auto-compaction: grow → compact → rebuild) visible
in the prefix-cache-accumulation / context-growth telemetry. Model: Sonnet
(`claude-sonnet-4-6`), as before. Matrix: 2 conditions (goal, ralph_loop) × 2
tasks (coding, research).

## Task 1 — coding: Triton kernel gauntlet
- Files: `tasks/coding_longhorizon/prompt.md`, `config/tasks/coding_longhorizon.yaml`,
  seed `tasks/coding_longhorizon/workspace_seed/{check_all.sh, reference_1..4.py}`.
- Four Triton kernels of increasing difficulty (fused elementwise → row LayerNorm
  → tiled GEMM → fused GEMM+bias+relu). Agent writes `solution_1..4.py`.
- Self-test: `bash check_all.sh` → per-kernel `compiled/correctness/decoy/speedup`
  + `GEOMEAN=<x> ALL_PASS=<bool>`.
- Completion: all 4 compiled & correct & `decoy=False`, geomean speedup ≥ **2.0×**.
- Long-horizon because: 4 kernels × profile→test→tune rounds; autotuning encouraged
  (the old bounded task forbade it). Context cycle from accumulated KernelGYM
  verdicts, profiling output, 4 reference reads, large tracebacks (expect ≥1 compaction).

## Task 2 — research: LLM inference-serving systems deep-dive
- Files: `tasks/research_longhorizon/prompt.md`, `config/tasks/research_longhorizon.yaml`.
- Comparative survey of 8 systems (vLLM, TensorRT-LLM, SGLang, TGI, LMDeploy,
  DeepSpeed-MII, llama.cpp, MLC-LLM) on scheduling/batching, KV-cache mgmt,
  quantization, parallelism/disaggregation, perf claims; plus a Comparison Matrix
  and a Tradeoffs & Recommendations section.
- Completion: 10 `##` sections; each system names KV-cache + batching + ≥1 quant
  format; ≥ **30** distinct http(s) URLs; **3000–4500** words; matrix covers all 8.
- Long-horizon because: real multi-source research per system (reverses the old
  "cite from memory" guard). Context cycle from many large, uncached `web_fetch`
  pages (≈5–15k tokens each) — expect 2–4 compactions; strongest demonstrator.

## Condition → command wiring (confirmed)
- `goal` condition → `harness/conditions/goal.sh` invokes **`/goal`** (wraps the
  task prompt with a goal/completion-criteria framing; a separate faster model
  verifies the completion condition each turn).
- `ralph_loop` condition → `harness/conditions/ralph_loop.sh` invokes
  **`/ralph-loop:ralph-loop`** (plugin:skill form of the ralph-loop plugin) with
  `--max-iterations` and `--completion-promise RALPH_DONE`.
- Both launchers are task-agnostic: each long-horizon task above runs under both.

## Remaining harness wiring (TODO before running)
1. **Coding post-hoc scoring**: `harness/runner.py::score_run` (and
   `harness/score/score_coding.py`) are hardcoded to score a single `solution.py`
   vs `tasks/coding/reference_code.py`. They need a multi-kernel branch (read
   `solution_1..4.py` + `reference_1..4.py`, compute geomean) for the gauntlet.
   The in-run self-test (`check_all.sh`) already works regardless.
2. **Research rubric thresholds**: `analysis/research_rubric.py` URL/word-count
   bands were tuned for the old short report; revisit for ≥30 URLs / 3000–4500
   words so scoring is fair (the prompt's self-check already enforces the real
   completion condition).
3. **Point the re-run at the new task names** `coding_longhorizon` /
   `research_longhorizon` (experiment config `tasks:` list or `runner --task`).
4. **Live-test `check_all.sh`** against a running KernelGYM (references are plain
   PyTorch `Model`s in kernelbench format; untested against a live gym yet).

## Open knobs (defaults chosen, tunable)
- geomean speedup target 2.0×; research ≥30 URLs / 3000–4500 words.
- compaction target: sizing aims for ≥1 (coding) / 2–4 (research) compactions.
