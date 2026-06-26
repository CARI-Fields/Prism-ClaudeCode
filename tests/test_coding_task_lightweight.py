from pathlib import Path


def test_coding_reference_is_lightweight_elementwise_task():
    text = Path("experiment/tasks/coding/reference_code.py").read_text()

    assert "nn.Linear" not in text
    assert "matmul" not in text.lower()
    assert "8192" not in text
    assert "torch.relu(x * self.scale + self.bias)" in text
    assert "feature_size = 4096" in text
    assert "batch_size = 1024" in text


def test_coding_prompt_is_bounded_and_discourages_search():
    text = Path("experiment/tasks/coding/prompt.md").read_text()

    assert "bounded experiment task" in text
    assert "Do not do broad benchmark sweeps or autotuning" in text
    assert "Use a flat one-dimensional elementwise grid over `x.numel()`" in text
    assert "`decoy=False` is required" in text
    assert "make at most one targeted fix" in text
    assert "8192" not in text
    assert "complete freedom" not in text
    assert "Let's think step by step" not in text
