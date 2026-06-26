from pathlib import Path
from experiment.harness.config import load_experiment, load_task, load_condition

def test_load_experiment():
    exp = load_experiment(Path("experiment/config/experiment.yaml"))
    assert exp.model == "claude-sonnet-4-6"
    assert exp.reps == 3
    assert exp.conditions == [
        "single_agent", "goal", "subagents", "ralph_loop",
        "dynamic_workflow", "loop_dynamic"
    ]
    assert exp.tasks == ["coding", "research"]
    assert exp.proxy_port == 8080

def test_load_task_with_and_without_workspace():
    coding = load_task(Path("experiment/config/tasks/coding.yaml"))
    assert coding.name == "coding"
    assert coding.workspace == Path("experiment/tasks/coding/workspace")
    research = load_task(Path("experiment/config/tasks/research.yaml"))
    assert research.workspace is None

def test_load_condition():
    c = load_condition(Path("experiment/config/conditions/subagents.yaml"))
    assert c.name == "subagents"
    assert c.launcher == Path("experiment/harness/conditions/subagents.sh")


def test_load_goal_condition():
    c = load_condition(Path("experiment/config/conditions/goal.yaml"))
    assert c.name == "goal"
    assert c.launcher == Path("experiment/harness/conditions/goal.sh")
