# Loops
"""
Loops repeat code. Python has two:
  for  - iterate over the items of any iterable (list, str, range, dict, file ...)
  while - repeat as long as a condition is true
break leaves a loop, continue skips to the next iteration, and an optional else block runs when the loop
finishes WITHOUT hitting break.
"""

# for loop
# Example
for fruit in ["apple", "banana", "cherry"]:
    print(fruit)

# range(stop), range(start, stop), range(start, stop, step)
# Example
print(list(range(5)))  # [0, 1, 2, 3, 4]
print(list(range(2, 10, 3)))  # [2, 5, 8]
print(list(range(5, 0, -1)))  # [5, 4, 3, 2, 1]
total = 0
for n in range(1, 101):
    total += n
print("sum 1..100 =", total)

# while loop
# Example
count = 3
while count > 0:
    print("countdown", count)
    count -= 1
print("liftoff")

# break and continue
# Example
for n in range(10):
    if n % 2 == 0:
        continue  # skip even numbers
    if n > 7:
        break  # stop completely
    print("odd", n)

# for ... else
"""
The else block runs only if the loop was NOT ended by break. Great for "search" loops.
"""
# Example
for n in range(2, 10):
    if n * n == 49:
        print("found", n)
        break
else:
    print("no number squared equals 49 in 2..9")

# enumerate - index and value together
# Example
for index, name in enumerate(["Ann", "Bob", "Cy"], start=1):
    print(index, name)

# zip - walk several iterables in parallel
# Example
names = ["Ann", "Bob", "Cy"]
scores = [90, 72, 85]
for name, score in zip(names, scores, strict=True):  # strict=True raises if lengths differ
    print(f"{name}: {score}")

# Looping over dicts and strings
# Example
prices = {"tea": 2.5, "coffee": 3.0}
for item, price in prices.items():
    print(item, price)
for ch in "hey":
    print(ch, end=" ")
print()

# Reversed and sorted
# Example
for n in reversed(range(3)):
    print(n, end=" ")
print()
for word in sorted(["pear", "fig", "apple"], key=len):
    print(word, end=" ")
print()

# Nested loops
# Example
for i in range(1, 4):
    print(" ".join(str(i * j) for j in range(1, 4)))

# while True with break
"""
Use `while True` when you do not know in advance how many iterations are needed.
"""
# Example
attempts = 0
while True:
    attempts += 1
    if attempts**2 > 50:
        break
print("first n with n*n > 50:", attempts)

# Comprehensions are loops that build collections
# Example
squares = [n * n for n in range(6) if n % 2 == 0]
print(squares)  # [0, 4, 16]

# Common mistakes
"""
1. Infinite while loops: forgetting to update the variable in the condition.
2. Off-by-one errors: range(1, 5) stops at 4; range(n) gives n items starting at 0.
3. Modifying a list while looping over it; loop over a copy (items[:]) or build a new list.
4. Using range(len(seq)) when you want the items; loop directly or use enumerate().
5. Thinking for/else's else runs when the loop is empty - it runs whenever there was no break.
"""
