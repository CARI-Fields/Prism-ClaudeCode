from harness.score.extract import extract_last_code_block


def test_extracts_last_python_block():
    text = "intro\n```python\nold = 1\n```\nmiddle\n```python\nimport triton\nx = 2\n```\nend"
    assert extract_last_code_block(text) == "import triton\nx = 2"


def test_returns_none_when_no_block():
    assert extract_last_code_block("no code here") is None
