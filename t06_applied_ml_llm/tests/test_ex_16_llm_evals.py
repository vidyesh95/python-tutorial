import numpy as np
import pytest

from _loader import load

ex = load("t06_applied_ml_llm", "ex_16_llm_evals")


@pytest.mark.parametrize(
    ("pred", "gold", "expected"),
    [
        ("  Paris.  ", "paris", True),
        ("PARIS!", "Paris", True),
        ("New   York", "new york", True),
        ("Paris, France", "Paris", False),
        ("Lyon", "Paris", False),
        ("42", "42?", True),
    ],
)
def test_exact_match(pred, gold, expected):
    assert ex.exact_match(pred, gold) is expected


def test_regex_match():
    assert ex.regex_match("  ORD-1234 ", r"^ORD-\d{4}$")
    assert ex.regex_match("my order is ord-9", r"ord-\d")
    assert not ex.regex_match("ORD-77", r"^ORD-\d{4}$")


@pytest.mark.parametrize("p", [0, 25, 50, 90, 95, 100])
def test_percentile_matches_numpy(p):
    values = [0.5, 3.0, 1.2, 9.9, 4.4, 2.2, 7.1]
    assert ex.percentile(values, p) == pytest.approx(float(np.percentile(values, p)))


def test_percentile_single_and_empty():
    assert ex.percentile([5.0], 95) == 5.0
    with pytest.raises(ValueError):
        ex.percentile([], 50)


def test_diff_runs():
    old = {"a": True, "b": True, "c": False, "d": False}
    new = {"a": True, "b": False, "c": True, "d": False, "e": True, "f": False}
    assert ex.diff_runs(old, new) == {"regressions": ["b"], "fixes": ["c", "e"]}


def test_diff_runs_ignores_missing_and_is_sorted():
    old = {"z": True, "y": True, "gone": True}
    new = {"z": False, "y": False}
    assert ex.diff_runs(old, new) == {"regressions": ["y", "z"], "fixes": []}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"score": 4, "reason": "good"}', 4),
        ('Sure! Here you go: {"score": "5", "reason": "x"} hope it helps', 5),
        ('{"score": 9}', 5),
        ('{"score": 0}', 1),
        ("Score: 3/5 because it is partially right", 3),
        ("score 2", 2),
        ("I cannot decide", None),
        ('{"verdict": "good"}', None),
        ('{"score": "high"}', None),
    ],
)
def test_parse_judge_score(raw, expected):
    assert ex.parse_judge_score(raw) == expected
