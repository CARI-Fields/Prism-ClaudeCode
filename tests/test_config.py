from pathlib import Path
from harness.config import load_experiment, load_task, load_condition

def test_load_experiment():
    exp = load_experiment(Path("config/experiment.yaml"))
    assert exp.model == "claude-sonnet-4-6"
    assert exp.reps == 3
    assert exp.conditions == [
        "single_agent", "subagents", "ralph_loop", "dynamic_workflow", "loop_dynamic"
    ]
    assert exp.tasks == ["coding", "research"]
    assert exp.proxy_port == 8080

def test_load_task_with_and_without_workspace():
    coding = load_task(Path("config/tasks/coding.yaml"))
    assert coding.name == "coding"
    assert coding.workspace == Path("tasks/coding/workspace")
    research = load_task(Path("config/tasks/research.yaml"))
    assert research.workspace is None

def test_load_condition():
    c = load_condition(Path("config/conditions/subagents.yaml"))
    assert c.name == "subagents"
    assert c.launcher == Path("harness/conditions/subagents.sh")
