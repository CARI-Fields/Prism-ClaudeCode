# Pilot Spike Notes

Captured: 2026-06-19. All probes used `claude-sonnet-4-6` model context (actual model dispatched by Claude Code default: `claude-opus-4-8`).

---

## Tap version

```
claude-tap 0.1.120
```

Relevant flag help text:

```
proxy options:
  --tap-port PORT       Proxy port (default: auto)

storage and update options:
  --tap-output-dir OUTPUT_DIR
                        Legacy trace directory to import once (default: ./.traces)

viewer options:
  --tap-no-open         Don't auto-open live or generated HTML viewers in a browser
  --tap-live            Use the shared local dashboard while the client runs (default: on)
  --tap-no-live         Disable the shared dashboard (restores pre-v0.1.75 behavior)
  --tap-live-port LIVE_PORT
                        Port for the shared dashboard (default: 19527)
```

**Key finding:** `--tap-output-dir` is labeled "Legacy trace directory to import once". In v0.1.120 the primary store is a SQLite database at `~/.local/share/claude-tap/traces.sqlite3` (tables: `sessions`, `records`, `proxy_logs`, `record_blobs`). The `--tap-output-dir` flag does NOT write JSONL files to disk in this version; it is a legacy import flag. Traces must be queried from the SQLite database.

**Verified working wrapper shape:**
```bash
/path/to/.venv/bin/claude-tap --tap-no-live --tap-no-open -- <claude args>
```
`--tap-output-dir` can be omitted (writes nothing to that dir) or kept for forward compatibility.

---

## Tap output

Trace storage: SQLite at `~/.local/share/claude-tap/traces.sqlite3`

Tables:
- `sessions` — one row per claude-tap invocation: `id, started_at, updated_at, date_key, client, proxy_mode, status, record_count, summary_json`
- `records` — one row per API call: `session_id, record_index, turn, timestamp, payload_json`
- `record_blobs` — deduplicated large blobs (messages arrays, tool outputs): `session_id, hash, kind, payload_json, size_bytes`
- `proxy_logs` — proxy-level log lines

**Session ID** from tap summary (printed to stdout) matches the sqlite `sessions.id`. Example from plain probe: `ed704b68-e21d-498d-9c20-a180db5e1425`.

**Trace filename pattern:** none (SQLite DB, not files). Legacy file export via `claude-tap export <session_id> -o out.json --format json`.

**For one captured request (plain probe, record_index=1):**

Request body keys:
```
model, messages, system, tools, metadata, max_tokens, thinking,
context_management, output_config, stream
```

Note: `messages` and large tool arrays are stored as blob references in `records.payload_json` and resolved via `record_blobs` (keyed by sha256 hash). The actual content is retrievable by joining on `record_blobs.hash`.

**Response `usage` object (redacted excerpt):**
```json
{
  "input_tokens": 5405,
  "cache_creation_input_tokens": 35931,
  "cache_read_input_tokens": 0,
  "cache_creation": {
    "ephemeral_5m_input_tokens": 0,
    "ephemeral_1h_input_tokens": 35931
  },
  "output_tokens": 4,
  "service_tier": "standard",
  "inference_geo": "not_available",
  "output_tokens_details": {
    "thinking_tokens": 0
  },
  "iterations": [
    {
      "input_tokens": 5405,
      "output_tokens": 4,
      "cache_read_input_tokens": 0,
      "cache_creation_input_tokens": 35931,
      "cache_creation": {
        "ephemeral_5m_input_tokens": 0,
        "ephemeral_1h_input_tokens": 35931
      },
      "type": "message"
    }
  ]
}
```

Session summary printed to stdout:
```
API calls: 1
Tokens: 5,405 in / 4 out / 35,931 cache_write
Session: ed704b68-e21d-498d-9c20-a180db5e1425
Database: /home/yubaifeng/.local/share/claude-tap/traces.sqlite3
```

---

## Transcript location

**Encoding rule (confirmed):** Claude Code writes session JSONL to:
```
~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl
```
where `<encoded-cwd>` is the absolute cwd with every `/` replaced by `-`.

