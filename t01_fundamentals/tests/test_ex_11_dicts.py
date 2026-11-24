from _loader import load

ex = load("t01_fundamentals", "ex_11_dicts")


def test_word_count():
    assert ex.word_count("the cat and The hat") == {"the": 2, "cat": 1, "and": 1, "hat": 1}
    assert ex.word_count("") == {}
    assert ex.word_count("a a a") == {"a": 3}


def test_invert_dict():
    assert ex.invert_dict({"a": 1, "b": 2}) == {1: "a", 2: "b"}
    assert ex.invert_dict({}) == {}


def test_merge_with_sum():
    a = {"x": 1, "y": 2}
    b = {"y": 10, "z": 3}
    assert ex.merge_with_sum(a, b) == {"x": 1, "y": 12, "z": 3}
    assert a == {"x": 1, "y": 2}  # inputs untouched
    assert b == {"y": 10, "z": 3}
    assert ex.merge_with_sum({}, {"a": 1}) == {"a": 1}


def test_group_by_length():
    assert ex.group_by_length(["a", "bb", "c", "dd", "eee"]) == {
        1: ["a", "c"],
        2: ["bb", "dd"],
        3: ["eee"],
    }
    assert ex.group_by_length([]) == {}


def test_get_nested():
    assert ex.get_nested({"a": {"b": {"c": 1}}}, ["a", "b", "c"]) == 1
    assert ex.get_nested({"a": {"b": 1}}, ["a", "x"], default=0) == 0
    assert ex.get_nested({"a": 5}, ["a", "b"]) is None
    assert ex.get_nested({"a": 1}, []) == {"a": 1}
