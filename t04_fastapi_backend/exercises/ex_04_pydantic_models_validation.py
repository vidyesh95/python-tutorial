"""Exercise 04: Pydantic models, validation and response_model.

The models and routes are wired up. Implement the validators and handlers.

Tasks
1. normalize_email: strip + lowercase; raise ValueError if there is no "@" in the result.
   (It is already hooked up as a field validator on UserCreate.email.)
2. check_password: raise ValueError unless the password has >= 8 chars AND at least one digit;
   return it unchanged otherwise. (Hooked up on UserCreate.password.)
3. create_user: POST /users -> 201. Reject a duplicate email with 409. Store a record
   {"id", "email", "name", "age", "password_hash"} in USERS (password_hash = "hashed:" + pw).
   The response must NOT contain password/password_hash: fix the route's `response_model`.
4. get_user: GET /users/{user_id} -> UserPublic, or 404 {"detail": "User not found"}.
5. update_user: PATCH /users/{user_id}: apply ONLY the fields the client sent
   (`model_dump(exclude_unset=True)`), return UserPublic. 404 if missing.

IDs: use max(existing ids, default=0) + 1.

Run: uv run pytest t04_fastapi_backend -k ex_04
"""

from typing import Annotated

from fastapi import FastAPI, HTTPException  # noqa: F401
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Exercise 04")

USERS: dict[int, dict] = {}


def normalize_email(value: str) -> str:
    raise NotImplementedError


def check_password(value: str) -> str:
    raise NotImplementedError


class UserCreate(BaseModel):
    email: str
    name: Annotated[str, Field(min_length=1, max_length=50)]
    age: Annotated[int | None, Field(ge=0, le=150)] = None
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return check_password(v)


class UserPublic(BaseModel):
    id: int
    email: str
    name: str
    age: int | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    age: int | None = None


@app.post("/users", status_code=201)  # <- task 3: this decorator needs a response_model
def create_user(user: UserCreate) -> dict:
    raise NotImplementedError


@app.get("/users/{user_id}", response_model=UserPublic)
def get_user(user_id: int) -> dict:
    raise NotImplementedError


@app.patch("/users/{user_id}", response_model=UserPublic)
def update_user(user_id: int, changes: UserUpdate) -> dict:
    raise NotImplementedError
