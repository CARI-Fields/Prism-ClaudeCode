from pathlib import Path


def test_goal_launcher_starts_prompt_with_goal_slash_command():
    path = Path("experiment/harness/conditions/goal.sh")
    text = path.read_text()

    assert path.stat().st_mode & 0o111
    assert 'PROMPT="/goal ' in text
    assert '$(cat "$PROMPT_FILE")$SELFTEST' in text
    assert 'Write your solution to solution.py and run: bash check_kernel.sh solution.py' in text
    assert "TaskCreate" not in text
    assert "TaskUpdate" not in text


def test_subagents_launcher_requires_foreground_delegation():
    text = Path("experiment/harness/conditions/subagents.sh").read_text()

    assert "MUST use the Task tool" in text
    assert "exactly one short foreground subagent task" in text
    assert "wait for that subagent" in text
    assert "Do not launch background research workflows" in text


def test_loop_launchers_default_to_lightweight_iteration_budget():
    ralph = Path("experiment/harness/conditions/ralph_loop.sh").read_text()
    loop_dynamic = Path("experiment/harness/conditions/loop_dynamic.sh").read_text()

    assert 'ITERS="${RALPH_ITERS:-2}"' in ralph
    assert 'RALPH_PLUGIN_DIR="${RALPH_PLUGIN_DIR:-$HOME/.claude/plugins/cache/claude-plugins-official/ralph-loop/1.0.0}"' in ralph
    assert "--plugin-dir" in ralph
    assert "/ralph-loop" in ralph
    assert "--max-iterations" in ralph
    assert "--completion-promise" in ralph
    assert "_feedback.sh" not in ralph
    assert "for i in" not in ralph
    assert 'ITERS="${LOOP_ITERS:-2}"' in loop_dynamic
    assert "final lightweight continuation step" in loop_dynamic
    assert "make at most one small targeted speed tweak" in loop_dynamic
    assert "do not produce a long explanation" in loop_dynamic


def test_dynamic_workflow_launcher_bounds_agent_fanout():
    text = Path("experiment/harness/conditions/dynamic_workflow.sh").read_text()

    assert "MUST use the Workflow tool exactly once" in text
    assert "launch exactly one short agent" in text
    assert "wait for that workflow result" in text
    assert "Do not launch broad background workflows, parallel agent fleets" in text
