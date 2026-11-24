"""Exercise 15 - Exceptions.

Tasks:
1. safe_int: convert text to int, returning a default on failure.
2. safe_divide: division that returns None instead of raising ZeroDivisionError.
3. withdraw: raise custom exceptions for invalid or too-large amounts.
4. parse_all: split a list of strings into parsed integers and the invalid entries.
5. first_valid_int: use try/except inside a loop and return the first parsable value.

The custom exceptions below are used by ``withdraw`` and the tests.
"""


class BankError(Exception):
    """Base class for banking errors."""


class InvalidAmountError(BankError, ValueError):
    """Raised when an amount is zero or negative."""


class InsufficientFundsError(BankError):
    """Raised when the balance is too low."""


def safe_int(text: str, default: int | None = None) -> int | None:
    """Convert ``text`` to int; return ``default`` if conversion fails (ValueError or TypeError).

    Examples:
        safe_int("12") -> 12
        safe_int("x", default=0) -> 0
        safe_int("x") -> None
        safe_int(None) -> None
    """
    try:
        return int(text)
    except ValueError, TypeError:
        return default


def safe_divide(a: float, b: float) -> float | None:
    """Return ``a / b`` or None when ``b`` is zero.

    Examples:
        safe_divide(10, 4) -> 2.5
        safe_divide(1, 0) -> None
        safe_divide(0, 5) -> 0.0
    """
    try:
        return a / b
    except ZeroDivisionError:
        return None


def withdraw(balance: float, amount: float) -> float:
    """Return the new balance. Raise ``InvalidAmountError`` if amount <= 0 and
    ``InsufficientFundsError`` if amount > balance.

    Examples:
        withdraw(100, 30) -> 70
        withdraw(100, 100) -> 0
        withdraw(100, 0) -> raises InvalidAmountError
        withdraw(50, 80) -> raises InsufficientFundsError
    """
    if amount <= 0:
        raise InvalidAmountError(f"amount must be positive, got {amount}")
    if amount > balance:
        raise InsufficientFundsError(f"balance {balance} is less than {amount}")
    return balance - amount


def parse_all(items: list[str]) -> tuple[list[int], list[str]]:
    """Return ``(valid_ints, invalid_strings)`` preserving order.

    Examples:
        parse_all(["1", "x", "3"]) -> ([1, 3], ["x"])
        parse_all([]) -> ([], [])
        parse_all(["a"]) -> ([], ["a"])
    """
    valid: list[int] = []
    invalid: list[str] = []
    for item in items:
        try:
            valid.append(int(item))
        except ValueError:
            invalid.append(item)
    return valid, invalid


def first_valid_int(items: list[str]) -> int:
    """Return the first item that parses as an int. Raise ``LookupError`` if none does.

    Examples:
        first_valid_int(["a", "b", "7", "8"]) -> 7
        first_valid_int(["a"]) -> raises LookupError
        first_valid_int([]) -> raises LookupError
    """
    for item in items:
        try:
            return int(item)
        except ValueError:
            continue
    raise LookupError("no valid integer found")
