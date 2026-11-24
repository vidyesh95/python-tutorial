# Scope and Closures
"""
Scope decides where a name is visible. Python looks a name up in this order (LEGB):
  L - Local:      inside the current function
  E - Enclosing:  inside any outer (enclosing) functions
  G - Global:     at the top level of the module
  B - Built-in:   names Python provides (len, print, ...)
Assignment inside a function creates a LOCAL variable unless you declare global or nonlocal.
"""

# Local vs global
# Example
language = "Python"  # global


def show() -> None:
    message = "local to show()"  # local
    print(message, "|", language)  # reading a global is fine


show()
# print(message)  # NameError: message only exists inside show()


# Shadowing
# Example
def shadow() -> None:
    language = "Java"  # a NEW local variable; the global is untouched
    print("inside:", language)


shadow()
print("outside:", language)

# The global keyword
"""
To REBIND a module-level variable from inside a function you must declare it global.
Prefer passing values in and returning results; globals make code hard to test.
"""
counter = 0


# Example
def increment() -> None:
    global counter
    counter += 1


increment()
increment()
print("counter =", counter)


# Without global, this would fail:
def broken() -> None:
    # counter += 1  -> UnboundLocalError: Python sees the assignment and treats counter as local
    pass


# Enclosing scope and nonlocal
# Example
def outer() -> int:
    total = 0

    def add(n: int) -> None:
        nonlocal total  # rebind the variable in outer()
        total += n

    add(5)
    add(10)
    return total


print(outer())

# Closures
"""
A closure is an inner function that REMEMBERS variables from the enclosing function, even after the
enclosing function has finished. It is how you build function factories.
"""


# Example
def make_multiplier(factor: int):
    def multiply(x: int) -> int:
        return x * factor  # factor is remembered

    return multiply


double = make_multiplier(2)
triple = make_multiplier(3)
print(double(10), triple(10))
print(double.__closure__[0].cell_contents)  # peek at the captured value


# A closure with state
# Example
def make_counter(start: int = 0):
    count = start

    def next_value() -> int:
        nonlocal count
        count += 1
        return count

    return next_value


c1 = make_counter()
c2 = make_counter(100)
print(c1(), c1(), c2())

# Loop variables and late binding
"""
A closure looks the variable up when it is CALLED, not when it was created. All lambdas below see the final i.
Bind the current value with a default argument (i=i) to freeze it.
"""
# Example
late = [lambda: i for i in range(3)]  # noqa: B023
print([f() for f in late])  # [2, 2, 2]
frozen = [lambda i=i: i for i in range(3)]
print([f() for f in frozen])  # [0, 1, 2]

# Comprehension and loop variables
# Example
for idx in range(3):  # noqa: B007
    pass
print(idx)  # loop variables leak out of for loops (2) ...
squares = [n * n for n in range(3)]
# print(n)  # ... but not out of comprehensions (NameError)

# Built-in scope
# Example
print(len("abc"))  # noqa: F821
len = 5  # shadows the built-in in this module - never do this!
print(len)
del len  # removes our shadow; the built-in is visible again
print(len("abc"))  # noqa: F821
print(globals().keys() >= {"language", "counter"}, locals() is globals())

# Common mistakes
"""
1. UnboundLocalError: assigning to a name inside a function makes it local for the WHOLE function.
2. Overusing global; pass arguments and return values instead.
3. Shadowing built-ins (list, dict, str, id, sum, max ...) with your own variable names.
4. Late binding surprise: closures created in a loop all share the loop variable.
5. Forgetting nonlocal when an inner function should update an outer variable.
"""
