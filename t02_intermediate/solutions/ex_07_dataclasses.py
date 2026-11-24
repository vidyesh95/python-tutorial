"""Exercise 07: Dataclasses.

Tasks
1. Product: validation in __post_init__ and a default_factory field.
2. Version: make it frozen and ordered (fix the decorator), then implement bump_minor.
3. Inventory: mutable default via field(default_factory=...).
4. Point3D: slots + keyword-only fields (fix the decorator), implement norm.

Run: uv run pytest t02_intermediate -k dataclasses
"""

from dataclasses import dataclass, field, replace


@dataclass
class Product:
    """A product. price must be >= 0 (ValueError otherwise, raised in __post_init__)."""

    name: str
    price: float
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate: raise ValueError('price must be >= 0') for negative prices."""
        if self.price < 0:
            raise ValueError("price must be >= 0")

    def with_discount(self, percent: float) -> "Product":
        """Return a NEW Product with price reduced by percent (copy tags too).

        >>> Product("pen", 10.0).with_discount(25).price
        7.5
        """
        return Product(self.name, self.price * (1 - percent / 100), list(self.tags))


@dataclass(frozen=True, order=True)
class Version:
    """Semantic version. Must compare by (major, minor, patch) and be immutable."""

    major: int
    minor: int = 0
    patch: int = 0

    def bump_minor(self) -> "Version":
        """Return a new Version with minor + 1 and patch reset to 0 (use dataclasses.replace).

        >>> Version(1, 2, 3).bump_minor()
        Version(major=1, minor=3, patch=0)
        """
        return replace(self, minor=self.minor + 1, patch=0)


@dataclass
class Inventory:
    """Item name -> quantity. Each Inventory needs its own dict."""

    items: dict[str, int] = field(default_factory=dict)

    def add(self, name: str, qty: int = 1) -> None:
        """Increase the quantity of name by qty. Raise ValueError if qty <= 0."""
        if qty <= 0:
            raise ValueError("qty must be positive")
        self.items[name] = self.items.get(name, 0) + qty

    def total(self) -> int:
        """Total number of units across all items."""
        return sum(self.items.values())


@dataclass(slots=True, kw_only=True)
class Point3D:
    """A 3D point. Fields must be keyword-only and the class must use __slots__."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def norm(self) -> float:
        """Euclidean length: sqrt(x^2 + y^2 + z^2)."""
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5
