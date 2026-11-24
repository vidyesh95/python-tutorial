from _loader import load

ex = load("t01_fundamentals", "ex_14_scope")


def test_make_counter():
    c = ex.make_counter()
    assert [c(), c(), c()] == [1, 2, 3]
    d = ex.make_counter(10)
    assert d() == 11
    assert c() == 4  # independent of d


def test_make_multiplier():
    assert ex.make_multiplier(3)(4) == 12
    assert ex.make_multiplier(0.5)(10) == 5.0
    double, triple = ex.make_multiplier(2), ex.make_multiplier(3)
    assert (double(5), triple(5)) == (10, 15)


def test_make_accumulator():
    acc = ex.make_accumulator()
    assert acc(5) == 5
    assert acc(10) == 15
    assert acc(-3) == 12
    other = ex.make_accumulator()
    assert other(1) == 1


def test_compose():
    assert ex.compose(str.upper, str.strip)("  hi ") == "HI"
    assert ex.compose(len, str)(12345) == 5
    assert ex.compose(lambda x: x + 1, lambda x: x * 2)(5) == 11


def test_make_adders():
    assert [f(10) for f in ex.make_adders([1, 2, 3])] == [11, 12, 13]
    assert ex.make_adders([]) == []
    assert ex.make_adders([5])[0](0) == 5
