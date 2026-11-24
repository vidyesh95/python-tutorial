# Sets
"""
A set is an UNORDERED collection of UNIQUE, hashable items. Membership tests are very fast, duplicates
disappear automatically, and sets support maths-style operations (union, intersection, difference).
A frozenset is the immutable version.
"""

# Creating sets
# Example
colors = {"red", "green", "blue"}  # duplicate is dropped
print(colors, len(colors))
print(set([1, 2, 2, 3]), set("hello"))
empty = set()  # {} would create an empty DICT
print(type(empty), type({}))

# Adding and removing
# Example
colors.add("yellow")
colors.discard("purple")  # no error if missing
colors.remove("red")  # KeyError if missing
print(colors)
item = colors.pop()  # removes an arbitrary item
print(item in colors)

# Membership is fast
# Example
big = set(range(100_000))
print(99_999 in big)

# Set algebra
"""
a | b  union          a & b  intersection
a - b  difference     a ^ b  symmetric difference (in exactly one)
a <= b subset         a >= b superset        a.isdisjoint(b)
"""
# Example
a = {1, 2, 3, 4}
b = {3, 4, 5}
print(a | b, a & b, a - b, a ^ b)
print({3, 4} <= a, a >= {1}, a.isdisjoint({9}))
print(a.union(b), a.intersection(b))  # method forms accept any iterable

# Removing duplicates
# Example
data = [3, 1, 3, 2, 1]
print(set(data))  # order lost
print(list(dict.fromkeys(data)))  # unique AND keeps first-seen order
print(sorted(set(data)))

# Set comprehension
# Example
print({n % 3 for n in range(10)})
print({word[0] for word in ["apple", "avocado", "banana"]})

# Sets contain only hashable items
# Example
print({(1, 2), (1, 2)})  # tuples are fine
# {[1, 2]} would raise TypeError: unhashable type: 'list'

# frozenset
# Example
fs = frozenset([1, 2, 3])
print(fs, {fs: "can be a dict key"})

# Practical use: what do two lists have in common?
# Example
alice = {"python", "sql", "git"}
bob = {"python", "docker", "git"}
print("shared:", alice & bob)
print("only alice:", alice - bob)
print("everything:", sorted(alice | bob))

# Common mistakes
"""
1. {} is an empty dict, not an empty set. Use set().
2. Relying on order - sets are unordered; use sorted(s) when you need a stable order.
3. Trying to index a set: s[0] raises TypeError.
4. Putting lists or dicts inside a set (unhashable). Use tuples or frozensets.
5. Using remove() on something that may not be there; use discard().
"""
