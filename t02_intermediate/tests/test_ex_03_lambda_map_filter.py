from _loader import load

ex = load("t02_intermediate", "ex_03_lambda_map_filter")


def test_sort_words():
    assert ex.sort_words(["pear", "fig", "apple", "kiwi"]) == ["fig", "kiwi", "pear", "apple"]
    words = ["b", "a"]
    assert ex.sort_words(words) == ["a", "b"]
    assert words == ["b", "a"]  # original untouched
    assert ex.sort_words([]) == []


def test_top_n_by():
    items = [{"v": 1}, {"v": 9}, {"v": 5}]
    assert ex.top_n_by(items, "v", 2) == [{"v": 9}, {"v": 5}]
    assert ex.top_n_by(items, "v", 10) == [{"v": 9}, {"v": 5}, {"v": 1}]
    assert ex.top_n_by([], "v", 3) == []


def test_product():
    assert ex.product([2, 3, 4]) == 24
    assert ex.product([]) == 1
    assert ex.product([5, 0]) == 0


def test_compose():
    inc = lambda x: x + 1  # noqa: E731
    times10 = lambda x: x * 10  # noqa: E731
    assert ex.compose(inc, times10)(2) == 30
    assert ex.compose(times10, inc)(2) == 21
    assert ex.compose()(7) == 7


def test_parse_positive_ints():
    assert ex.parse_positive_ints(["3", "x", "0", "12", "-4", ""]) == [3, 12]
    assert ex.parse_positive_ints([]) == []
    assert ex.parse_positive_ints(["007"]) == [7]
