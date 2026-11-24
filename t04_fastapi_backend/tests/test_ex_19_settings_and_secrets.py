import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic_settings")
from fastapi.testclient import TestClient
from pydantic import ValidationError

from _loader import load

ex = load("t04_fastapi_backend", "ex_19_settings_and_secrets")


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """No stray SHOP_* variables and no real .env file (run from an empty directory)."""
    import os

    for name in [k for k in os.environ if k.startswith("SHOP_")]:
        monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    ex.get_settings.cache_clear()
    yield
    ex.get_settings.cache_clear()


def test_defaults():
    s = ex.Settings()
    assert (s.env, s.debug, s.cors_origins) == ("dev", False, [])


def test_env_vars_are_typed(monkeypatch):
    monkeypatch.setenv("SHOP_DEBUG", "true")
    monkeypatch.setenv("SHOP_ENV", "staging")
    s = ex.Settings()
    assert s.debug is True and s.env == "staging"


def test_comma_separated_origins(monkeypatch):
    monkeypatch.setenv("SHOP_CORS_ORIGINS", " https://a.com, https://b.com ,,")
    assert ex.Settings().cors_origins == ["https://a.com", "https://b.com"]


def test_origins_list_passes_through():
    assert ex.Settings(cors_origins=["https://x.io"]).cors_origins == ["https://x.io"]


def test_prod_rejects_debug_and_default_key(monkeypatch):
    monkeypatch.setenv("SHOP_ENV", "prod")
    monkeypatch.setenv("SHOP_SECRET_KEY", "a-real-secret")
    monkeypatch.setenv("SHOP_DEBUG", "true")
    with pytest.raises(ValidationError, match="debug must be off"):
        ex.Settings()

    monkeypatch.setenv("SHOP_DEBUG", "false")
    assert ex.Settings().env == "prod"  # now valid

    monkeypatch.delenv("SHOP_SECRET_KEY")
    with pytest.raises(ValidationError, match="SHOP_SECRET_KEY"):
        ex.Settings()


def test_non_prod_allows_insecure_defaults(monkeypatch):
    monkeypatch.setenv("SHOP_ENV", "staging")
    monkeypatch.setenv("SHOP_DEBUG", "true")
    assert ex.Settings().debug is True


def test_dotenv_file_is_read(tmp_path):
    dotenv = tmp_path / "prod.env"
    dotenv.write_text("SHOP_ENV=staging\nSHOP_CORS_ORIGINS=https://a.com,https://b.com\nOTHER=1\n")
    s = ex.Settings(_env_file=dotenv)
    assert s.env == "staging" and s.cors_origins == ["https://a.com", "https://b.com"]


def test_redacted_masks_secrets_only(monkeypatch):
    monkeypatch.setenv("SHOP_SECRET_KEY", "super-secret")
    monkeypatch.setenv("SHOP_DATABASE_URL", "postgresql://u:pw@db/app")
    view = ex.redacted(ex.Settings())
    assert view["secret_key"] == "***" and view["database_url"] == "***"
    assert view["env"] == "dev"
    assert "super-secret" not in str(view) and "pw@db" not in str(view)


def test_get_settings_is_cached(monkeypatch):
    first = ex.get_settings()
    monkeypatch.setenv("SHOP_ENV", "staging")
    assert ex.get_settings() is first
    assert ex.get_settings().env == "dev"  # cached before the env var changed
    ex.get_settings.cache_clear()
    assert ex.get_settings().env == "staging"


def test_info_endpoint_never_leaks_secret(monkeypatch):
    monkeypatch.setenv("SHOP_SECRET_KEY", "super-secret")
    client = TestClient(ex.create_app())
    body = client.get("/info").json()
    assert body["secret_key"] == "***"
    assert "super-secret" not in client.get("/info").text


def test_dependency_override_replaces_settings():
    app = ex.create_app()
    app.dependency_overrides[ex.get_settings] = lambda: ex.Settings(env="staging", debug=True)
    body = TestClient(app).get("/info").json()
    assert body["env"] == "staging" and body["debug"] is True
