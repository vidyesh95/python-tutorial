# Pydantic v2
"""
Pydantic turns type hints into RUNTIME validation. You declare a model; it parses and
validates untrusted input (JSON, dicts, env vars) into typed objects, or raises a
ValidationError that lists every problem.

Key pieces (v2 names):
- BaseModel: the base class. `Model(**data)` or `Model.model_validate(data)`.
- Field(...): constraints (gt, ge, min_length, pattern), defaults, aliases, descriptions.
- @field_validator("name"): validate/transform ONE field. @model_validator: whole model.
- @computed_field: a derived property that is included in the serialized output.
- model_dump() / model_dump_json(): to dict / JSON. model_validate_json(): parse JSON.
- TypeAdapter(T): validate ANY type (list[int], dict[str, Model], unions) without a model.
- Default mode is "lax": "42" becomes 42. Use strict=True or `ConfigDict(strict=True)` to
  forbid coercion.
- pydantic-settings (separate package, `BaseSettings`) loads config from env vars and .env
  files with the same validation. Mentioned only; it is not installed in this track.

Common mistakes:
- Using v1 names (`.dict()`, `.json()`, `@validator`, `class Config`). Use the v2 names.
- Mutable defaults: Pydantic copies them for you, but prefer `Field(default_factory=list)`.
- Forgetting that lax mode coerces: `"true"`, `"1"`, `1.0` all pass for some types.
- Raising anything but ValueError/AssertionError inside validators (they become errors).
- Treating validation as sanitization: a valid string can still be a malicious one.

Where this shows up in backend/ML/robotics work:
- Backend: FastAPI request and response bodies ARE Pydantic models (see t04_fastapi_backend).
- ML/LLM: validating structured LLM output, experiment configs, dataset records.
- Robotics: validating sensor/calibration/config files before a robot trusts them.
"""

from datetime import date
from typing import Annotated, Literal

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


# Example: a basic model with coercion and constraints
class User(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=50)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    age: int = Field(ge=0, le=150)
    tags: list[str] = Field(default_factory=list)


user = User(id="7", name="Ada", email="ada@example.com", age=36)  # type: ignore[arg-type]
print(user)  # "7" was coerced to int 7
print(type(user.id).__name__, user.tags)

# Example: validation errors are structured
try:
    User(id="x", name="", email="nope", age=200)  # type: ignore[arg-type]
except ValidationError as exc:
    print("error count:", exc.error_count())
    for err in exc.errors():
        print(" ", err["loc"], err["type"])


# Example: field validators (transform/validate one field) and model validators (cross-field)
class Booking(BaseModel):
    guest: str
    check_in: date
    check_out: date
    room: Literal["single", "double", "suite"] = "single"

    @field_validator("guest")
    @classmethod
    def normalize_guest(cls, v: str) -> str:
        return v.strip().title()

    @model_validator(mode="after")
    def dates_in_order(self) -> "Booking":
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self

    @computed_field  # included in model_dump(), derived from other fields
    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days


booking = Booking(guest="  grace hopper ", check_in="2025-03-01", check_out="2025-03-04")  # type: ignore[arg-type]
print(booking.guest, booking.nights, booking.check_in)

try:
    Booking(guest="x", check_in="2025-03-04", check_out="2025-03-01")  # type: ignore[arg-type]
except ValidationError as exc:
    print("model validator:", exc.errors()[0]["msg"])

# Example: serialization round trips
as_dict = booking.model_dump()
as_json = booking.model_dump_json()
print(as_dict["nights"], as_dict["check_in"])  # date objects stay dates in python mode
print(as_json)  # JSON mode converts them to ISO strings
print("round trip equal:", Booking.model_validate_json(as_json) == booking)
print("include/mode:", booking.model_dump(mode="json", include={"guest", "room"}))


# Example: nested models and aliases (JSON keys that are not valid Python names)
class Address(BaseModel):
    city: str
    zip_code: str = Field(alias="zipCode")


class Customer(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True)  # frozen => immutable + hashable
    name: str
    address: Address


customer = Customer.model_validate(
    {"name": "Linus", "address": {"city": "Oslo", "zipCode": "0150"}}
)
print(customer.address.zip_code, customer.model_dump(by_alias=True)["address"])
try:
    customer.name = "x"  # type: ignore[misc]
except ValidationError as exc:
    print("frozen:", exc.errors()[0]["type"])

# Example: TypeAdapter validates any type, no model class required
ints = TypeAdapter(list[int])
print(ints.validate_python(["1", 2, "3"]))
PositiveInt = Annotated[int, Field(gt=0)]  # reusable constrained type via Annotated
scores = TypeAdapter(dict[str, PositiveInt])
print(scores.validate_json('{"a": 1, "b": 5}'))
try:
    scores.validate_python({"a": 0})
except ValidationError as exc:
    print("adapter error:", exc.errors()[0]["type"])

# Example: strict mode turns off coercion
try:
    TypeAdapter(int, config=ConfigDict(strict=True)).validate_python("5")
except ValidationError as exc:
    print("strict:", exc.errors()[0]["type"])


# Example: settings-style config (the idea behind pydantic-settings' BaseSettings)
class AppConfig(BaseModel):
    debug: bool = False
    workers: int = Field(default=2, ge=1)
    database_url: str = "sqlite:///dev.db"


env = {"debug": "true", "workers": "4"}  # imagine os.environ filtered by prefix
print(AppConfig(**env))  # type: ignore[arg-type]
print("JSON schema keys:", sorted(AppConfig.model_json_schema()["properties"]))  # used by OpenAPI
