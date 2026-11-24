from _loader import load

ex = load("t01_fundamentals", "ex_06_input_output")


def test_format_price():
    assert ex.format_price(1234.5) == "$1,234.50"
    assert ex.format_price(0) == "$0.00"
    assert ex.format_price(1000000) == "$1,000,000.00"


def test_format_row():
    assert ex.format_row("Tea", 2, 3.5) == "Tea           2      3.50"
    assert ex.format_row("Bagel", 10, 2.25) == "Bagel        10      2.25"
    assert len(ex.format_row("x", 1, 1.0)) == 25


def test_as_percent():
    assert ex.as_percent(1, 4) == "25.0%"
    assert ex.as_percent(2, 3) == "66.7%"
    assert ex.as_percent(5, 0) == "n/a"
    assert ex.as_percent(0, 5) == "0.0%"


def test_parse_int():
    assert ex.parse_int(" 42\n") == 42
    assert ex.parse_int("abc", default=-1) == -1
    assert ex.parse_int("") == 0
    assert ex.parse_int("-5") == -5


def test_banner():
    assert ex.banner("Hi", 10) == "=== Hi ==="
    assert ex.banner("Menu", 12, "*") == "*** Menu ***"
    assert len(ex.banner("Title")) == 20
