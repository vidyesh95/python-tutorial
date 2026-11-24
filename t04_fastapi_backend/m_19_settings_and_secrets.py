# Settings and Secrets
"""
The 12-factor rule: configuration lives in the ENVIRONMENT, not in code. pydantic-settings
turns environment variables (and optional `.env` files) into a typed, validated object:

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")
        debug: bool = False
        database_url: SecretStr

    Settings()   # reads APP_DEBUG, APP_DATABASE_URL ... validates and converts types

Precedence (highest wins): arguments to `Settings(...)` > environment variables > `.env`
file > field defaults. A missing required field raises a clear ValidationError AT STARTUP,
which is exactly when you want to find out.

Key features
- `env_prefix`: namespaces your variables (APP_*) so they don't collide with others.
- `SecretStr` / `SecretBytes`: `repr()`/`str()`/logging show `**********`; call
  `.get_secret_value()` only at the moment you hand the value to the client library.
- `.env` for local development ONLY. It is in `.gitignore`; commit a `.env.example` instead.
  Multiple files are allowed: `env_file=(".env", f".env.{env}")` (later files win).
- Per-environment config: choose values by `APP_ENV` (dev/staging/prod) and VALIDATE the
  dangerous combinations (e.g. debug on in prod) with a `model_validator`.
- Lists from env: a comma-separated string needs `NoDecode` + a before-validator, because
  pydantic-settings otherwise tries to parse list fields as JSON.
- Nested: `env_nested_delimiter="__"` maps `APP_DB__POOL_SIZE=5` onto a nested model.
- Inject with `Depends(get_settings)` where `get_settings` is `@lru_cache`d (settings are
  read once), and override it in tests with `app.dependency_overrides`.

Run live:  uv run fastapi dev t04_fastapi_backend/m_19_settings_and_secrets.py
           APP_ENV=staging APP_DEBUG=true uv run fastapi dev t04_fastapi_backend/m_19_settings_and_secrets.py

Common mistakes
- Hard-coding secrets, or committing `.env`. Treat a leaked secret as compromised: rotate it.
- Logging the whole settings object, a DSN with a password, or `settings.model_dump()` of
  secret fields. Log non-secret fields only (see `public_view` below).
- Reading `os.environ` all over the codebase instead of one Settings class.
- Constructing `Settings()` at import time in modules that tests import (hard to override);
  use a cached `get_settings()` dependency instead.
- Bools from env: "false" is a string; let pydantic parse it (`debug: bool`), never `if os.getenv(...)`.
- `Settings` with `extra="forbid"` + a shared `.env` file full of other variables.

Production notes
- In prod, inject secrets from a secret manager (AWS Secrets Manager/SSM, GCP Secret Manager,
  Vault, Kubernetes Secrets) as env vars or mounted files; pydantic-settings can read a
  secrets directory with `secrets_dir=` (one file per field).
- Never bake secrets into images (m_18) and never pass them as build args.
- Rotate secrets regularly; support two valid keys during rotation (e.g. JWT signing keys).
- Fail fast on startup if required config is missing or inconsistent.
"""

import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from unittest import mock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

INSECURE_DEFAULT_KEY = "change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",  # ignored if the file does not exist
        extra="ignore",  # unrelated variables in .env are fine
    )

    env: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = False
    database_url: SecretStr = SecretStr("sqlite:///./dev.db")
    secret_key: SecretStr = SecretStr(INSECURE_DEFAULT_KEY)
    cors_origins: Annotated[list[str], NoDecode] = []  # APP_CORS_ORIGINS=a.com,b.com
    redis_url: str = "redis://localhost:6379/0"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def check_production(self) -> Settings:
        if self.env == "prod":
            if self.debug:
                raise ValueError("debug must be off in prod")
            if self.secret_key.get_secret_value() == INSECURE_DEFAULT_KEY:
                raise ValueError("APP_SECRET_KEY must be set in prod")
        return self


def public_view(settings: Settings) -> dict[str, Any]:
    """Safe-to-log dict: secrets are masked, never revealed."""
    return {
        name: ("***" if isinstance(value, SecretStr) else value)
        for name, value in settings.model_dump().items()
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


app = FastAPI(title="Settings demo")


@app.get("/info")
def info(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    return public_view(settings)


def env_vars(**values: str) -> Any:
    """Demo helper: temporarily replace the process environment."""
    return mock.patch.dict(os.environ, values, clear=True)


if __name__ == "__main__":
    # 1. Defaults only (no .env file read: _env_file=None)
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    print("defaults:", public_view(s))
    print(
        "repr hides secrets:",
        repr(s.secret_key),
        "| real value only on request:",
        s.secret_key.get_secret_value(),
    )

    # 2. Environment variables, with type conversion and a comma-separated list
    with env_vars(
        APP_DEBUG="true", APP_CORS_ORIGINS="https://a.com, https://b.com", APP_ENV="staging"
    ):
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        print("from env:", s.env, s.debug, s.cors_origins)

    # 3. A .env file (temporary directory: nothing is left behind). Real env still wins.
    with tempfile.TemporaryDirectory() as tmp:
        dotenv = Path(tmp) / ".env"
        dotenv.write_text("APP_REDIS_URL=redis://cache:6379/1\nAPP_DEBUG=true\nUNRELATED=1\n")
        with env_vars(APP_DEBUG="false"):
            s = Settings(_env_file=dotenv)  # type: ignore[call-arg]
        print(".env + env:", s.redis_url, "| debug =", s.debug, "(env beat .env)")

    # 4. Per-environment validation fails fast
    with env_vars(APP_ENV="prod", APP_DEBUG="true"):
        try:
            Settings(_env_file=None)  # type: ignore[call-arg]
        except ValidationError as exc:
            print("prod misconfig rejected:", exc.errors()[0]["msg"])

    # 5. Override the dependency in a test/demo instead of touching the environment
    app.dependency_overrides[get_settings] = lambda: Settings(
        env="dev",
        debug=True,
        secret_key=SecretStr("test-key"),
        _env_file=None,  # type: ignore[call-arg]
    )
    print("/info:", TestClient(app).get("/info").json())
    app.dependency_overrides.clear()
