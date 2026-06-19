# Plan A2 — Instrumentation & Real Workloads — Design

**Date:** 2026-06-19
**Status:** Draft for review
**Builds on:** Plan A (merged capture harness) — adds the metrics + workloads needed to *fully demonstrate Claude Code's capability* and to capture user-experience + load metrics the user requires.

## 1. Goal

Extend the merged harness so each run captures, in addition to context-window & prefix-cache data:
- **用户体验 / UX:** task-level **success rate**, **TTFT** (true time-to-first-token), prefill/decode latency split, total latency, completion time.
- **负载 / load:** already captured (request count, per-request seq length, PD ratio, cache-hit pattern) — unchanged.
- **Performance** (coding task only): kernel **speedup**.

…using two substantial, decomposable workloads (GPU-kernel coding + deep research) so the 5 orchestration conditions produce meaningfully different behavior.

## 2. What's new vs Plan A

| # | Component | Why |
|---|---|---|
| A | **Streaming TTFT proxy** | claude-tap only records total `duration_ms`; no first-token timing (verified). |
| B | **Kernel coding workload** + self-test tool + eval-feedback loops + external scorer | Real, hard, two-dimensional success (correctness + speedup); exercises all conditions. |
| C | **Deep-research workload** + scorer | Decomposable 6-section survey; checkable success. |
| D | **Per-run scorer + artifact capture** | Writes success/perf into `run_meta` for Plan B. |
| E | **Isolated per-run workspaces + service orchestration** | Clean isolation; manage drkernel310 env, Redis, KernelGYM, qwen. |

## 3. Component A — Streaming TTFT capture

A thin async pass-through proxy `harness/capture/ttft_proxy.py` that **claude-tap forwards through** via its `--tap-target` flag, so claude-tap's verified body/usage capture is unchanged:

```
claude  →  claude-tap (bodies+usage, :auto)  →  ttft_proxy (:TTFT_PORT)  →  https://api.anthropic.com
```

Per request it timestamps the SSE stream and emits one JSONL row:
- `request_id` (from response `request-id` header — joins to claude-tap records)
- `t_send` (request received) → `t_message_start` (first `message_start` event ≈ **prefill done**) → `t_first_text` (first `content_block_delta` ≈ **TTFT**) → `t_done` (stream end ≈ **total**)

Derived in Plan B: `prefill_latency = t_message_start − t_send`, `TTFT = t_first_text − t_send`, `decode_time = t_done − t_first_text`, `decode_rate = output_tokens / decode_time`.

Rows collected into `data/raw/<run_id>/ttft/` (time-window or per-run file). **Hard requirement:** byte-transparent streaming (no buffering, headers preserved) so caching/timing are not perturbed — re-validate fidelity (usage tokens still match claude-tap + JSONL) as in the Plan A pilot.

## 4. Component B — GPU-kernel coding workload

