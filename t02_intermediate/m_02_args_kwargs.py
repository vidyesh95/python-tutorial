# *args and **kwargs
"""
*args collects extra positional arguments into a tuple.
**kwargs collects extra keyword arguments into a dict.
In a function definition, special markers control how callers may pass arguments:
    def f(a, b, /, c, d, *, e, f): ...
        a, b -> positional-only (before `/`)
        c, d -> positional or keyword
        e, f -> keyword-only (after `*`)
In a call, `*iterable` and `**mapping` UNPACK values into arguments.
"""

from typing import Any


# Example: *args
def total(*numbers: float) -> float:
    return sum(numbers)


print(total(1, 2, 3), total())


# Example: **kwargs
def describe(**fields: Any) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(fields.items()))


print(describe(name="Ada", role="engineer"))


# Example: all together, in the required order
def mix(a: int, b: int = 2, *args: int, flag: bool = False, **kwargs: Any) -> None:
    print(f"a={a} b={b} args={args} flag={flag} kwargs={kwargs}")


mix(1)
mix(1, 5, 7, 8, flag=True, color="red")


# Example: keyword-only arguments force readable call sites
def connect(host: str, *, port: int = 5432, ssl: bool = True) -> str:
    return f"{host}:{port} ssl={ssl}"


print(connect("db.local", port=6543))
# connect("db.local", 6543)  # TypeError: takes 1 positional argument


# Example: positional-only arguments (name is not part of the API)
def clamp(value: float, low: float, high: float, /) -> float:
    return max(low, min(value, high))


print(clamp(15, 0, 10))

# Example: unpacking in calls
point = (3, 4)
options = {"port": 1234, "ssl": False}
print(connect("example.com", **options))
print(max(*point))

# Unpacking when building collections
a, b = [1, 2], [3, 4]
merged = [*a, *b, 5]
defaults = {"retries": 3, "timeout": 5}
config = {**defaults, "timeout": 30}  # later keys win
print(merged, config)

# Example: star-unpacking in assignment
first, *middle, last = [1, 2, 3, 4, 5]
print(first, middle, last)


# Example: forwarding arguments to another function (wrappers use this a lot)
def logged_call(func: Any, /, *args: Any, **kwargs: Any) -> Any:
    print(f"calling {func.__name__} with {args} {kwargs}")
    return func(*args, **kwargs)


print(logged_call(connect, "h", port=1))

"""
Common mistakes
- Mutable default arguments: def f(items=[]) shares one list across calls.
  Use None and create the list inside.
- Passing a keyword-only argument positionally (TypeError).
- Forgetting the unpack star: f(args) passes ONE tuple, f(*args) passes its items.
- Duplicate keys in a call: f(**a, **b) raises TypeError if both have the same key.
- Using **kwargs everywhere and losing self-documenting signatures.
  Prefer explicit parameters; use **kwargs for genuine pass-through.
"""

"""
Where this shows up in backend/ML work
- Decorators and middleware forward (*args, **kwargs) to the wrapped function.
- FastAPI endpoints rely on keyword parameters; keyword-only args make config APIs clear.
- Merging config layers: {**defaults, **env, **cli}.
- Model constructors in ML libs accept **hyperparams that you forward from a config dict.
"""
