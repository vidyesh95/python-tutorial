# Pydantic Models and Validation
"""
Pydantic v2 models are classes whose type hints are enforced at runtime. FastAPI uses them to:
- parse and validate JSON REQUEST bodies,
- filter and serialize RESPONSES (`response_model`),
- generate the OpenAPI schema (so /docs shows exact shapes).

Core tools:
- `BaseModel` + type hints; `Field(...)` adds constraints (min_length, ge, le, pattern...).
- `@field_validator("x")` checks/normalizes one field; `@model_validator(mode="after")`
  checks relationships between fields. Raise `ValueError` -> becomes a 422 detail entry.
- Use SEPARATE models per purpose (the "model family" pattern):
      UserCreate  (input: has a password)   UserUpdate (all fields optional)
      UserPublic  (output: no password)     UserInDB   (internal: has password hash)
  This is how you avoid ever leaking `password_hash` to clients.
- `response_model=UserPublic` (or a `-> UserPublic` return annotation) filters whatever the
  handler returns down to that model's fields.
- `model.model_dump(exclude_unset=True)` gives only the fields the client actually sent
  - the key to correct PATCH handling.
- `ConfigDict(from_attributes=True)` lets a model be built from ORM objects (lesson 07).

Invalid input never reaches your code: FastAPI replies 422 with a list of errors, each with
`loc` (where), `msg` (why) and `type` (machine code).

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_04_pydantic_models_validation.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_04_pydantic_models_validation
"""

from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

app = FastAPI(title="Pydantic Models")


# Example: the model family
class UserBase(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=20, pattern=r"^[a-z0-9_]+$")]
    age: Annotated[int | None, Field(ge=13, le=120)] = None


class UserCreate(UserBase):  # what clients SEND
    password: Annotated[str, Field(min_length=8)]
    password_confirm: str

    @field_validator("username")
    @classmethod
    def no_reserved(cls, v: str) -> str:  # field validator: one field
        if v in {"admin", "root"}:
            raise ValueError("username is reserved")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":  # model validator: across fields
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        return self


class UserPublic(UserBase):  # what clients GET (no password!)
    model_config = ConfigDict(from_attributes=True)
    id: int


class UserUpdate(BaseModel):  # PATCH body: everything optional
    username: str | None = None
    age: int | None = None


DB: dict[int, dict] = {}  # fake storage; holds the secret field too


# Example: response_model strips fields not in UserPublic
@app.post("/users", response_model=UserPublic, status_code=201)
def create_user(user: UserCreate) -> dict:
    new_id = len(DB) + 1
    record = {"id": new_id, **user.model_dump(exclude={"password_confirm"})}
    record["password_hash"] = "hashed:" + record.pop("password")  # never store plain text
    DB[new_id] = record
    return record  # contains password_hash, but the client will not see it


@app.get("/users/{user_id}", response_model=UserPublic)
def get_user(user_id: int) -> dict:
    if user_id not in DB:
        raise HTTPException(404, "User not found")
    return DB[user_id]


# Example: PATCH applies only the fields the client sent
@app.patch("/users/{user_id}", response_model=UserPublic)
def patch_user(user_id: int, changes: UserUpdate) -> dict:
    if user_id not in DB:
        raise HTTPException(404, "User not found")
    DB[user_id].update(changes.model_dump(exclude_unset=True))  # {} fields are skipped
    return DB[user_id]


# Example: using EmailStr needs the optional `email-validator` package (installed with
# fastapi[standard]); shown here for reference:
class Contact(BaseModel):
    email: EmailStr


"""
Common mistakes:
- One model for everything: the response then echoes `password` or internal ids.
- `model_dump()` instead of `model_dump(exclude_unset=True)` in PATCH: unsent fields get
  overwritten with None.
- Mutable defaults: `tags: list[str] = []` is safe in Pydantic (copied per instance), but a
  shared global dict used as a database is not safe across workers.
- Raising HTTPException inside validators: raise `ValueError`; HTTPException belongs in handlers.
- Assuming `int` fields accept only ints: Pydantic coerces "5" -> 5 in lax mode. Use
  `strict=True` (Field or ConfigDict) when you need exact types.

Production notes:
- Validate at the edge, trust inside: after parsing you hold typed data.
- Use `extra="forbid"` in `model_config` for inputs to reject typos like `{"usernmae": ...}`.
- 422 bodies echo the offending input; make sure that never includes secrets in logs.
- Keep response models stable: they are your API contract. Add fields, don't rename them.
- Return type annotations (`-> UserPublic`) work like response_model and also help type checkers.
"""

if __name__ == "__main__":
    client = TestClient(app)
    good = {
        "username": "ada_l",
        "age": 30,
        "password": "s3cretpass",
        "password_confirm": "s3cretpass",
    }
    r = client.post("/users", json=good)
    print(r.status_code, r.json())  # no password / password_hash in the output

    bad = {"username": "AD", "age": 5, "password": "short", "password_confirm": "nope"}
    for err in client.post("/users", json=bad).json()["detail"]:
        print(err["loc"], "->", err["msg"])

    print(
        client.post("/users", json={**good, "password_confirm": "x" * 10}).json()["detail"][0][
            "msg"
        ]
    )
    print(client.post("/users", json={**good, "username": "admin"}).json()["detail"][0]["msg"])
    print(client.patch("/users/1", json={"age": 31}).json())  # username untouched
    print(client.get("/users/9").status_code)
