"""Exercise 07: Pydantic v2.

Tasks
1. Product: validate `name` (strip whitespace, must not be empty after stripping), make
   `price` > 0 and `quantity` >= 1 (default 1), add computed field `total` = price * quantity.
2. DateRange: model validator ensuring end >= start; computed field `days` (inclusive).
3. parse_int_list: parse a JSON string like '["1", 2]' into list[int] with a TypeAdapter.
4. error_fields: which top-level fields of Product fail validation for the given dict?
5. strict_int: validate with strict mode, so "5" is rejected but 5 is accepted.

The model stubs below raise NotImplementedError from inside a validator or property.
Replace those bodies, and add the Field constraints marked TODO (import what you need
from pydantic: Field, TypeAdapter, ConfigDict, ValidationError).

Run: uv run pytest t03_advanced -k pydantic
"""

from datetime import date

from pydantic import (
    BaseModel,
    computed_field,
    field_validator,
    model_validator,
)


class Product(BaseModel):
    name: str
    price: float  # TODO: must be > 0 (use Field)
    quantity: int = 1  # TODO: must be >= 1 (use Field)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Strip whitespace; raise ValueError if the result is empty."""
        raise NotImplementedError

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> float:
        """price * quantity, rounded to 2 decimals."""
        raise NotImplementedError


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def check_order(self) -> "DateRange":
        """Raise ValueError('end must not be before start') when end < start; return self."""
        raise NotImplementedError

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days(self) -> int:
        """Number of days from start to end, inclusive (same day => 1)."""
        raise NotImplementedError


def parse_int_list(raw: str) -> list[int]:
    """Parse a JSON array into list[int] with TypeAdapter.validate_json (lax mode coerces)."""
    raise NotImplementedError


def error_fields(data: dict[str, object]) -> list[str]:
    """Return the sorted, de-duplicated top-level field names that fail validating `Product(**data)`.

    Return [] when the data is valid.
    """
    raise NotImplementedError


def strict_int(value: object) -> int:
    """Validate `value` as an int in STRICT mode. Raise pydantic.ValidationError for "5"."""
    raise NotImplementedError
