# Exceptions
"""
When something goes wrong at runtime Python raises an exception. If nothing handles it, the program stops
with a traceback. With try / except you can recover or clean up gracefully.

  try:      code that might fail
  except X: runs if an X (or subclass) was raised
  else:     runs if NO exception happened
  finally:  ALWAYS runs (cleanup)
"""

# Catching an exception
# Example
try:
    result = 10 / 0
except ZeroDivisionError:
    print("cannot divide by zero")

# Catching several types and using the exception object
# Example
for raw in ["42", "abc", None]:
    try:
        print("parsed", int(raw))  # type: ignore[arg-type]
    except ValueError as err:
        print("bad value:", err)
    except TypeError as err:
        print("bad type:", err)
    except (KeyError, IndexError):  # one handler for several types
        print("never reached here")


# try / except / else / finally
# Example
def read_number(text: str) -> int | None:
    try:
        value = int(text)
    except ValueError:
        print("  not a number")
        return None
    else:  # only when no exception occurred
        print("  parsed fine")
        return value
    finally:  # always runs, even after return
        print("  done with", repr(text))


print(read_number("7"))
print(read_number("x"))

# Common built-in exceptions
"""
ValueError (right type, wrong value) | TypeError (wrong type) | KeyError | IndexError | AttributeError
ZeroDivisionError | FileNotFoundError | ImportError | NameError | RuntimeError | StopIteration
All inherit from Exception. Catch the most specific one you can.
"""

# Example
for func in (lambda: {}["missing"], lambda: [1][5], lambda: "a" + 1, lambda: None.upper()):
    try:
        func()
    except Exception as err:  # broad catch only for demos / top-level handlers
        print(type(err).__name__, "->", err)


# Raising exceptions
# Example
def set_age(age: int) -> int:
    if age < 0:
        raise ValueError(f"age must be >= 0, got {age}")
    return age


try:
    set_age(-3)
except ValueError as err:
    print("caught:", err)


# Re-raising and chaining
# Example
def parse_port(text: str) -> int:
    try:
        return int(text)
    except ValueError as err:
        raise RuntimeError(f"invalid port {text!r}") from err  # keeps the original as __cause__


try:
    parse_port("http")
except RuntimeError as err:
    print(err, "| caused by:", repr(err.__cause__))

# Custom exceptions
"""
Create your own by subclassing Exception. A shared base class lets callers catch the whole family.
"""


# Example
class BankError(Exception):
    """Base class for all banking errors."""


class InsufficientFunds(BankError):
    def __init__(self, balance: float, needed: float) -> None:
        super().__init__(f"balance {balance} is less than {needed}")
        self.balance = balance
        self.needed = needed


def withdraw(balance: float, amount: float) -> float:
    if amount > balance:
        raise InsufficientFunds(balance, amount)
    return balance - amount


try:
    withdraw(50, 80)
except BankError as err:  # catches InsufficientFunds too
    print("bank error:", err)


# Context managers clean up for you
# Example
class Noisy:
    def __enter__(self) -> "Noisy":
        print("enter")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        print("exit (even on error)")
        return False  # do not swallow the exception


try:
    with Noisy():
        raise ValueError("boom")
except ValueError:
    print("handled after cleanup")

# EAFP: easier to ask forgiveness than permission
# Example
data = {"a": 1}
try:
    value = data["b"]
except KeyError:
    value = 0
print(value)

# Common mistakes
"""
1. A bare  except:  or  except Exception: pass  hides real bugs. Catch specific types and log/handle them.
2. Putting too much code inside try; wrap only the line that can fail.
3. Using exceptions for normal control flow in hot loops (they are slower than an if).
4. Losing the original traceback: use  raise NewError(...) from err  or a plain  raise  to re-raise.
5. Order matters: put specific except clauses BEFORE general ones (subclass before parent).
"""
