import pytest

from _loader import load

ex = load("t02_intermediate", "ex_04_classes_objects")


def test_deposit_and_withdraw():
    acct = ex.BankAccount("ada", 100)
    acct.deposit(50)
    acct.withdraw(30)
    assert acct.balance == 120
    for bad in (0, -5):
        with pytest.raises(ValueError):
            acct.deposit(bad)
    with pytest.raises(ValueError):
        acct.withdraw(1000)
    assert acct.balance == 120  # failed operations change nothing


def test_balance_is_read_only():
    acct = ex.BankAccount("ada")
    assert acct.balance == 0.0
    with pytest.raises(AttributeError):
        acct.balance = 10
    assert isinstance(ex.BankAccount.balance, property)


def test_from_string_is_classmethod():
    acct = ex.BankAccount.from_string("ada:100.5")
    assert (acct.owner, acct.balance) == ("ada", 100.5)

    class Savings(ex.BankAccount):
        pass

    assert type(Savings.from_string("x:1")) is Savings  # uses cls, not a hard-coded class


def test_is_valid_amount_static():
    assert ex.BankAccount.is_valid_amount(1) is True
    assert ex.BankAccount.is_valid_amount(0) is False
    assert ex.BankAccount.is_valid_amount(-3) is False


def test_temperature():
    t = ex.Temperature(100)
    assert t.fahrenheit == 212.0
    t.celsius = 0
    assert t.fahrenheit == 32.0
    with pytest.raises(ValueError):
        t.celsius = -300
    assert t.celsius == 0  # invalid assignment is rejected
    with pytest.raises(ValueError):
        ex.Temperature(-500)
    with pytest.raises(AttributeError):
        t.fahrenheit = 5  # computed property