**Source:** drkernel-lab KernelBench L2 problems (`distill/problems/problems_sample.jsonl`). **Chosen problem:** `76_Gemm_Add_ReLU` (GEMM+bias+ReLU @1024×8192; Triton's strong suit, clean speedup signal). The problem's self-contained `prompt_text` becomes `tasks/coding/prompt.md`; `reference_code` is stored for scoring.

**Self-test tool (agent-facing):** each run's isolated scratch dir contains `check_kernel.sh` and the problem files. The prompt instructs the agent to write its kernel to `solution.py` and run `bash check_kernel.sh solution.py` to compile/test it. `check_kernel.sh` uses the **drkernel310** python to POST `solution.py` + `reference_code` to KernelGYM `:10908/evaluate` and prints `compiled / correctness / decoy / speedup`. This lets `single_agent`/`subagents`/`workflow` iterate within a session.

**Eval-feedback loops (ralph/loop):** between iterations the launcher scores the current `solution.py` and injects the result (errors, correctness, speedup, best-so-far) into the next prompt — `ralph_loop` via the fresh prompt + a `PROGRESS.md`, `loop_dynamic` via the `--continue` prompt.

**Authoritative external scoring (final):** after the whole run, the harness scores the final `solution.py` with one POST to `/evaluate` and records the official result. **Success = `correctness == true AND decoy_kernel == false`; performance = `speedup = reference_runtime / kernel_runtime`** (mean of 100 CUDA-event trials, clipped at 3.0). These are independent of the agent's self-reported results.

## 5. Component C — Deep-research workload

`tasks/research/prompt.md` = the approved survey: write `report.md` covering 6 sections (FlashAttention family; quantized GEMM kernels; KV-cache/paged-attention kernels; Triton vs CUDA vs CUTLASS tradeoffs; hardware features incl. Blackwell FP4/FP8; autotuning & compilers), each with citations + a comparison table. Runs in an isolated scratch dir.

**Scorer** `harness/score/score_research.py`: `report.md` exists, all 6 section headings present, ≥12 distinct cited URLs, optional LLM-judge (a `claude -p` rubric → 0–5). Records `sections_present`, `citation_count`, `judge_score`, `success` (all sections + ≥12 citations).

## 6. Component D — Per-run scorer + artifact capture

After the launcher finishes, `runner.execute` additionally:
1. Snapshots the agent's scratch workspace into `data/raw/<run_id>/artifacts/`.
2. Runs the task's scorer (`harness/score/score_coding.py` or `score_research.py`).
3. Collects TTFT rows into `ttft/`.
4. Adds to `run_meta.json`:
   - common: `success` (bool), `completion_time_s` (= ended−started).
   - coding: `compiled`, `correctness`, `decoy_kernel`, `speedup`, `reference_runtime_ms`, `kernel_runtime_ms`, `iterations`.
   - research: `sections_present`, `citation_count`, `judge_score`.

## 7. Component E — Isolated workspaces & service orchestration

- Each run executes in a fresh scratch cwd (`data/raw/<run_id>/workspace/`, gitignored), seeded per task. The agent never touches the experiment repo.
- `harness/services.py` ensures prerequisites before a sweep and health-checks them:
  - `docker stop qwen` (frees ~95 GB unified memory — **else OOM**),
  - Redis `:6379`, KernelGYM GPU server `:10908` (`sandbox/gpu-kernelgym/start_gpu_newstd.sh`),
  - the `ttft_proxy`.
  - Coding runs require the gym; research runs require only the ttft_proxy. All runs use the gym/env only via the scorer + self-test tool, not the agent's model calls.
- New config (in `config/experiment.yaml` / task configs): `drkernel_python` (`/home/yubaifeng/e84381970/envs/drkernel310/bin/python3.10`), `kernelgym_url` (`http://127.0.0.1:10908`), `ttft_port`, `problem_name` (`76_Gemm_Add_ReLU`), iteration counts.

## 8. Metric coverage after Plan A2 (closes both gaps)

| Metric | Source |
|---|---|
| 请求数 / seq length / PD ratio / cache-hit pattern | claude-tap records + usage (Plan A) ✅ |
| 任务完成时间 | run_meta started/ended ✅ |
| total latency | claude-tap `duration_ms` ✅ |
| **TTFT + prefill/decode latency split** | **ttft_proxy (A)** ✅ |
| **success rate (task)** | **scorers (B coding /evaluate, C research) (D)** ✅ |
| **kernel performance (speedup)** | **/evaluate (B)** ✅ |

## 9. Environment facts & risks

- GB10 / Blackwell sm_121: `torch.profiler` per-kernel attribution flaky → KernelGYM uses a `perf_counter` fallback; **CUDA-event speedup is sound**. Harmless "capability 12.0 max" torch warning. `apt` is broken (no installs).
- **qwen container pins ~95 GB** → must `docker stop qwen` before any GPU eval, or OOM.
- TTFT proxy is the highest-risk build: must stream byte-transparently; gate it behind a functional + fidelity test (real `claude -p` through the full chain works; usage matches; TTFT recorded) before use.
- The `drkernel310` env is aarch64-native and already built — do **not** pip-restore cross-arch.

## 10. Open parameters (default = keep, flag for the user)

- **Model:** experiment fixes `claude-sonnet-4-6` (control). Kernel-writing is hard; `opus-4-8` would showcase more but breaks the fixed-model control. **Default: keep sonnet across all conditions**; revisit only if success is uniformly zero.
- **Reasoning effort:** the drkernel server uses `--effort high/xhigh`. Our launchers don't set effort. **Default: leave effort unset (CC default)**; could pin it as another control.
- **Problem count:** one fixed problem (`76_Gemm_Add_ReLU`) keeps the comparison controlled; reps capture variance. A small problem set is a later extension.

## 11. Out of scope (YAGNI)

- Retraining/RL (the drkernel-lab's own purpose) — we only *use* its gym + problems for scoring.
- More than one coding / one research problem.
- Multi-model comparison (model held fixed).

## 12. Implementation phasing (for the plan)

1. TTFT proxy + fidelity/functional test (de-risk first).
2. Service orchestration + isolated workspaces.
3. Kernel workload: prompt extraction, `check_kernel.sh`, `score_coding.py`.
4. Research workload + `score_research.py`.
5. Eval-feedback loop launchers (ralph/loop) + self-test wiring.
6. Wire scorers + TTFT + artifact capture into `runner.execute` + `run_meta`.
7. End-to-end single-cell dry/real validation (one cell), then ready for the (still user-gated) sweep.
