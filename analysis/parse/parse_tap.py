from __future__ import annotations

import json
from datetime import datetime

from analysis.parse.tokenizer import scale_to_total


BUILTIN_TOOL_NAMES = {
    "Agent", "AskUserQuestion", "Bash", "CronCreate", "CronDelete", "CronList",
    "DesignSync", "Edit", "EnterPlanMode", "EnterWorktree", "ExitPlanMode",
    "ExitWorktree", "Glob", "Grep", "LS", "Monitor", "NotebookEdit",
    "PushNotification", "Read", "RemoteTrigger", "ScheduleWakeup", "Skill",
    "TaskCreate", "TaskGet", "TaskList", "TaskOutput", "TaskStop",
    "TaskUpdate", "TodoRead", "TodoWrite", "WebFetch", "WebSearch",
    "Workflow", "Write",
}


def parse_iso(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def _usage(turn: dict) -> dict:
    return (turn.get("response") or {}).get("usage") or {}


def has_response_usage(turn: dict) -> bool:
    """A real, completed model request reports token usage. Aborted / cancelled /
    empty responses are still captured but come back with an empty usage block
    (``response.usage == {}``, ``content == []``, ``stop_reason == null``) and carry
    no tokens."""
    return bool(_usage(turn))


def drop_empty_turns(tap: list) -> list:
    """Remove captured turns that have no usage — aborted or non-responses. They
    contribute zero tokens of read/write/input and would otherwise inflate request
    counts and pad every per-request curve with leading flat-zero points."""
    return [turn for turn in tap if has_response_usage(turn)]


def _request_type(turn: dict) -> str:
    system_text = "\n".join(_text_from_content(item) for item in turn.get("system") or [])
    system_lower = system_text.lower()
    if "security monitor for autonomous ai coding agents" in system_lower:
        return "security-monitor"
    if "cc_is_subagent=true" not in system_lower:
        return "main-agent"

    tool_names = {
        tool.get("name") for tool in turn.get("tools") or []
        if isinstance(tool, dict) and isinstance(tool.get("name"), str)
    }
    message_text = "\n".join(
        _message_text(message) for message in turn.get("messages") or []
    ).lower()

    if "workflow orchestration script" in system_lower:
        return "workflow-subagent"
    if "assistant for performing a web search tool use" in system_lower or "web_search" in tool_names:
        return "web-search-subagent"
    if "web page content:" in message_text:
        return "web-fetch-subagent"
    if "agent for claude code" in system_lower:
        return "task-subagent"
    return "subagent-internal"


def tap_turns(tap: list) -> list[dict]:
    rows = []
    for i, turn in enumerate(tap):
        u = _usage(turn)
        cc = u.get("cache_creation") or {}
        ts = turn.get("timestamp")
        dur = turn.get("duration_ms") or 0
        start = parse_iso(ts) - dur / 1000 if ts else None
        rows.append({
            "request_index": i,
            "ts_start_epoch": start,
            "input_tokens": u.get("input_tokens", 0),
            "output_tokens": u.get("output_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "cache_creation_5m": cc.get("ephemeral_5m_input_tokens", 0),
            "cache_creation_1h": cc.get("ephemeral_1h_input_tokens", 0),
            "duration_ms": dur,
            "model": turn.get("model"),
            "request_type": _request_type(turn),
        })
    return rows


def _component_bytes(value) -> int:
    """Size of a request component (system/tools/messages). Handles inline content
    and claude-tap blob references (which carry a 'bytes' field)."""
    if value is None:
        return 0
    if isinstance(value, dict) and "__claude_tap_blob_ref__" in value:
        return int(value["__claude_tap_blob_ref__"].get("bytes", 0))
    if isinstance(value, list):
        return sum(_component_bytes(v) for v in value)
    return len(json.dumps(value, ensure_ascii=False))


def _cache_creation_tokens(usage: dict) -> int:
    if "cache_creation_input_tokens" in usage:
        return int(usage.get("cache_creation_input_tokens") or 0)
    cc = usage.get("cache_creation") or {}
    return int(cc.get("ephemeral_5m_input_tokens", 0) or 0) + int(
        cc.get("ephemeral_1h_input_tokens", 0) or 0
    )


def _add_part(parts: dict[str, float], component: str, value) -> None:
    size = float(_component_bytes(value))
    if size <= 0:
        return
    parts[component] = parts.get(component, 0.0) + size


def _text_from_content(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        text = item.get("text")
        if isinstance(text, str):
            return text
        content = item.get("content")
        if isinstance(content, str):
            return content
    return ""


def _message_text(message) -> str:
    content = message.get("content") if isinstance(message, dict) else message
    if isinstance(content, list):
        return "\n".join(_text_from_content(item) for item in content)
    return _text_from_content(content)


def _classify_system_item(item) -> str:
    text = _text_from_content(item)
    lower = text.lower()
    stripped = lower.lstrip()
    if (
        stripped.startswith("# auto memory")
        or stripped.startswith("<auto-memory")
        or "auto memory loaded" in lower
        or "persistent memory loaded" in lower
        or "file-based memory loaded" in lower
    ):
        return "auto memory"
    return "base system prompt"


def _classify_tool(tool) -> str:
    name = tool.get("name") if isinstance(tool, dict) else None
    if isinstance(name, str) and name in BUILTIN_TOOL_NAMES:
        return "builtin tool definitions"
    return "MCP / extension tool definitions"


def _classify_message_text(text: str, role: str | None) -> str:
    lower = text.lower()
    if "full content of your" in lower and "skill" in lower:
        return "invoked skill bodies"
    if "skill_listing" in lower or "available skills" in lower or "- superpowers:" in text:
        return "skills listing"
    if "claude.md" in lower or "project instructions" in lower or "path-scoped rules" in lower:
        return "CLAUDE.md / project instructions"
    if "<system-reminder>" in lower or "system-reminder" in lower or "hook" in lower:
        return "hooks / system reminders"
    if "subagent" in lower and ("summary" in lower or "completed" in lower or "metadata" in lower):
        return "subagent summaries"
    if role == "assistant":
        return "assistant / conversation history"
    if role == "user":
        return "user input"
    return "assistant / conversation history"


def _classify_message_content(item, role: str | None) -> str:
    if isinstance(item, dict) and item.get("type") == "tool_result":
        return "tool results / file reads"
    return _classify_message_text(_text_from_content(item), role)


def _context_source_bytes(turn: dict) -> dict[str, float]:
    parts: dict[str, float] = {}
    for item in turn.get("system") or []:
        _add_part(parts, _classify_system_item(item), item)
    for tool in turn.get("tools") or []:
        _add_part(parts, _classify_tool(tool), tool)
    for message in turn.get("messages") or []:
        role = message.get("role") if isinstance(message, dict) else None
        content = message.get("content") if isinstance(message, dict) else message
        if isinstance(content, list):
            for item in content:
                _add_part(parts, _classify_message_content(item, role), item)
        else:
            _add_part(parts, _classify_message_text(_text_from_content(content), role), content)
    return parts


def tap_components(tap: list) -> list[dict]:
    rows = []
    for i, turn in enumerate(tap):
        u = _usage(turn)
        prompt = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                  + _cache_creation_tokens(u))
        request_type = _request_type(turn)
        sizes = _context_source_bytes(turn)
        est = scale_to_total(sizes, prompt)
        for comp in sizes:
            rows.append({"request_index": i, "component": comp,
                         "bytes": int(sizes[comp]), "est_tokens": est[comp],
                         "request_type": request_type})
    return rows


def _component_text(value) -> str:
    """Best-effort real text for one context chunk. Blob-ref'd content has no inline
    text (only a byte count), so emit a placeholder for it."""
    if value is None:
        return ""
    if isinstance(value, dict) and "__claude_tap_blob_ref__" in value:
        n = int(value["__claude_tap_blob_ref__"].get("bytes", 0))
        return f"(externalized blob, {n} bytes — text not captured)"
    if isinstance(value, list):
        return "\n".join(_component_text(v) for v in value)
    if isinstance(value, dict):
        text = _text_from_content(value)
        if text:
            return text
        return json.dumps(value, ensure_ascii=False)  # e.g. tool definitions
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _context_source_texts(turn: dict) -> dict[str, list[str]]:
    parts: dict[str, list[str]] = {}

    def add(component: str, value) -> None:
        text = _component_text(value)
        if text and text.strip():
            parts.setdefault(component, []).append(text)

    for item in turn.get("system") or []:
        add(_classify_system_item(item), item)
    for tool in turn.get("tools") or []:
        add(_classify_tool(tool), tool)
    for message in turn.get("messages") or []:
        role = message.get("role") if isinstance(message, dict) else None
        content = message.get("content") if isinstance(message, dict) else message
        if isinstance(content, list):
            for item in content:
                add(_classify_message_content(item, role), item)
        else:
            add(_classify_message_text(_text_from_content(content), role), content)
    return parts


def tap_component_texts(tap: list, max_chars: int = 800) -> list[dict]:
    """Per-(request_index, component) real text, truncated to a preview.

    Components whose joined text is identical across every turn (system prompt,
    tool definitions, CLAUDE.md, ...) are emitted ONCE per run with ``stable=True``
    to bound the embedded payload; volatile components (messages, tool results) are
    emitted per request with ``stable=False``."""
    by_comp: dict[str, list[tuple[int, str, str]]] = {}
    for i, turn in enumerate(tap):
        request_type = _request_type(turn)
        for comp, chunks in _context_source_texts(turn).items():
            joined = "\n\n".join(chunks).strip()
            if joined:
                by_comp.setdefault(comp, []).append((i, request_type, joined))

    rows = []
    for comp, entries in by_comp.items():
        stable = len({text for _, _, text in entries}) == 1
        emit = entries[:1] if stable else entries
        for i, request_type, text in emit:
            preview = text[:max_chars]
            rows.append({
                "request_index": i,
                "component": comp,
                "request_type": request_type,
                "text": preview,
                "truncated": len(text) > max_chars,
                "bytes": len(text.encode("utf-8")),
                "stable": stable,
            })
    return rows
