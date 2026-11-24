"""Exercise 07: Pydantic v2.

Tasks
1. Product: validate `name` (strip whitespace, must not be empty after stripping), make
   `price` > 0 and `quantity` >= 1 (default 1), add computed field `total` = price * quantity.
2. DateRange: model validator ensuring end >= start; computed field `days` (inclusive).
3. parse_int_list: parse a JSON string like '["1", 2]' into list[int] with a TypeAdapter.
4. error_fields: which top-level fields of Product fail validation for the given dict?
5. strict_int: validate with strict mode, so "5" is rejected but 5 is accepted.

The model stubs below raise NotImplementedError from inside a validator or property.
Replace those bodies, and add the Field constraints marked TODO.

Run: uv run pytest t03_advanced -k pydantic
"""

from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)


class Product(BaseModel):
    name: str
    price: float = Field(gt=0)
    quantity: int = Field(default=1, ge=1)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Strip whitespace; raise ValueError if the result is empty."""
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> float:
        """price * quantity, rounded to 2 decimals."""
        return round(self.price * self.quantity, 2)


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def check_order(self) -> "DateRange":
        """Raise ValueError('end must not be before start') when end < start; return self."""
        if self.end < self.start:
            raise ValueError("end must not be before start")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days(self) -> int:
        """Number of days from start to end, inclusive (same day => 1)."""
        return (self.end - self.start).days + 1


def parse_int_list(raw: str) -> list[int]:
    """Parse a JSON array into list[int] with TypeAdapter.validate_json (lax mode coerces)."""
    return TypeAdapter(list[int]).validate_json(raw)


def error_fields(data: dict[str, object]) -> list[str]:
    """Return the sorted, de-duplicated top-level field names that fail validating `Product(**data)`.

    Return [] when the data is valid.
    """
    try:
        Product(**data)  # type: ignore[arg-type]
    except ValidationError as exc:
        return sorted({str(err["loc"][0]) for err in exc.errors()})
    return []


def strict_int(value: object) -> int:
    """Validate `value` as an int in STRICT mode. Raise pydantic.ValidationError for "5"."""
    return TypeAdapter(int, config=ConfigDict(strict=True)).validate_python(value)
