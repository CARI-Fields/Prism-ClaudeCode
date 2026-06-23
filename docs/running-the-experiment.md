# Running the experiment

How to run cells (individually or a subset — not all 30 at once) and how `make analyze`
turns whatever you've captured into figures + a report.

A **cell** = one `(task, condition, rep)`:
- `task` ∈ `coding | research`
- `condition` ∈ `single_agent | goal | subagents | ralph_loop | dynamic_workflow | loop_dynamic`
- `rep` = integer (use `1`–`3` for the full design → 5×2×3 = 30 cells)

All commands run from the repo root. The harness uses the project venv (`.venv/bin/python`);
the `Makefile` already points `PY` at it.

---

## 1. Prerequisites (once per session)

Every cell routes the model's API traffic through the TTFT proxy. **Coding** cells also
need the KernelGYM (to score the kernel); **research** cells do not.

```bash
make setup            # first time only: pip install -e ".[dev]" into .venv
make ttft-up          # start the TTFT proxy on :8770  (needed for ALL cells)
```

### KernelGYM (only for `coding` cells)
The gym scores kernels via `/evaluate`. Bring-up gotchas on this box:
- Host redis `:6379` is broken/shared with a live `:10907` setup — use a **clean redis on
  `:6380`** instead.
- The gym start script hardcodes `REDIS_PORT=6379`, so start the modules directly, and
  **the worker MUST get `API_PORT=10908`** (else it registers on the default `:10907` and
  never processes evals → kernel scores time out).
- `docker stop qwen` first (frees ~95 GB of unified memory, else OOM).

```bash
DRENV=/home/yubaifeng/e84381970/envs/drkernel310
GYM=/home/yubaifeng/e84381970/drkernel-lab/sandbox/gpu-kernelgym
sg docker -c "docker stop qwen" || true
"$DRENV/bin/redis-server" --port 6380 --daemonize yes
cd "$GYM"
env CUDA_VISIBLE_DEVICES=0 PYTHONPATH="$GYM" API_HOST=127.0.0.1 API_PORT=10908 \
    REDIS_HOST=localhost REDIS_PORT=6380 REDIS_DB=0 REDIS_PASSWORD= \
    REDIS_KEY_PREFIX=kernelgym_newstd REDIS_KEY_PREFIX_LEGACY=kernelgym_newstd \
    DEFAULT_TOOLKIT=kernelbench DEFAULT_BACKEND_ADAPTER=kernelbench DEFAULT_BACKEND=triton \
    nohup "$DRENV/bin/python3.10" -m kernelgym.server.api.server >/tmp/gym_api.log 2>&1 &
env CUDA_VISIBLE_DEVICES=0 PYTHONPATH="$GYM" API_HOST=127.0.0.1 API_PORT=10908 \
    REDIS_HOST=localhost REDIS_PORT=6380 REDIS_KEY_PREFIX=kernelgym_newstd \
    DEFAULT_BACKEND=triton \
    nohup "$DRENV/bin/python3.10" -m kernelgym.worker.single_worker \
      --worker-id worker_gpu_newstd_0 --device cuda:0 --persistent >/tmp/gym_worker.log 2>&1 &
# wait ~30-60s, then:
curl -s http://127.0.0.1:10908/health        # expect {"status":"healthy",...}
```

The runner auto-runs `docker stop qwen` + a gym health check before each cell, and
**health-gates coding cells**: if the gym is down it records `status:"skipped"` and moves on
(no wasted model call).

---

## 2. Run cells with control

### One cell
```bash
make run TASK=coding   CONDITION=single_agent REP=1
make run TASK=research CONDITION=subagents    REP=1
```
Equivalent direct form: `.venv/bin/python -m harness.runner --task coding --condition single_agent --rep 1`.

### Preview a cell without calling the model
```bash
.venv/bin/python -m harness.runner --task coding --condition single_agent --rep 1 --dry-run
```

### A chosen subset
Loop over only the tuples you want. **Keep it sequential** — the TTFT log is shared and
windowed by time, so never run two cells at once:
```bash
for c in single_agent subagents; do
  make run TASK=research CONDITION=$c REP=1
done
```

Each cell lands in `data/raw/<task>__<condition>__<rep>__<UTC-ts>/` with
`tap/ transcripts/ ttft/ workspace/ run_meta.json`.

---

## 3. Cost / scope controls

- **Cheapest first:** run `research` conditions — no gym, no kernel eval.
- **Shorten loops:** `ralph_loop`/`loop_dynamic` default to 5 iterations. Reduce them:
  ```bash
  RALPH_ITERS=2 make run TASK=coding CONDITION=ralph_loop REP=1
  LOOP_ITERS=2  make run TASK=coding CONDITION=loop_dynamic REP=1
  ```
- **Fewer cells:** just run the conditions/reps you care about (section 2).
- **Sequential only:** never run cells concurrently (shared TTFT log).

### Full sweep (all 30, when ready)
```bash
make dry-all     # preview: prints 30 "=== <run_id> ===" blocks, no API calls
make run-all     # runs all 30 sequentially; failures are isolated (status:"failed", continues)
```

---

## 4. `make analyze` — figures + report

`make analyze` is **idempotent and cumulative**: it rescans *everything currently in*
`data/raw/` and rebuilds from scratch (it does not append).

```bash
make analyze
```

What it does:
1. **Builds tidy tables** → `data/processed/{turns,components,runs}.parquet`. It includes
   every `data/raw/<run_id>/` that has a `run_meta.json` (partial/aborted cells without one
   are skipped; per-run errors are caught and skipped with a printed note).
2. **Renders 4 figures** → `figures/`:
   - `cache_accumulation.png` — **headline**: cumulative `cache_read` (prefix-cache hits) per
     condition over requests
   - `context_growth.png` — per-request context size by component (system / tools / messages)
   - `latency.png` — TTFT vs total latency by condition
   - `success_speedup.png` — success rate + mean kernel speedup by condition
3. **Writes** `reports/report.md` — a runs-summary table (one row per run: `run_id, task,
   condition, success, speedup, num_requests, total_cache_read, cache_hit_ratio,
   completion_time_s`) with the four figures embedded.

If `data/raw/` is empty it writes a "No runs found" stub instead of crashing.

`data/processed/` is regenerated each time (gitignored); `figures/` + `reports/report.md`
are the committed deliverables.

---

## 5. The loop you'll actually use

```bash
make ttft-up                                   # (+ gym bring-up for coding cells)
make run TASK=coding CONDITION=single_agent REP=1
make run TASK=coding CONDITION=subagents    REP=1
make analyze                                   # regenerate figures + report over ALL cells so far
# ...run more cells, re-run `make analyze` anytime to refresh the whole report
```

You control which cells exist by running them individually; `make analyze` always reflects
exactly what's in `data/raw/`.
