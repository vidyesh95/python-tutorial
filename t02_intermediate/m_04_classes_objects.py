# Classes and Objects
"""
A class is a blueprint; an object (instance) is one thing built from it.
- __init__ sets up a new instance. `self` is the instance itself.
- Instance attributes live on each object; class attributes are shared by all.
- Methods are functions defined in the class body.
- @classmethod receives the class (cls): great for alternative constructors.
- @staticmethod receives neither: a plain function namespaced in the class.
- @property turns a method into a computed attribute, with optional validation on set.
Convention: a leading underscore (_balance) means "internal, please don't touch".
"""


# Example: a simple class
class Account:
    bank_name = "PyBank"  # class attribute, shared
    _count = 0

    def __init__(self, owner: str, balance: float = 0.0) -> None:
        self.owner = owner  # instance attributes
        self._balance = balance
        Account._count += 1

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._balance += amount

    # Example: property (read access looks like an attribute)
    @property
    def balance(self) -> float:
        return self._balance

    @property
    def is_empty(self) -> bool:
        return self._balance == 0

    # Example: setter with validation
    @balance.setter
    def balance(self, value: float) -> None:
        if value < 0:
            raise ValueError("balance cannot be negative")
        self._balance = value

    # Example: classmethod as alternative constructor
    @classmethod
    def from_string(cls, text: str) -> Account:
        owner, balance = text.split(":")
        return cls(owner, float(balance))

    # Example: staticmethod: related helper that needs no instance or class
    @staticmethod
    def is_valid_amount(amount: float) -> bool:
        return amount > 0

    @classmethod
    def total_accounts(cls) -> int:
        return cls._count


acct = Account("Ada", 100)
acct.deposit(50)
print(acct.owner, acct.balance, acct.is_empty)

acct.balance = 10  # goes through the setter
print(acct.balance)
try:
    acct.balance = -1
except ValueError as exc:
    print("rejected:", exc)

other = Account.from_string("Grace:250.5")
print(other.owner, other.balance)
print(Account.is_valid_amount(5), Account.total_accounts())

# Class vs instance attributes
print(acct.bank_name, Account.bank_name)
acct.bank_name = "Shadow"  # creates an INSTANCE attribute that shadows the class one
print(acct.bank_name, other.bank_name)

# Introspection
print(vars(other))
print(isinstance(other, Account), type(other).__name__)


# Example: __repr__ makes debugging pleasant (more in the dunder lesson)
class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to(self, other: Point) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


print(Point(0, 0).distance_to(Point(3, 4)), Point(1, 2))

"""
Common mistakes
- Forgetting `self` as the first parameter of an instance method.
- Mutable class attributes (e.g. items = []) are shared between all instances.
  Create mutable state in __init__ instead.
- Assigning to self.x in a class that defines a property x with no setter (AttributeError).
- Calling a method on the class without an instance: Account.deposit(10).
- Overusing classes: a plain function or dict is sometimes enough.
"""

"""
Where this shows up in backend/ML work
- Service classes (UserService, Repository) hold a DB session and expose methods.
- Alternative constructors: Config.from_env(), Model.from_checkpoint(path).
- Properties expose computed fields; ORMs and Pydantic models are classes with attributes.
- ML model wrappers: fit/predict methods over stored state.
"""
