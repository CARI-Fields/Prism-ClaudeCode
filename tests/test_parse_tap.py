import json
from pathlib import Path
from analysis.parse.parse_tap import parse_iso, tap_turns, tap_components, tap_component_texts

FIX = Path("tests/fixtures/real_cell/tap.json")


def test_parse_iso_to_epoch():
    assert abs(parse_iso("2026-06-19T21:02:44.554578+00:00") - 1781902964.554578) < 1e-3


def test_tap_turns_shape_and_start_time():
    tap = json.loads(FIX.read_text())
    rows = tap_turns(tap)
    assert len(rows) == len(tap)
    r0 = rows[0]
    for k in ("request_index", "ts_start_epoch", "input_tokens", "output_tokens",
              "cache_read", "cache_creation_5m", "cache_creation_1h",
              "duration_ms", "model", "request_type"):
        assert k in r0
    assert r0["request_index"] == 0
    assert r0["request_type"] == "main-agent"
    # start = completion timestamp - duration
    assert r0["ts_start_epoch"] == parse_iso(tap[0]["timestamp"]) - tap[0]["duration_ms"] / 1000


def test_tap_marks_request_type_subclasses_without_filtering():
    tap = [
        {
            "timestamp": "2026-06-19T21:02:44.554578+00:00",
            "duration_ms": 1000,
            "model": "claude-sonnet-4-6",
            "system": [{"type": "text", "text": "You are a Claude agent."}],
            "tools": [{"name": "Read", "description": "Read files"}],
            "messages": [{"role": "user", "content": "Do the coding task."}],
            "response": {"usage": {
                "input_tokens": 10,
                "cache_read_input_tokens": 20,
                "cache_creation_input_tokens": 30,
                "output_tokens": 5,
            }},
        },
        {
            "timestamp": "2026-06-19T21:02:45.554578+00:00",
            "duration_ms": 500,
            "model": "claude-sonnet-4-6",
            "system": [{
                "type": "text",
                "text": "You are a security monitor for autonomous AI coding agents.",
            }],
            "messages": [{"role": "user", "content": "<transcript> Bash check_kernel.sh"}],
            "response": {
                "content": [{"type": "text", "text": "<block>no</block>"}],
                "usage": {
                    "input_tokens": 7,
                    "cache_read_input_tokens": 11,
                    "cache_creation_input_tokens": 13,
                    "output_tokens": 2,
                },
            },
        },
        {
            "timestamp": "2026-06-19T21:02:46.554578+00:00",
            "duration_ms": 500,
            "model": "claude-sonnet-4-6",
            "system": [
                {"type": "text", "text": "cc_is_subagent=true;"},
                {"type": "text", "text": "You are a subagent spawned by a workflow orchestration script."},
            ],
            "tools": [{"name": "Read", "description": "Read files"}],
            "messages": [{"role": "user", "content": "Return a compact sketch."}],
            "response": {"usage": {
                "input_tokens": 1,
                "cache_read_input_tokens": 2,
                "cache_creation_input_tokens": 3,
                "output_tokens": 4,
            }},
        },
        {
            "timestamp": "2026-06-19T21:02:47.554578+00:00",
            "duration_ms": 500,
            "model": "claude-sonnet-4-6",
            "system": [
                {"type": "text", "text": "cc_is_subagent=true;"},
                {"type": "text", "text": "You are an agent for Claude Code, Anthropic's official CLI for Claude."},
            ],
            "tools": [{"name": "Agent", "description": "Launch subagent"}],
            "messages": [{"role": "user", "content": "Investigate briefly."}],
            "response": {"usage": {
                "input_tokens": 2,
                "cache_read_input_tokens": 3,
                "cache_creation_input_tokens": 4,
                "output_tokens": 5,
            }},
        },
        {
            "timestamp": "2026-06-19T21:02:48.554578+00:00",
            "duration_ms": 500,
            "model": "claude-sonnet-4-6",
            "system": [
                {"type": "text", "text": "cc_is_subagent=true;"},
                {"type": "text", "text": "You are an assistant for performing a web search tool use"},
            ],
            "tools": [{"name": "web_search", "description": "Search web"}],
            "messages": [{"role": "user", "content": "Search recent sources."}],
            "response": {"usage": {
                "input_tokens": 3,
                "cache_read_input_tokens": 4,
                "cache_creation_input_tokens": 5,
                "output_tokens": 6,
            }},
        },
        {
            "timestamp": "2026-06-19T21:02:49.554578+00:00",
            "duration_ms": 500,
            "model": "claude-sonnet-4-6",
            "system": [{"type": "text", "text": "cc_is_subagent=true;"}],
            "messages": [{"role": "user", "content": "Web page content:\n---\nPaper text"}],
            "response": {"usage": {
                "input_tokens": 4,
                "cache_read_input_tokens": 5,
                "cache_creation_input_tokens": 6,
                "output_tokens": 7,
            }},
        },
    ]

    turns = tap_turns(tap)
    assert [row["request_type"] for row in turns] == [
        "main-agent",
        "security-monitor",
        "workflow-subagent",
        "task-subagent",
        "web-search-subagent",
        "web-fetch-subagent",
    ]
    assert [row["request_index"] for row in turns] == [0, 1, 2, 3, 4, 5]

    components = tap_components(tap)
    monitor_components = [row for row in components if row["request_index"] == 1]
    assert monitor_components
    assert {row["request_type"] for row in monitor_components} == {"security-monitor"}
    assert sum(row["est_tokens"] for row in monitor_components) == 31


