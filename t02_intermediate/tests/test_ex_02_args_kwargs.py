import pytest

from _loader import load

ex = load("t02_intermediate", "ex_02_args_kwargs")


def test_total():
    assert ex.total(1, 2, 3.5) == 6.5
    assert ex.total() == 0
    assert ex.total(-1, 1) == 0


def test_build_url():
    assert (
        ex.build_url("example.com", port=8080, page=2, q="x")
        == "http://example.com:8080?page=2&q=x"
    )
    assert ex.build_url("example.com", secure=True) == "https://example.com:80"
    with pytest.raises(TypeError):
        ex.build_url("example.com", 8080)  # port is keyword-only


def test_merge_configs():
    a = {"a": 1, "b": 2}
    assert ex.merge_configs(a, {"b": 3}, {"c": 4}) == {"a": 1, "b": 3, "c": 4}
    assert a == {"a": 1, "b": 2}  # not mutated
    assert ex.merge_configs() == {}


def test_first_and_rest():
    assert ex.first_and_rest([1, 2, 3]) == (1, [2, 3])
    assert ex.first_and_rest([9]) == (9, [])
    with pytest.raises(ValueError):
        ex.first_and_rest([])


def test_clamp_positional_only():
    assert ex.clamp(15, 0, 10) == 10
    assert ex.clamp(-5, 0, 10) == 0
    assert ex.clamp(5, 0, 10) == 5
    with pytest.raises(TypeError):
        ex.clamp(value=5, low=0, high=10)