Example: cwd `/tmp/cc-pilot/plain` → encoded dir `-tmp-cc-pilot-plain`.

**Confirmed:** only `/` is replaced by `-`. Dots (`.`) and underscores (`_`) are preserved as-is (verified: cwd `/tmp/cc-pilot/plain` → `-tmp-cc-pilot-plain`, no dot-stripping observed).

**Subagent sidechains** are written to:
```
~/.claude/projects/<encoded-cwd>/<session-uuid>/subagents/agent-<id>.jsonl
```
(each sidechain has its own JSONL, separate from the parent session file).

**Workflow subagents** are written to:
```
~/.claude/projects/<encoded-cwd>/<session-uuid>/subagents/workflows/<wf-id>/agent-<id>.jsonl
```
plus a `journal.jsonl` tracking workflow state.

**One assistant message's `message.usage` object** (from plain probe session JSONL):
```json
{
  "input_tokens": 5405,
  "cache_creation_input_tokens": 35931,
  "cache_read_input_tokens": 0,
  "output_tokens": 4,
  "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
  "service_tier": "standard",
  "cache_creation": {
    "ephemeral_1h_input_tokens": 35931,
    "ephemeral_5m_input_tokens": 0
  },
  "inference_geo": "not_available",
  "iterations": [
    {
      "input_tokens": 5405,
      "output_tokens": 4,
      "cache_read_input_tokens": 0,
      "cache_creation_input_tokens": 35931,
      "cache_creation": {
        "ephemeral_5m_input_tokens": 0,
        "ephemeral_1h_input_tokens": 35931
      },
      "type": "message"
    }
  ],
  "speed": "standard"
}
```

---

## Proxy fidelity

Comparing the same plain probe request across both sources:

| Field | Tap trace (SQLite) | Session JSONL |
|-------|--------------------|---------------|
| `input_tokens` | 5405 | 5405 |
| `output_tokens` | 4 | 4 |
| `cache_creation_input_tokens` | 35931 | 35931 |
| `cache_read_input_tokens` | 0 | 0 |
| `cache_creation.ephemeral_1h_input_tokens` | 35931 | 35931 |
| `cache_creation.ephemeral_5m_input_tokens` | 0 | 0 |

**Result: PERFECT MATCH — zero delta.** The proxy does not perturb token counts or cache state. The tap trace is a faithful copy of the real API response, forwarded unchanged to Claude Code.

Additional fields in JSONL but not tap trace: `server_tool_use`, `speed`. These are Claude Code SDK additions, not from the raw API response.

---

## Condition commands

| Condition | Exact invocation | Verification |
|-----------|-----------------|--------------|
| `single_agent` | `claude -p "Reply with only the word READY."` | JSONL has 0 `isSidechain:True` entries; one session file created |
| `subagents` | `claude -p "Use the Task tool to launch two subagents in parallel: the first returns only the word ALPHA, the second returns only the word BETA. Report both results."` | Parent JSONL has 0 sidechain entries; `/subagents/agent-*.jsonl` files contain `isSidechain:True` on every line |
| `ralph_loop` | `for i in 1 2; do claude -p "Reply with only the word TICK$i."; done` | Two separate JSONL files created in the project dir (different session UUIDs each iteration) |
| `loop_dynamic` | Iteration 1: `claude -p "Reply with only the word STEP1."` then iteration 2: `claude --continue -p "Reply with only the word STEP2."` | ONE JSONL file in the project dir; both iterations appended to same session UUID (context retained) |
| `dynamic_workflow` | `claude -p "Use a workflow to count to three and return each number separately as three subagents: one for ONE, one for TWO, one for THREE. Report all results."` | Spawned 3 subagents; stored under `subagents/workflows/wf_*/agent-*.jsonl`; `isSidechain:True` confirmed in workflow agent files |

### Condition details

**`single_agent`:**
Run from a dedicated cwd, e.g. `/tmp/cc-pilot/plain`.
```bash
mkdir -p /tmp/cc-pilot/plain && cd /tmp/cc-pilot/plain
claude -p "Reply with only the word READY."
```
Transcript at: `~/.claude/projects/-tmp-cc-pilot-plain/<session-uuid>.jsonl`
All entries have `isSidechain: False` (or None for non-message types).

