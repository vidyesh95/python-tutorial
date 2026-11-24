"""Exercise 04: Classes and objects.

Tasks
1. BankAccount.deposit / withdraw with validation.
2. BankAccount.balance: a read-only property (no setter).
3. BankAccount.from_string: classmethod alternative constructor ("ada:100.5").
4. BankAccount.is_valid_amount: staticmethod.
5. Temperature: property with a validating setter and a computed property.

Run: uv run pytest t02_intermediate -k classes
"""


class BankAccount:
    """A simple account. The balance is stored privately and exposed read-only."""

    def __init__(self, owner: str, balance: float = 0.0) -> None:
        raise NotImplementedError

    @property
    def balance(self) -> float:
        """Current balance (read-only: assigning raises AttributeError)."""
        raise NotImplementedError

    def deposit(self, amount: float) -> None:
        """Add amount. Raise ValueError if amount <= 0."""
        raise NotImplementedError

    def withdraw(self, amount: float) -> None:
        """Remove amount. Raise ValueError if amount <= 0 or exceeds the balance."""
        raise NotImplementedError

    @classmethod
    def from_string(cls, text: str) -> "BankAccount":
        """Build from 'owner:balance'.

        >>> BankAccount.from_string("ada:100.5").balance
        100.5
        """
        raise NotImplementedError

    @staticmethod
    def is_valid_amount(amount: float) -> bool:
        """True when amount is greater than zero."""
        raise NotImplementedError


class Temperature:
    """Stores celsius; exposes fahrenheit as a computed property."""

    ABSOLUTE_ZERO_C = -273.15

    def __init__(self, celsius: float) -> None:
        raise NotImplementedError

    @property
    def celsius(self) -> float:
        """Temperature in Celsius."""
        raise NotImplementedError

    @celsius.setter
    def celsius(self, value: float) -> None:
        """Set Celsius. Raise ValueError if below absolute zero (-273.15)."""
        raise NotImplementedError

    @property
    def fahrenheit(self) -> float:
        """Celsius converted to Fahrenheit: c * 9 / 5 + 32.

        >>> Temperature(100).fahrenheit
        212.0
        """
        raise NotImplementedError
