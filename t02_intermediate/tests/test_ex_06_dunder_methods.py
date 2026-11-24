import pytest

from _loader import load

ex = load("t02_intermediate", "ex_06_dunder_methods")


def test_money_repr_and_str():
    m = ex.Money(1050)
    assert repr(m) == "Money(1050, 'USD')"
    assert str(m) == "USD 10.50"
    assert str(ex.Money(5, "EUR")) == "EUR 0.05"


def test_money_equality_hash_and_order():
    assert ex.Money(100) == ex.Money(100)
    assert ex.Money(100) != ex.Money(100, "EUR")
    assert ex.Money(100) != "USD 1.00"  # NotImplemented falls back to False
    assert len({ex.Money(1), ex.Money(1), ex.Money(2)}) == 2
    assert ex.Money(1) < ex.Money(2)
    assert sorted([ex.Money(3), ex.Money(1)]) == [ex.Money(1), ex.Money(3)]
    assert ex.Money(2) >= ex.Money(2)
    with pytest.raises(ValueError):
        _ = ex.Money(1) < ex.Money(1, "EUR")


def test_money_add():
    assert ex.Money(100) + ex.Money(250) == ex.Money(350)
    with pytest.raises(ValueError):
        ex.Money(1) + ex.Money(1, "EUR")


def test_playlist_sequence_protocol():
    p = ex.Playlist(["a", "b", "c"])
    assert len(p) == 3
    assert p[0] == "a" and p[-1] == "c"
    sliced = p[1:]
    assert isinstance(sliced, ex.Playlist) and list(sliced) == ["b", "c"]
    assert list(p) == ["a", "b", "c"]
    assert "b" in p
    with pytest.raises(IndexError):
        p[10]


def test_playlist_add_returns_new():
    a, b = ex.Playlist(["x"]), ex.Playlist(["y", "z"])
    c = a + b
    assert list(c) == ["x", "y", "z"]
    assert len(a) == 1 and len(b) == 2


def test_polynomial_call_and_bool():
    p = ex.Polynomial([1, 2, 3])  # 1 + 2x + 3x^2
    assert p(0) == 1
    assert p(2) == 17
    assert ex.Polynomial([5])(100) == 5
    assert bool(p) is True
    assert bool(ex.Polynomial([])) is False
    assert bool(ex.Polynomial([0, 0])) is False
