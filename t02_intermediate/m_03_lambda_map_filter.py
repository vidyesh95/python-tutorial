# Lambda, map, filter, sorted and reduce
"""
A lambda is a small anonymous function limited to a single expression:
    lambda x: x * 2
Use it for short throwaway callbacks. For anything named or reused, write a `def`.
map(func, items)      -> lazily applies func to each item
filter(func, items)   -> lazily keeps items where func(item) is truthy
sorted(items, key=f)  -> returns a new sorted list ordered by f(item)
functools.reduce(f, items, start) -> folds items into one value
Comprehensions are often more readable than map/filter, but you will see both.
"""

from functools import reduce
from operator import itemgetter

# Example: lambda
square = (lambda x: x * x)(5)  # call immediately, just to show it is a function
print("square:", square)

# Example: map and filter return lazy iterators; wrap in list() to see values
nums = [1, 2, 3, 4, 5, 6]
print(list(map(lambda n: n * 10, nums)))
print(list(filter(lambda n: n % 2 == 0, nums)))
# The comprehension equivalents
print([n * 10 for n in nums], [n for n in nums if n % 2 == 0])

# map with several iterables; strict=True (3.14+) raises if lengths differ, like zip(strict=True)
print(list(map(lambda a, b: a + b, [1, 2, 3], [10, 20, 30], strict=True)))

# Example: sorted with key
people = [
    {"name": "Ada", "age": 36},
    {"name": "Linus", "age": 28},
    {"name": "Grace", "age": 45},
]
print([p["name"] for p in sorted(people, key=lambda p: p["age"])])
print([p["name"] for p in sorted(people, key=lambda p: p["age"], reverse=True)])

# operator.itemgetter is a faster, clearer alternative to a simple lambda
print([p["name"] for p in sorted(people, key=itemgetter("name"))])

# Sort by several criteria with a tuple key
words = ["pear", "fig", "apple", "kiwi", "date"]
print(sorted(words, key=lambda w: (len(w), w)))  # length first, then alphabetical

# min / max accept key too
print(max(words, key=len), min(words, key=len))

# Example: reduce folds a sequence into one value
print("product:", reduce(lambda acc, n: acc * n, [1, 2, 3, 4], 1))
print("longest:", reduce(lambda a, b: a if len(a) >= len(b) else b, words))

# Reduce with an initial value handles empty input safely
print("empty sum:", reduce(lambda acc, n: acc + n, [], 0))

# Example: lambdas capture variables, not values (late binding)
late = [lambda: i for i in range(3)]  # noqa: B023
print("late binding:", [f() for f in late])  # all 2
bound = [lambda i=i: i for i in range(3)]  # default arg freezes the value
print("early binding:", [f() for f in bound])

# Example: dispatch table of small functions
ops = {"add": lambda a, b: a + b, "mul": lambda a, b: a * b}
print(ops["mul"](3, 4))

"""
Common mistakes
- Assigning a lambda to a name (f = lambda ...). Use def; it gets a real name in tracebacks.
- Writing complicated multi-condition lambdas that nobody can read.
- Forgetting map/filter are lazy: printing them shows <map object>, not values.
- Late binding in loops (see above): use a default argument or functools.partial.
- reduce without an initial value raises TypeError on an empty sequence.
"""

"""
Where this shows up in backend/ML work
- Sorting query results: sorted(rows, key=lambda r: r.created_at).
- Picking the best model: max(results, key=lambda r: r["f1"]).
- Pandas/polars style callbacks: df.apply(lambda row: ...), groupby aggregations.
- Retry/hook registries use small callables stored in dicts.
"""
