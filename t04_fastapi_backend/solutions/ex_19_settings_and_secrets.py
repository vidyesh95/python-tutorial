"""Exercise 19: Settings and secrets with pydantic-settings.

Tasks
1. Settings.split_origins: accept a comma-separated string for `cors_origins`.
2. Settings.check_production: reject unsafe production configuration.
3. redacted: a log-safe dict view of the settings (secrets masked).
4. get_settings: a cached factory (one Settings per process).

Env vars use the prefix SHOP_ (SHOP_ENV, SHOP_DEBUG, SHOP_CORS_ORIGINS, ...).
Note: a model validator runs on every Settings(), so do task 2 before the rest.

Run: uv run pytest t04_fastapi_backend -k settings_and_secrets
"""

from functools import lru_cache
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI
from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_KEY = "change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHOP_", env_file=".env", extra="ignore")

    env: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = False
    secret_key: SecretStr = SecretStr(DEFAULT_KEY)
    database_url: SecretStr = SecretStr("sqlite:///./shop.db")
    cors_origins: Annotated[list[str], NoDecode] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: Any) -> Any:
        """A str like "https://a.com, https://b.com," becomes ["https://a.com",
        "https://b.com"] (strip whitespace, drop empty parts). Other values (a list) pass
        through unchanged.
        """
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def check_production(self) -> Settings:
        """When env == "prod": raise ValueError if debug is on, or if the secret key still
        equals DEFAULT_KEY. Return self otherwise (non-prod environments are not checked).
        """
        if self.env == "prod":
            if self.debug:
                raise ValueError("debug must be off in prod")
            if self.secret_key.get_secret_value() == DEFAULT_KEY:
                raise ValueError("SHOP_SECRET_KEY must be set in prod")
        return self


def redacted(settings: Settings) -> dict[str, Any]:
    """Return settings.model_dump() but with every SecretStr value replaced by "***"."""
    return {
        name: "***" if isinstance(value, SecretStr) else value
        for name, value in settings.model_dump().items()
    }


@lru_cache
def get_settings() -> Settings:
    """Build Settings() from the environment. The @lru_cache above makes it a singleton;
    your job is just to return the instance.
    """
    return Settings()


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/info")
    def info(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
        return redacted(settings)

    return app
