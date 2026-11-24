from _loader import load

ex = load("t01_fundamentals", "ex_01_variables")


def test_swap():
    assert ex.swap(1, 2) == (2, 1)
    assert ex.swap("x", "y") == ("y", "x")
    assert ex.swap(None, 0) == (0, None)


def test_rectangle_stats():
    assert ex.rectangle_stats(3, 4) == (12, 14)
    assert ex.rectangle_stats(0, 5) == (0, 10)
    assert ex.rectangle_stats(2.5, 2) == (5.0, 9.0)


def test_full_name():
    assert ex.full_name("Ada", "Lovelace") == "Ada Lovelace"
    assert ex.full_name("  Alan ", " Turing") == "Alan Turing"


def test_next_birthday_message():
    assert ex.next_birthday_message("Ada", 36) == "Ada will be 37 next year"
    assert ex.next_birthday_message("Bo", 0) == "Bo will be 1 next year"
