"""Reference solution for Exercise 04: Pydantic models, validation and response_model."""

from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Exercise 04")

USERS: dict[int, dict] = {}


def normalize_email(value: str) -> str:
    cleaned = value.strip().lower()
    if "@" not in cleaned:
        raise ValueError("email must contain '@'")
    return cleaned


def check_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("password must be at least 8 characters")
    if not any(ch.isdigit() for ch in value):
        raise ValueError("password must contain a digit")
    return value


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


@app.post("/users", status_code=201, response_model=UserPublic)
def create_user(user: UserCreate) -> dict:
    if any(u["email"] == user.email for u in USERS.values()):
        raise HTTPException(status_code=409, detail="Email already registered")
    new_id = max(USERS, default=0) + 1
    record = {
        "id": new_id,
        "email": user.email,
        "name": user.name,
        "age": user.age,
        "password_hash": "hashed:" + user.password,
    }
    USERS[new_id] = record
    return record


@app.get("/users/{user_id}", response_model=UserPublic)
def get_user(user_id: int) -> dict:
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    return USERS[user_id]


@app.patch("/users/{user_id}", response_model=UserPublic)
def update_user(user_id: int, changes: UserUpdate) -> dict:
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    USERS[user_id].update(changes.model_dump(exclude_unset=True))
    return USERS[user_id]
