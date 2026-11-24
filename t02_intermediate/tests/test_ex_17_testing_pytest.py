"""Live example of pytest features applied to the ex_17 functions.

Read this file: it shows fixtures, parametrize, pytest.raises, tmp_path, monkeypatch.
"""

import pytest

from _loader import load

ex = load("t02_intermediate", "ex_17_testing_pytest")


# parametrize: one test body, many cases
@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (1, "1"),
        (2, "2"),
        (3, "Fizz"),
        (5, "Buzz"),
        (9, "Fizz"),
        (10, "Buzz"),
        (15, "FizzBuzz"),
        (30, "FizzBuzz"),
    ],
)
def test_fizzbuzz(n, expected):
    assert ex.fizzbuzz(n) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A man, a plan, a canal: Panama", True),
        ("racecar", True),
        ("hello", False),
        ("", True),  # edge case: empty string
        ("No 'x' in Nixon", True),
        ("ab", False),
    ],
)
def test_is_palindrome(text, expected):
    assert ex.is_palindrome(text) is expected


# fixture: a fresh cart for each test that asks for it
@pytest.fixture
def cart():
    c = ex.ShoppingCart()
    c.add("apple", 0.5, 4)
    c.add("book", 12.0)
    return c


def test_cart_total_and_len(cart):
    assert cart.total() == 14.0
    assert len(cart) == 2


def test_cart_starts_empty():
    empty = ex.ShoppingCart()
    assert empty.total() == 0
    assert len(empty) == 0


def test_cart_fixture_is_fresh_each_time(cart):
    cart.add("pen", 1.0)
    assert len(cart) == 3  # not affected by other tests


# pytest.raises with match
@pytest.mark.parametrize(("price", "qty"), [(1.0, 0), (1.0, -1), (-1.0, 1)])
def test_cart_rejects_bad_input(cart, price, qty):
    with pytest.raises(ValueError):
        cart.add("bad", price, qty)
    assert len(cart) == 2  # rejected items are not stored


# tmp_path: a real temporary directory
def test_read_config(tmp_path):
    path = tmp_path / "app.env"
    path.write_text("# comment\n\nHOST = localhost\nURL=http://x/?a=b\nEMPTY=\n", encoding="utf-8")
    assert ex.read_config(path) == {"HOST": "localhost", "URL": "http://x/?a=b", "EMPTY": ""}


def test_read_config_invalid_line(tmp_path):
    path = tmp_path / "bad.env"
    path.write_text("GOOD=1\nnot a pair\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a pair"):
        ex.read_config(path)


# monkeypatch: safely change environment variables
def test_get_api_key_present(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    assert ex.get_api_key() == "secret"


@pytest.mark.parametrize("value", [None, ""])
def test_get_api_key_missing(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("API_KEY", raising=False)
    else:
        monkeypatch.setenv("API_KEY", value)
    with pytest.raises(KeyError, match="API_KEY is not set"):
        ex.get_api_key()
