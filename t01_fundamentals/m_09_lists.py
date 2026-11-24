# Lists
"""
A list is an ordered, MUTABLE collection written with square brackets. It can hold any mix of types,
allows duplicates, and is the most-used data structure in Python.
"""

# Creating lists
# Example
empty: list[int] = []
numbers = [5, 3, 8, 1]
mixed = [1, "two", 3.0, [4, 5]]
print(numbers, mixed, list("abc"), list(range(3)))

# Indexing and slicing (same rules as strings)
# Example
print(numbers[0], numbers[-1])  # 5 1
print(numbers[1:3])  # [3, 8]
print(numbers[::-1])  # [1, 8, 3, 5]
print(mixed[3][0])  # 4  (nested list)

# Adding items
# Example
fruits = ["apple", "banana"]
fruits.append("cherry")  # add to the end
fruits.insert(1, "avocado")  # add at index 1
fruits.extend(["date", "elderberry"])  # add many
print(fruits)
print(fruits + ["fig"])  # + builds a new list

# Removing items
# Example
fruits.remove("avocado")  # by value (first match)
last = fruits.pop()  # remove and return the last item
first = fruits.pop(0)  # remove and return index 0
del fruits[0]  # delete by index
print(last, first, fruits)
fruits.clear()
print(fruits)

# Searching and counting
# Example
nums = [4, 2, 9, 2, 7]
print(nums.index(9), nums.count(2), 7 in nums, len(nums))
print(min(nums), max(nums), sum(nums))

# Sorting
"""
list.sort() sorts IN PLACE and returns None. sorted(list) returns a NEW sorted list.
Both accept key= and reverse=.
"""
# Example
print(sorted(nums))
print(sorted(nums, reverse=True))
words = ["pear", "fig", "banana"]
words.sort(key=len)
print(words)
nums.reverse()  # in place
print(nums)

# Mutability: assignment does not copy!
# Example
a = [1, 2, 3]
b = a  # same list, two names
b.append(4)
print(a)  # [1, 2, 3, 4]
c = a.copy()  # shallow copy (also a[:] or list(a))
c.append(5)
print(a, c)

# Nested lists and shallow copies
# Example
grid = [[0] * 3 for _ in range(2)]  # correct: independent rows
grid[0][0] = 1
print(grid)
bad = [[0] * 3] * 2  # wrong: both rows are the SAME list
bad[0][0] = 1
print(bad)  # [[1, 0, 0], [1, 0, 0]]

# List comprehensions
# Example
squares = [n**2 for n in range(6)]
evens = [n for n in range(10) if n % 2 == 0]
labels = ["big" if n > 2 else "small" for n in range(5)]
pairs = [(x, y) for x in range(2) for y in range(2)]
print(squares, evens, labels, pairs)

# Unpacking and star
# Example
first_item, *middle, last_item = [1, 2, 3, 4, 5]
print(first_item, middle, last_item)

# Useful helpers
# Example
print(list(zip("abc", [1, 2, 3], strict=True)))
print(list(enumerate("ab")))
print(list(map(str.upper, ["a", "b"])))
print(list(filter(None, [0, 1, "", "x"])))  # drops falsy values
print(any(n > 8 for n in nums), all(n > 1 for n in nums))

# Common mistakes
"""
1. Believing  b = a  copies the list; it only adds another name. Use a.copy().
2. result = my_list.sort()  gives None; sort() returns nothing. Use sorted() if you want a value.
3. [[0] * 3] * 2  repeats the SAME inner list. Use a comprehension.
4. Removing items while iterating over the list; iterate over a copy or build a new list.
5. IndexError from  items[len(items)]; the last valid index is len(items) - 1 (or -1).
6. Using a mutable list as a default argument (see the functions lesson).
"""
