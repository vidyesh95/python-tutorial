import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_15_exceptions")


def test_safe_int():
    assert ex.safe_int("12") == 12
    assert ex.safe_int("x", default=0) == 0
    assert ex.safe_int("x") is None
    assert ex.safe_int(None) is None


def test_safe_divide():
    assert ex.safe_divide(10, 4) == 2.5
    assert ex.safe_divide(1, 0) is None
    assert ex.safe_divide(0, 5) == 0.0


def test_withdraw_ok():
    assert ex.withdraw(100, 30) == 70
    assert ex.withdraw(100, 100) == 0


def test_withdraw_errors():
    with pytest.raises(ex.InvalidAmountError):
        ex.withdraw(100, 0)
    with pytest.raises(ex.InvalidAmountError):
        ex.withdraw(100, -5)
    with pytest.raises(ex.InsufficientFundsError):
        ex.withdraw(50, 80)


def test_custom_exception_hierarchy():
    assert issubclass(ex.InsufficientFundsError, ex.BankError)
    assert issubclass(ex.InvalidAmountError, ex.BankError)
    assert issubclass(ex.BankError, Exception)


def test_parse_all():
    assert ex.parse_all(["1", "x", "3"]) == ([1, 3], ["x"])
    assert ex.parse_all([]) == ([], [])
    assert ex.parse_all(["a"]) == ([], ["a"])


def test_first_valid_int():
    assert ex.first_valid_int(["a", "b", "7", "8"]) == 7
    assert ex.first_valid_int(["-2"]) == -2
    with pytest.raises(LookupError):
        ex.first_valid_int(["a"])
    with pytest.raises(LookupError):
        ex.first_valid_int([])
