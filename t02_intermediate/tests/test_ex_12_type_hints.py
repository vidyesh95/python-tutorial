import typing

import pytest

from _loader import load

ex = load("t02_intermediate", "ex_12_type_hints")


def test_first():
    assert ex.first([3, 4]) == 3
    assert ex.first([]) is None
    assert ex.first([], default=0) == 0
    assert ex.first("xyz") == "x"
    assert ex.first((7,)) == 7


def test_generic_function_uses_pep695_params():
    assert len(ex.first.__type_params__) == 1


def test_box():
    b = ex.Box(3)
    assert b.map(str).item == "3"
    assert b.map(lambda n: n * 2).map(lambda n: n + 1).item == 7
    assert b.item == 3  # map returns a new Box
    assert ex.Box(None).get_or("fallback") == "fallback"
    assert ex.Box(0).get_or(5) == 0  # falsy but not None
    assert len(ex.Box.__type_params__) == 1


def test_typed_dict_user():
    user = ex.make_user("ada", 36)
    assert user == {"name": "ada", "age": 36}
    assert typing.is_typeddict(ex.User)
    assert ex.is_adult(user)
    assert not ex.is_adult(ex.make_user("kid", 17))
    assert ex.is_adult(ex.make_user("edge", 18))
    with pytest.raises(ValueError):
        ex.make_user("x", -1)


def test_greet_all_protocol():
    class Dog:
        def greet(self):
            return "woof"

    class Robot:
        def greet(self):
            return "beep"

    assert ex.greet_all([Dog(), Robot()]) == ["woof", "beep"]
    assert ex.greet_all([]) == []
    assert ex.greet_all(g for g in [Dog()]) == ["woof"]  # any iterable


def test_apply_n():
    assert ex.apply_n(lambda x: x * 2, 1, 3) == 8
    assert ex.apply_n(lambda x: x + 1, 10, 0) == 10
    with pytest.raises(ValueError):
        ex.apply_n(lambda x: x, 1, -1)