def test_tap_components_anchored_to_prompt_tokens():
    tap = json.loads(FIX.read_text())
    comps = tap_components(tap)
    c0 = [c for c in comps if c["request_index"] == 0]
    assert {"base system prompt", "builtin tool definitions", "invoked skill bodies"} <= {
        c["component"] for c in c0
    }
    assert next(c for c in c0 if c["component"] == "base system prompt")["est_tokens"] > 1000
    # est_tokens for a request sum to its prompt tokens (input+cache_read+cache_creation)
    u = tap[0]["response"]["usage"]
    prompt = u["input_tokens"] + u["cache_read_input_tokens"] + u["cache_creation_input_tokens"]
    assert sum(c["est_tokens"] for c in c0) == prompt


def test_system_prompt_memory_instructions_do_not_reclassify_whole_prompt_as_auto_memory():
    tap = [{
        "timestamp": "2026-06-19T21:02:44.554578+00:00",
        "duration_ms": 1000,
        "model": "claude-sonnet-4-6",
        "system": [{
            "type": "text",
            "text": (
                "You are an interactive agent.\n"
                "The memory system lets you load project context when relevant."
            ),
        }],
        "tools": [],
        "messages": [{"role": "user", "content": "Do the task."}],
        "response": {"usage": {
            "input_tokens": 100,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": 5,
        }},
    }]

    components = tap_components(tap)
    by_component = {row["component"]: row["est_tokens"] for row in components}

    assert by_component["base system prompt"] > by_component["user input"]
    assert "auto memory" not in by_component


def test_tap_components_classify_context_sources():
    tap = [{
        "timestamp": "2026-06-19T21:02:44.554578+00:00",
        "duration_ms": 1000,
        "model": "claude-sonnet-4-6",
        "system": [
            {"type": "text", "text": "You are a Claude agent."},
            {"type": "text", "text": "# auto memory\nPersistent memory instructions."},
        ],
        "tools": [
            {"name": "Read", "description": "Read files"},
            {"name": "mcp__docs__search", "description": "Search docs"},
        ],
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "<system-reminder>SessionStart hook additional context</system-reminder>"},
                {"type": "text", "text": "Project instructions loaded from CLAUDE.md\nAlways run tests."},
                {"type": "text", "text": "- superpowers:test-driven-development: Use when implementing"},
                {"type": "text", "text": "**Below is the full content of your 'superpowers:test-driven-development' skill**\n# TDD"},
                {"type": "text", "text": "User task: build the report"},
            ],
        }, {
            "role": "assistant",
            "content": [{"type": "text", "text": "I will inspect files."}],
        }, {
            "role": "user",
            "content": [{"type": "tool_result", "content": "file contents from Read"}],
        }],
        "response": {"usage": {
            "input_tokens": 100,
            "cache_read_input_tokens": 20,
            "cache_creation_input_tokens": 30,
            "output_tokens": 5,
            "cache_creation": {"ephemeral_5m_input_tokens": 30, "ephemeral_1h_input_tokens": 0},
        }},
    }]

    c0 = tap_components(tap)
    components = {c["component"] for c in c0}

    assert {
        "base system prompt",
        "auto memory",
        "builtin tool definitions",
        "MCP / extension tool definitions",
        "hooks / system reminders",
        "CLAUDE.md / project instructions",
        "skills listing",
        "invoked skill bodies",
        "user input",
        "assistant / conversation history",
        "tool results / file reads",
    } <= components
    assert sum(c["est_tokens"] for c in c0) == 150


def test_tap_component_texts_full_is_untruncated():
    long = "x" * 1000
    tap = [{
        "timestamp": "2026-06-19T21:02:44.554578+00:00",
        "duration_ms": 1000,
        "model": "claude-sonnet-4-6",
        "system": [{"type": "text", "text": "You are a Claude agent."}],
        "messages": [{"role": "user", "content": [{"type": "text", "text": long}]}],
        "response": {"usage": {
            "input_tokens": 10, "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0, "output_tokens": 5,
        }},
    }]
    preview = {r["component"]: r for r in tap_component_texts(tap)}
    full = {r["component"]: r for r in tap_component_texts(tap, max_chars=None)}
    assert preview["user input"]["text"] == long[:800]
    assert preview["user input"]["truncated"] is True
    assert full["user input"]["text"] == long
    assert full["user input"]["truncated"] is False
