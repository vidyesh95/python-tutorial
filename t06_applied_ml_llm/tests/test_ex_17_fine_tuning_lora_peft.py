import numpy as np
import pytest

from _loader import load

ex = load("t06_applied_ml_llm", "ex_17_fine_tuning_lora_peft")


def test_lora_param_count():
    assert ex.lora_param_count(4096, 4096, 16) == 131072
    assert ex.lora_param_count(100, 50, 4) == 600  # rectangular: r * (d_in + d_out)


def test_trainable_fraction():
    assert ex.trainable_fraction([(4096, 4096)], 16) == pytest.approx(131072 / 4096**2)
    shapes = [(100, 50), (64, 64)]
    expected = (4 * 150 + 4 * 128) / (5000 + 4096)
    assert ex.trainable_fraction(shapes, 4) == pytest.approx(expected)


def test_trainable_fraction_grows_with_rank():
    shapes = [(512, 512)] * 3
    assert ex.trainable_fraction(shapes, 8) == pytest.approx(2 * ex.trainable_fraction(shapes, 4))


def test_lora_merge_matches_two_path_forward():
    rng = np.random.default_rng(0)
    w = rng.normal(size=(6, 5))
    a = rng.normal(size=(2, 5))
    b = rng.normal(size=(6, 2))
    x = rng.normal(size=(3, 5))
    alpha = 8.0
    merged = ex.lora_merge(w, a, b, alpha)
    two_path = x @ w.T + (alpha / 2) * (x @ a.T) @ b.T
    assert np.allclose(x @ merged.T, two_path)


def test_lora_merge_zero_b_is_identity_and_does_not_mutate():
    w = np.arange(12.0).reshape(3, 4)
    original = w.copy()
    out = ex.lora_merge(w, np.ones((2, 4)), np.zeros((3, 2)), alpha=16)
    assert np.array_equal(out, original)
    ex.lora_merge(w, np.ones((2, 4)), np.ones((3, 2)), alpha=16)
    assert np.array_equal(w, original)


GOOD = {
    "messages": [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
}


def test_validate_chat_example_ok():
    assert ex.validate_chat_example(GOOD) == []


@pytest.mark.parametrize("example", [{}, {"messages": []}, {"messages": "hi"}, {"messages": None}])
def test_validate_chat_example_missing_messages(example):
    assert ex.validate_chat_example(example) == ["missing non-empty 'messages' list"]


def test_validate_chat_example_reports_each_problem():
    example = {
        "messages": [
            {"role": "robot", "content": "x"},
            {"role": "user", "content": "   "},
        ]
    }
    errors = ex.validate_chat_example(example)
    assert "message 0: bad role 'robot'" in errors
    assert "message 1: empty content" in errors
    assert "last message must be from the assistant" in errors
    assert len(errors) == 3


def test_qlora_memory_gb():
    assert ex.qlora_memory_gb(7, 0) == pytest.approx(3.5)
    assert ex.qlora_memory_gb(7, 16.8) == pytest.approx(3.5 + 16.8e6 * 12 / 1024**3)
    assert ex.qlora_memory_gb(8, 0, base_bits=16) == pytest.approx(16.0)