**`subagents`:**
Run from a dedicated cwd. The prompt must explicitly request Task-tool delegation. No `--dangerously-skip-permissions` needed for read-only tasks.
```bash
mkdir -p /tmp/cc-pilot/subagents && cd /tmp/cc-pilot/subagents
claude -p "Use the Task tool to launch two subagents in parallel: the first returns only the word ALPHA, the second returns only the word BETA. Report both results."
```
Sidechains at: `~/.claude/projects/-tmp-cc-pilot-subagents/<session-uuid>/subagents/agent-*.jsonl`
Each sidechain file has `isSidechain: True` on every entry.

**`ralph_loop`:**
External shell loop; each iteration starts a fresh `claude` process (new session, no context).
```bash
mkdir -p /tmp/cc-pilot/ralph-loop && cd /tmp/cc-pilot/ralph-loop
for i in 1 2; do claude -p "Reply with only the word TICK$i."; done
```
Result: 2 separate JSONL files with distinct session UUIDs.

**`loop_dynamic`:**
`/loop` slash command (`claude -p "/loop ..."`) does NOT self-pace headlessly — it runs once and stops. The working mechanism for context-retained multi-turn loop is `claude --continue -p "..."` (short form: `claude -c -p "..."`).
```bash
mkdir -p /tmp/cc-pilot/loop-dynamic && cd /tmp/cc-pilot/loop-dynamic
claude -p "Reply with only the word STEP1."          # starts session
claude --continue -p "Reply with only the word STEP2."  # continues SAME session
```
Result: single JSONL file; both turns appended to same session UUID.
Contrast with ralph_loop: same session UUID across iterations = context retained.

**`dynamic_workflow`:**
Triggered by including "use a workflow" in the prompt. No special flags needed. Claude Code's built-in Workflow tool orchestrates subagents and writes them under a `workflows/` subdir.
```bash
mkdir -p /tmp/cc-pilot/workflow && cd /tmp/cc-pilot/workflow
claude -p "Use a workflow to count to three: three subagents, one returns ONE, one TWO, one THREE."
```
Workflow subagents at: `~/.claude/projects/<cwd-encoded>/<session-uuid>/subagents/workflows/<wf-id>/agent-*.jsonl`
Journal at: `.../workflows/<wf-id>/journal.jsonl`

---

## Decision

| Condition | Go / No-go | Notes |
|-----------|-----------|-------|
| `single_agent` | GO | Plain `claude -p` works; transcript location confirmed |
| `subagents` | GO | Task-tool delegation in prompt reliably spawns sidechains; `isSidechain:True` confirmed in subagent files |
| `ralph_loop` | GO | Shell `for` loop; each iteration = new session UUID = reset context; trivially verifiable |
| `loop_dynamic` | GO (with fallback) | `claude --continue -p "..."` retains session; `/loop` slash command does NOT self-pace headlessly and should not be used |
| `dynamic_workflow` | GO (with caveat) | "use a workflow" in prompt triggers Workflow orchestration; subagents stored under `workflows/` subdir; confirmed with 3-agent run. Note: workflow subagents are stored in a different path than plain Task-tool subagents — parsers must check both `subagents/*.jsonl` and `subagents/workflows/<wf-id>/*.jsonl` |

**Final command table:**

```bash
# single_agent
claude -p "Reply with only the word READY."

# subagents
claude -p "Use the Task tool to launch two subagents in parallel: ..."

# ralph_loop
for i in 1 2; do claude -p "TICK$i."; done

# loop_dynamic (retained context)
claude -p "STEP1."
claude --continue -p "STEP2."

# dynamic_workflow
claude -p "Use a workflow to ... three subagents ..."
```

**Auth header redaction:** claude-tap redacts Authorization headers to `Bearer sk-an...` in the SQLite payload_json. Confirmed: no `sk-ant-...` keys present in fixture files.
