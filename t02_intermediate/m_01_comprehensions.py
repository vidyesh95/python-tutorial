# Comprehensions
"""
A comprehension builds a collection from an iterable in one expression.
Shapes:
    [expr for x in items if cond]          -> list
    {k: v for x in items}                  -> dict
    {expr for x in items}                  -> set (unique values)
    (expr for x in items)                  -> generator (lazy, one item at a time)
They are usually clearer and faster than building a list with .append() in a loop.
"""

from collections.abc import Iterator

# Example: list comprehension
numbers = [1, 2, 3, 4, 5, 6]
squares = [n * n for n in numbers]
print("squares:", squares)

# Filtering with an `if` at the end
evens = [n for n in numbers if n % 2 == 0]
print("evens:", evens)

# Conditional expression (if/else) goes BEFORE the `for`
labels = ["even" if n % 2 == 0 else "odd" for n in numbers]
print("labels:", labels)

# Example: nested loops (read left to right, like nested for statements)
pairs = [(x, y) for x in range(3) for y in range(3) if x != y]
print("pairs:", pairs)

# Flatten a matrix
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flat = [value for row in matrix for value in row]
print("flat:", flat)

# Example: dict comprehension
words = ["apple", "banana", "cherry"]
lengths = {word: len(word) for word in words}
print("lengths:", lengths)

# Invert a dict (values must be unique and hashable)
inverted = {length: word for word, length in lengths.items()}
print("inverted:", inverted)

# Example: set comprehension removes duplicates
first_letters = {word[0] for word in ["apple", "avocado", "banana", "blueberry"]}
print("first letters:", sorted(first_letters))

# Example: generator expression is lazy; nothing is computed until you iterate
gen = (n * n for n in range(1_000_000))
print("generator object:", type(gen).__name__)
print("sum of first 5 squares:", sum(n * n for n in range(5)))  # no extra brackets needed

# Generators can be consumed only once
small = (n for n in range(3))
print(list(small), list(small))  # second list is empty


def read_lines(text: str) -> Iterator[str]:
    """A tiny pipeline stage: strip each line, skip blanks."""
    return (line.strip() for line in text.splitlines() if line.strip())


print(list(read_lines("  a  \n\n b \n")))


# Example: the walrus operator avoids calling an expensive function twice
def expensive(n: int) -> int:
    return n * 10


results = [y for n in range(5) if (y := expensive(n)) > 10]
print("results:", results)

"""
Common mistakes
- Cramming too much logic in: if it needs more than one `for` plus one `if`, use a loop.
- Using a list comprehension just for side effects, e.g. [print(x) for x in xs].
  Use a plain for loop instead.
- Putting `if/else` after the `for` (a syntax error). Filter `if` goes at the end,
  conditional-expression `if/else` goes at the start.
- Building a huge list when a generator would do: sum([x for x in big]) wastes memory.
- Forgetting a generator is exhausted after one pass.
"""

"""
Where this shows up in backend/ML work
- Shaping API responses: [UserOut(**row) for row in rows].
- Building lookup tables: {user.id: user for user in users}.
- Streaming big files or datasets lazily with generator expressions so memory stays flat.
- Feature engineering in plain Python: [tokenize(doc) for doc in corpus].
"""
