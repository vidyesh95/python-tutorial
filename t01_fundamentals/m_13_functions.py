# Functions
"""
A function is a named, reusable block of code. Define it with def, give it parameters, and send a value
back with return. A function without return gives back None. Good functions do one thing, have a clear name,
a docstring, and type hints.
"""


# Defining and calling
# Example
def greet(name: str) -> str:
    """Return a greeting for ``name``."""
    return f"Hello, {name}!"


print(greet("Ada"))


# Parameters vs arguments, positional vs keyword
# Example
def power(base: float, exponent: float) -> float:
    """Return base raised to exponent."""
    return base**exponent


print(power(2, 5))  # positional
print(power(exponent=5, base=2))  # keyword - order does not matter


# Default values
# Example
def connect(host: str, port: int = 5432, *, secure: bool = True) -> str:
    """Build a connection string. Parameters after ``*`` must be passed by keyword."""
    scheme = "https" if secure else "http"
    return f"{scheme}://{host}:{port}"


print(connect("db.local"))
print(connect("db.local", 3306, secure=False))


# Returning several values
# Example
def stats(values: list[float]) -> tuple[float, float, float]:
    """Return (min, max, mean)."""
    return min(values), max(values), sum(values) / len(values)


low, high, mean = stats([2, 4, 9])
print(low, high, mean)


# *args and **kwargs
"""
*args collects extra positional arguments into a tuple; **kwargs collects extra keyword arguments into a dict.
"""


# Example
def describe(*args: int, **kwargs: str) -> str:
    return f"args={args} kwargs={kwargs}"


print(describe(1, 2, 3, color="red", size="L"))
numbers = [1, 2, 3]
options = {"color": "blue"}
print(describe(*numbers, **options))  # unpack when calling


# Positional-only and keyword-only markers
# Example
def clamp(value: float, /, low: float = 0, high: float = 1) -> float:
    """``value`` is positional-only (before the /)."""
    return max(low, min(high, value))


print(clamp(5, high=3), clamp(-1))


# Docstrings and help()
# Example
print(greet.__doc__)
print(greet.__name__, greet.__annotations__)


# Mutable default argument trap
"""
Default values are evaluated ONCE, when the function is defined. A list default is shared between calls:

    def add(item, bucket=[]):      # BAD
        bucket.append(item)
        return bucket

Use None and create the list inside instead.
"""


# Example
def add(item: str, bucket: list[str] | None = None) -> list[str]:
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket


print(add("a"), add("b"))  # independent lists


# Functions are objects
# Example
def apply(func, value):  # noqa: ANN001 - kept untyped to show the idea
    return func(value)


print(apply(str.upper, "abc"), apply(len, "abc"))
shout = greet  # another name for the same function
print(shout("Bob"))

# Lambda: a tiny anonymous function
# Example
square = lambda n: n * n  # noqa: E731
print(square(7))
print(sorted(["bb", "a", "ccc"], key=lambda s: -len(s)))


# Recursion: a function that calls itself
# Example
def factorial(n: int) -> int:
    """Return n! recursively."""
    if n <= 1:  # base case stops the recursion
        return 1
    return n * factorial(n - 1)


print(factorial(5))

# Common mistakes
"""
1. Forgetting return: the function silently gives back None.
2. Using a mutable default argument (list/dict/set) - use None as the default.
3. Printing instead of returning: print() shows a value, return hands it to the caller.
4. Calling greet instead of greet(): without parentheses you reference the function, you do not run it.
5. Missing/extra arguments: TypeError: greet() missing 1 required positional argument.
6. Recursion without a base case runs until RecursionError.
"""
