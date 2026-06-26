import pytest
from stack import Stack

def test_push_pop():
    s = Stack()
    s.push(1); s.push(2)
    assert s.pop() == 2
    assert s.pop() == 1

def test_peek_and_is_empty():
    s = Stack()
    assert s.is_empty()
    s.push(42)
    assert not s.is_empty()
    assert s.peek() == 42

def test_pop_empty_raises():
    with pytest.raises(IndexError):
        Stack().pop()
