"""Exercise 08 - Loops.

Tasks:
1. sum_of_evens: add the even numbers from 1 up to and including ``limit``.
2. fizzbuzz_list: FizzBuzz for 1..n as a list of strings.
3. first_repeated: first item that appears a second time while scanning left to right.
4. number_lines: prefix lines with their 1-based number using enumerate.
5. collatz_steps: count the steps of the Collatz sequence until it reaches 1 (while loop).
"""


def sum_of_evens(limit: int) -> int:
    """Return the sum of all even numbers in ``1..limit`` (inclusive).

    Examples:
        sum_of_evens(10) -> 30
        sum_of_evens(1) -> 0
        sum_of_evens(0) -> 0
    """
    total = 0
    for n in range(2, limit + 1, 2):
        total += n
    return total


def fizzbuzz_list(n: int) -> list[str]:
    """Return FizzBuzz values for 1..n ("Fizz", "Buzz", "FizzBuzz" or the number as text).

    Examples:
        fizzbuzz_list(5) -> ["1", "2", "Fizz", "4", "Buzz"]
        fizzbuzz_list(0) -> []
    """
    result: list[str] = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result


def first_repeated(items: list) -> object | None:
    """Return the first item whose second occurrence appears earliest, or None if all are unique.

    Examples:
        first_repeated([1, 2, 3, 2, 1]) -> 2
        first_repeated(["a", "b"]) -> None
        first_repeated([]) -> None
    """
    seen = set()
    for item in items:
        if item in seen:
            return item
        seen.add(item)
    return None


def number_lines(lines: list[str]) -> list[str]:
    """Return each line prefixed with ``"<n>: "`` starting at 1.

    Examples:
        number_lines(["a", "b"]) -> ["1: a", "2: b"]
        number_lines([]) -> []
    """
    return [f"{i}: {line}" for i, line in enumerate(lines, start=1)]


def collatz_steps(n: int) -> int:
    """Number of steps to reach 1: if n is even halve it, otherwise do 3n + 1. ``n`` must be >= 1.

    Examples:
        collatz_steps(1) -> 0
        collatz_steps(6) -> 8
        collatz_steps(27) -> 111
        collatz_steps(0) -> raises ValueError
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    steps = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps
