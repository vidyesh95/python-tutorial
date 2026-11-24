"""Exercise 01 - Variables.

Tasks:
1. swap: return the two values in swapped order.
2. rectangle_stats: compute area and perimeter and return both.
3. full_name: combine first and last name into one string.
4. next_birthday_message: build a message using variables and an f-string.
"""


def swap(a: object, b: object) -> tuple[object, object]:
    """Return ``(b, a)``.

    Examples:
        swap(1, 2) -> (2, 1)
        swap("x", "y") -> ("y", "x")
    """
    a, b = b, a
    return a, b


def rectangle_stats(width: float, height: float) -> tuple[float, float]:
    """Return ``(area, perimeter)`` of a rectangle.

    Examples:
        rectangle_stats(3, 4) -> (12, 14)
        rectangle_stats(0, 5) -> (0, 10)
    """
    area = width * height
    perimeter = 2 * (width + height)
    return area, perimeter


def full_name(first: str, last: str) -> str:
    """Join first and last name with one space; strip extra whitespace around each part.

    Examples:
        full_name("Ada", "Lovelace") -> "Ada Lovelace"
        full_name("  Alan ", " Turing") -> "Alan Turing"
    """
    return f"{first.strip()} {last.strip()}"


def next_birthday_message(name: str, age: int) -> str:
    """Return ``"<name> will be <age + 1> next year"``.

    Examples:
        next_birthday_message("Ada", 36) -> "Ada will be 37 next year"
        next_birthday_message("Bo", 0) -> "Bo will be 1 next year"
    """
    return f"{name} will be {age + 1} next year"
