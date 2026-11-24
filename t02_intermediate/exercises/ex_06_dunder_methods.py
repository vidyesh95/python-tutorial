"""Exercise 06: Dunder methods.

Tasks
1. Money.__repr__ / __str__.
2. Money.__eq__ / __hash__ / __lt__ / __add__.
3. Playlist: __len__, __getitem__, __iter__, __add__.
4. Polynomial: __call__ and __bool__.

Run: uv run pytest t02_intermediate -k dunder
"""

from collections.abc import Iterator
from functools import total_ordering


@total_ordering
class Money:
    """An amount in integer cents plus a currency code. Immutable by convention."""

    def __init__(self, cents: int, currency: str = "USD") -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        """Developer view: Money(1050, 'USD')."""
        raise NotImplementedError

    def __str__(self) -> str:
        """User view: 'USD 10.50'."""
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        """Equal when cents and currency match. Return NotImplemented for non-Money."""
        raise NotImplementedError

    def __hash__(self) -> int:
        """Consistent with __eq__ so Money works in sets and as dict keys."""
        raise NotImplementedError

    def __lt__(self, other: Money) -> bool:
        """Compare cents. Raise ValueError if the currencies differ."""
        raise NotImplementedError

    def __add__(self, other: Money) -> Money:
        """Return a new Money with summed cents. Raise ValueError if currencies differ."""
        raise NotImplementedError


class Playlist:
    """A sequence of song titles."""

    def __init__(self, songs: list[str]) -> None:
        raise NotImplementedError

    def __len__(self) -> int:
        """Number of songs."""
        raise NotImplementedError

    def __getitem__(self, index: int | slice) -> str | Playlist:
        """playlist[0] gives a title; playlist[1:3] gives a new Playlist."""
        raise NotImplementedError

    def __iter__(self) -> Iterator[str]:
        """Iterate over the titles."""
        raise NotImplementedError

    def __add__(self, other: Playlist) -> Playlist:
        """Concatenate two playlists into a new one."""
        raise NotImplementedError


class Polynomial:
    """Coefficients are lowest degree first: [1, 2, 3] means 1 + 2x + 3x^2."""

    def __init__(self, coeffs: list[float]) -> None:
        raise NotImplementedError

    def __call__(self, x: float) -> float:
        """Evaluate at x.

        >>> Polynomial([1, 2, 3])(2)
        17
        """
        raise NotImplementedError

    def __bool__(self) -> bool:
        """False for the zero polynomial (empty or all coefficients zero)."""
        raise NotImplementedError
