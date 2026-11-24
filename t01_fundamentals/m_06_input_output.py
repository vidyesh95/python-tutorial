# Input and Output
"""
print() writes to the screen (standard output) and input() reads a line typed by the user.
Formatting values into text is done with f-strings (best), str.format() or the old % operator.
input() BLOCKS waiting for the user, so this lesson only shows it inside a function that is never called here.
"""

import sys

# print() basics
# Example
print("Hello", "World")  # items separated by a space
print("a", "b", "c", sep="-")  # custom separator
print("no newline", end="")  # custom ending
print(" <- same line")
print("to stderr", file=sys.stderr)  # error stream (not stdout)

# f-strings
"""
Prefix a string with f and put any expression inside {}. Add = for quick debugging: f"{x=}".
"""
# Example
name = "Ada"
age = 36
print(f"{name} is {age} years old")
print(f"Next year: {age + 1}")
print(f"{name.upper()!r}")  # !r uses repr(), !s uses str()
print(f"{age=}")  # age=36

# Format specification: {value:[fill][align][width][,][.precision][type]}
# Example
pi = 3.14159265
print(f"[{pi:.2f}]")  # [3.14]
print(f"[{pi:10.3f}]")  # [     3.142]  width 10
print(f"[{name:>10}]")  # right aligned
print(f"[{name:<10}]")  # left aligned
print(f"[{name:^10}]")  # centred
print(f"[{name:*^11}]")  # centred, padded with *
print(f"[{42:05d}]")  # [00042]
print(f"[{1234567:,}]")  # [1,234,567]
print(f"[{0.85:.0%}]")  # [85%]
print(f"[{255:#x}] [{255:#b}] [{1500000:.2e}]")

# A small aligned table
# Example
items = [("Coffee", 3.5, 2), ("Bagel", 2.25, 1), ("Juice", 4.0, 3)]
print(f"{'Item':<10}{'Price':>8}{'Qty':>5}")
for item, price, qty in items:
    print(f"{item:<10}{price:>8.2f}{qty:>5}")

# Other formatting styles (you will meet them in older code)
# Example
print(f"{name} is {age}")
print("{0} {1} {0}".format("a", "b"))
print("%s is %d years old" % (name, age))  # noqa: UP031

# Multi-line output
# Example
print("line one\nline two")
print("""triple
quoted""")


# Reading input
"""
input(prompt) always returns a str. Convert it yourself with int()/float().
It is wrapped in a function here so that running this file never waits for a keyboard.
"""


def ask_age() -> int:
    """Ask the user for their age (not called in this lesson)."""
    raw = input("How old are you? ")  # blocks until Enter is pressed
    return int(raw)  # raises ValueError for non-numbers


def greet(raw_name: str) -> str:
    """Pure helper that is easy to test: clean input and build the greeting."""
    return f"Hello, {raw_name.strip().title()}!"


# Example
print(greet("  grace hopper "))  # simulating what a user might type

# Reading from sys.stdin without blocking when nothing is piped
# Example
print(sys.stdin.isatty() or "stdin is piped or redirected")

# Common mistakes
"""
1. Forgetting that input() returns a string:  input() + 1  raises TypeError. Use int(input()).
2. Not handling bad input: int("abc") raises ValueError (see the exceptions lesson).
3. Putting quotes of the same type inside an f-string expression on older Pythons; 3.12+ allows it, but
   mixing styles is still confusing - prefer different quote types.
4. Forgetting end="" when you do NOT want a newline; or flush=True when output must appear immediately.
5. Using print() for data you want to return from a function - return it instead.
"""
