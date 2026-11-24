"""Exercise 16 - Modules and imports.

Tasks:
1. circle_area: use the math module.
2. shuffled: reproducible shuffle with the random module (does not modify the input).
3. file_extension: use os.path to get an extension.
4. get_env: read an environment variable with a default.
5. python_at_least: compare against sys.version_info.
"""


def circle_area(radius: float) -> float:
    """Return the area of a circle (use ``math.pi``). Negative radius raises ValueError.

    Examples:
        circle_area(1) -> 3.141592653589793
        circle_area(0) -> 0.0
        circle_area(-1) -> raises ValueError
    """
    raise NotImplementedError


def shuffled(items: list, seed: int) -> list:
    """Return a NEW shuffled list; the same seed must always give the same order.
    The input list must not be modified. Use ``random.Random(seed)``.

    Examples:
        sorted(shuffled([1, 2, 3, 4], seed=1)) -> [1, 2, 3, 4]
        shuffled([1, 2, 3, 4], 5) == shuffled([1, 2, 3, 4], 5) -> True
    """
    raise NotImplementedError


def file_extension(filename: str) -> str:
    """Return the extension including the dot, lower-cased; "" if there is none.

    Examples:
        file_extension("report.CSV") -> ".csv"
        file_extension("archive.tar.gz") -> ".gz"
        file_extension("README") -> ""
        file_extension("/path/to/.bashrc") -> ""
    """
    raise NotImplementedError


def get_env(name: str, default: str = "") -> str:
    """Return the value of environment variable ``name`` or ``default`` if it is not set.

    Examples:
        get_env("HOME") -> "/home/you"   (whatever your HOME is)
        get_env("SURELY_NOT_SET_12345", "fallback") -> "fallback"
    """
    raise NotImplementedError


def python_at_least(major: int, minor: int = 0) -> bool:
    """True if the running Python is at least ``major.minor``.

    Examples:
        python_at_least(3) -> True
        python_at_least(3, 15) -> True on Python 3.15+
        python_at_least(99) -> False
    """
    raise NotImplementedError
