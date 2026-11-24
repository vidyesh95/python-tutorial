"""Exercise 06 - Input and output (formatting).

None of these functions use input() or print() so they are easy to test; they RETURN the text.

Tasks:
1. format_price: money formatting with a currency sign and thousands separators.
2. format_row: one aligned table row.
3. as_percent: express a fraction as a percentage string.
4. parse_int: clean user input and convert it, falling back to a default.
5. banner: centre a title between fill characters.
"""


def format_price(amount: float) -> str:
    """Format ``amount`` as dollars with thousands separators and 2 decimals.

    Examples:
        format_price(1234.5) -> "$1,234.50"
        format_price(0) -> "$0.00"
        format_price(1000000) -> "$1,000,000.00"
    """
    raise NotImplementedError


def format_row(name: str, qty: int, price: float) -> str:
    """Return ``name`` left-aligned in 10 chars, ``qty`` right-aligned in 5, ``price`` right-aligned
    in 10 with 2 decimals.

    Examples:
        format_row("Tea", 2, 3.5) -> "Tea           2      3.50"
        format_row("Bagel", 10, 2.25) -> "Bagel        10      2.25"
    """
    raise NotImplementedError


def as_percent(part: float, whole: float) -> str:
    """Return ``part / whole`` as a percentage with one decimal; ``"n/a"`` when whole is 0.

    Examples:
        as_percent(1, 4) -> "25.0%"
        as_percent(2, 3) -> "66.7%"
        as_percent(5, 0) -> "n/a"
    """
    raise NotImplementedError


def parse_int(raw: str, default: int = 0) -> int:
    """Strip ``raw`` and convert it to an int; return ``default`` when it is not a valid integer.

    Examples:
        parse_int(" 42\\n") -> 42
        parse_int("abc", default=-1) -> -1
        parse_int("") -> 0
    """
    raise NotImplementedError


def banner(title: str, width: int = 20, fill: str = "=") -> str:
    """Centre ``" title "`` (with a space either side) in ``width`` columns using ``fill``.

    Examples:
        banner("Hi", 10) -> "=== Hi ==="
        banner("Menu", 12, "*") -> "*** Menu ***"
    """
    raise NotImplementedError
