# Dictionaries
"""
A dict maps unique, hashable keys to values: {key: value}. Lookup by key is very fast. Since Python 3.7
dicts remember insertion order. Keys must be immutable (str, int, tuple ...); values can be anything.
"""

# Creating dictionaries
# Example
user = {"name": "Ada", "age": 36}
empty: dict[str, int] = {}
from_pairs = dict([("a", 1), ("b", 2)])
from_kwargs = dict(x=1, y=2)
print(user, empty, from_pairs, from_kwargs)
print(dict.fromkeys(["a", "b"], 0))  # {'a': 0, 'b': 0}

# Reading values
# Example
print(user["name"])  # KeyError if the key is missing!
print(user.get("email"))  # None if missing
print(user.get("email", "n/a"))  # custom default
print("age" in user, "email" in user)  # membership checks KEYS

# Adding, updating, removing
# Example
user["email"] = "ada@example.com"  # add
user["age"] = 37  # update
user.update({"city": "London", "age": 38})  # merge several
removed = user.pop("city")  # remove and return
del user["email"]
print(removed, user)
print(user.setdefault("role", "admin"))  # insert only if missing
print(user)

# Looping
# Example
for key in user:
    print(key, end=" ")
print()
for key, value in user.items():
    print(f"{key} = {value}")
print(list(user.keys()), list(user.values()))

# Merging (3.9+)
# Example
defaults = {"theme": "light", "lang": "en"}
overrides = {"theme": "dark"}
print(defaults | overrides)  # right side wins
merged = {**defaults, **overrides, "extra": 1}
print(merged)

# Dict comprehensions
# Example
squares = {n: n**2 for n in range(5)}
print(squares)
inverted = {v: k for k, v in squares.items()}
print(inverted)
print({k: v for k, v in squares.items() if v % 2 == 0})

# Nested dictionaries
# Example
config = {"db": {"host": "localhost", "port": 5432}, "debug": True}
print(config["db"]["port"])
print(config.get("cache", {}).get("ttl", 60))  # safe nested access

# Counting and grouping patterns
# Example
text = "mississippi"
counts: dict[str, int] = {}
for ch in text:
    counts[ch] = counts.get(ch, 0) + 1
print(counts)

groups: dict[int, list[str]] = {}
for word in ["pea", "fig", "plum", "kiwi", "apple"]:
    groups.setdefault(len(word), []).append(word)
print(groups)

# Sorting a dict by value
# Example
print(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
print(max(counts, key=counts.__getitem__))  # key with the largest value

# Common mistakes
"""
1. Indexing a missing key with d["x"] raises KeyError; use d.get("x") or check  "x" in d.
2. Using a list (mutable) as a key: TypeError: unhashable type. Use a tuple.
3. Modifying a dict's size while looping over it raises RuntimeError; loop over list(d) instead.
4. Expecting  "value" in d  to look at values; it checks keys. Use  "value" in d.values().
5. Forgetting that d2 = d1 does not copy; use d1.copy() or dict(d1) (shallow).
"""
