# Plan A2 validation

## TTFT fidelity probe results

Probe run: 2026-06-19, model `claude-sonnet-4-6`, cwd `/tmp/fidchk`.
Chain: `claude` → `claude-tap` (session `c9f17655-49c8-4bc6-b41d-d7ea2786a094`) → `ttft_proxy :8770` → `https://api.anthropic.com`.

### (a) TTFT row recorded — PASS

```json
{"request_id": "req_011CcDECSbD3tGpYes7wkb9z", "t_send_epoch": 1781899932.705159, "prefill_s": 2.9814, "ttft_s": 3.0095, "total_s": 3.1525, "status": 200}
```

`ttft_s` = 3.0095 s, `prefill_s` = 2.9814 s, `total_s` = 3.1525 s. All fields numeric and positive.

### (b) Fidelity preserved (proxy does not perturb usage) — PASS

| Field                        | claude-tap | session JSONL | delta |
|------------------------------|-----------|---------------|-------|
| input_tokens                 | 3         | 3             | 0     |
| output_tokens                | 5         | 5             | 0     |
| cache_read_input_tokens      | 0         | 0             | 0     |
| cache_creation_input_tokens  | 42085     | 42085         | 0     |

All four token fields match exactly. The TTFT proxy is byte-transparent; it does not perturb token or cache usage.
