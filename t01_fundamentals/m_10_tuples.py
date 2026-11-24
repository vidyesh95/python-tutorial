# Tuples
"""
A tuple is an ordered, IMMUTABLE collection written with parentheses. Use it for a fixed group of related
values (a point, an RGB colour, a database row) and anywhere you need a hashable sequence (dict keys, set items).
"""

# Creating tuples
# Example
point = (3, 4)
single = (42,)  # the comma makes the tuple, not the parentheses!
not_a_tuple = 42
no_parens = 1, 2, 3  # parentheses are optional
print(point, single, type(single), type(not_a_tuple), no_parens)
print(tuple([1, 2]), tuple("ab"), ())

# Indexing, slicing, methods
# Example
colors = ("red", "green", "blue", "green")
print(colors[0], colors[-1], colors[1:3])
print(colors.count("green"), colors.index("blue"), len(colors))
print("red" in colors)

# Immutability
"""
You cannot assign to an item: colors[0] = "pink" raises TypeError.
But a tuple that CONTAINS a mutable object (like a list) lets you change that inner object.
"""
# Example
holder = ([1, 2], "x")
holder[0].append(3)
print(holder)  # ([1, 2, 3], 'x')

# Unpacking
"""
Unpacking assigns each item to its own variable in one line. The number of names must match,
unless you use * to collect the rest into a list.
"""
# Example
x, y = point
print(x, y)
name, age, city = ("Ada", 36, "London")
print(name, age, city)

head, *tail = (1, 2, 3, 4)
print(head, tail)  # 1 [2, 3, 4]
first, *_, last = (1, 2, 3, 4, 5)  # _ means "I don't care"
print(first, last)

# Swapping variables with tuples
# Example
a, b = 1, 2
a, b = b, a
print(a, b)  # 2 1


# Returning several values from a function
# Example
def min_max(values: list[int]) -> tuple[int, int]:
    return min(values), max(values)  # actually returns one tuple


low, high = min_max([4, 9, 1, 7])
print(low, high)

# Nested unpacking and loops
# Example
people = [("Ann", (30, "NYC")), ("Bob", (25, "LA"))]
for person_name, (person_age, person_city) in people:
    print(person_name, person_age, person_city)

# Tuples as dictionary keys and set members
# Example
distances = {(0, 0): "origin", (1, 2): "A"}
print(distances[(1, 2)])
print({(1, 2), (1, 2), (2, 1)})

# Comparison is element by element
# Example
print((1, 2) < (1, 3), (2, 0) > (1, 99))

# Named tuples: tuples with field names
# Example
from collections import namedtuple  # noqa: E402

Point = namedtuple("Point", ["x", "y"])
p = Point(1, 2)
print(p, p.x, p[1])

# Common mistakes
"""
1. Forgetting the trailing comma in a one-item tuple:  (5)  is just the int 5; write (5,).
2. Trying to modify a tuple: t[0] = 1 raises TypeError; build a new one with  t = (1,) + t[1:].
3. Unpacking the wrong number of values: a, b = (1, 2, 3) raises ValueError. Use *rest.
4. Assuming a tuple is deeply immutable - the objects inside may still be mutable.
5. Using a list where a hashable key is required (dict keys, set items); convert it with tuple().
"""
