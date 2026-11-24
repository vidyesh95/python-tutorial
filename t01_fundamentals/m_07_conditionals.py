# Conditionals
"""
Conditionals let a program choose what to run. Python uses if / elif / else, where the code under each
branch is defined by INDENTATION (4 spaces), and match / case (structural pattern matching, 3.10+).
"""

# if / elif / else
# Example
temperature = 22
if temperature < 0:
    print("freezing")
elif temperature < 15:
    print("cold")
elif temperature < 25:
    print("pleasant")
else:
    print("hot")

# Comparisons can be chained
# Example
x = 7
print(1 < x < 10)  # True, same as 1 < x and x < 10

# Truthiness
"""
Every object has a truth value. These are falsy: False, None, 0, 0.0, "", [], (), {}, set().
Everything else is truthy. So you can write `if items:` instead of `if len(items) > 0:`.
"""
# Example
for value in (0, 1, "", "hi", [], [0], None):
    print(repr(value), "->", bool(value))

shopping: list[str] = []
if not shopping:
    print("nothing to buy")

# and / or / not, and short-circuiting
# Example
age = 20
has_ticket = True
if age >= 18 and has_ticket:
    print("welcome in")
print(None or "default")  # or returns the first truthy operand
print(0 and "never")  # and returns the first falsy operand

# Compare to None with is
# Example
result = None
if result is None:
    print("no result yet")

# Membership in conditions
# Example
vowels = "aeiou"
letter = "e"
if letter in vowels:
    print(letter, "is a vowel")

# Conditional expression (ternary)
# Example
label = "adult" if age >= 18 else "minor"
print(label)

# Nested conditions vs. guard clauses
"""
Deep nesting is hard to read. Handle the bad cases first and return early (a "guard clause").
"""


# Example
def describe_age(age: int) -> str:
    if age < 0:
        return "invalid"
    if age < 13:
        return "child"
    if age < 20:
        return "teen"
    return "adult"


print([describe_age(a) for a in (-1, 5, 15, 40)])

# match / case
"""
match compares a value against patterns top to bottom and runs the first one that fits.
 - literals:         case 200:
 - alternatives:     case 301 | 302:
 - capture variable: case other:
 - wildcard:         case _:
 - sequences:        case [x, y]:
 - dicts:            case {"type": "click"}:
 - guards:           case n if n > 100:
"""


# Example
def http_status(code: int) -> str:
    match code:
        case 200:
            return "OK"
        case 301 | 302:
            return "Redirect"
        case 404:
            return "Not Found"
        case n if 500 <= n < 600:
            return "Server Error"
        case _:
            return "Unknown"


print([http_status(c) for c in (200, 302, 404, 503, 999)])


# Example: matching sequences and dicts
def handle(event: object) -> str:
    match event:
        case {"type": "click", "pos": (x, y)}:
            return f"click at {x},{y}"
        case {"type": "key", "key": key}:
            return f"key {key}"
        case [first, *rest]:
            return f"list starting with {first} (+{len(rest)} more)"
        case str() as text:
            return f"text: {text}"
        case _:
            return "unknown"


print(handle({"type": "click", "pos": (3, 4)}))
print(handle({"type": "key", "key": "q"}))
print(handle([1, 2, 3]))
print(handle("hello"))
print(handle(3.14))

# Common mistakes
"""
1. Using = instead of ==:  if x = 5  is a SyntaxError.
2. Writing  if x == 1 or 2:  - that is always truthy. Write  if x in (1, 2):.
3. Comparing to True/False/None with ==; use  if flag:  or  if value is None:.
4. Wrong indentation, or mixing tabs and spaces.
5. In match, a bare name like  case RED:  CAPTURES a variable instead of comparing to a constant;
   use a dotted name (Color.RED) or a literal for comparisons.
"""
