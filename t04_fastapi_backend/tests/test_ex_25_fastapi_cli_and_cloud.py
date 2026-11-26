import sys
import textwrap

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_25_fastapi_cli_and_cloud")


# Task 1
def test_cli_defaults():
    assert ex.cli_defaults("dev") == {"host": "127.0.0.1", "port": 8000, "reload": True}
    assert ex.cli_defaults("run") == {"host": "0.0.0.0", "port": 8000, "reload": False}


def test_cli_defaults_rejects_unknown_mode():
    with pytest.raises(ValueError):
        ex.cli_defaults("start")


# Task 2
def test_build_argv_minimal():
    assert ex.build_argv("dev") == ["fastapi", "dev"]
    assert ex.build_argv("run", "main.py") == ["fastapi", "run", "main.py"]


def test_build_argv_options_in_documented_order():
    assert ex.build_argv(
        "run",
        host="0.0.0.0",
        port=80,
        workers=4,
        proxy_headers=True,
        forwarded_allow_ips="10.0.0.1,10.0.0.2",
        entrypoint="backend.main:app",
    ) == [
        "fastapi",
        "run",
        "--entrypoint",
        "backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "80",
        "--workers",
        "4",
        "--proxy-headers",
        "--forwarded-allow-ips",
        "10.0.0.1,10.0.0.2",
    ]


def test_build_argv_proxy_headers_tristate_and_port_zero():
    assert ex.build_argv("dev", proxy_headers=False) == ["fastapi", "dev", "--no-proxy-headers"]
    assert ex.build_argv("dev", proxy_headers=None) == ["fastapi", "dev"]
    assert ex.build_argv("dev", port=0) == ["fastapi", "dev", "--port", "0"]  # 0 is not None


def test_build_argv_errors():
    with pytest.raises(ValueError):
        ex.build_argv("serve")
    with pytest.raises(ValueError):
        ex.build_argv("dev", workers=2)
    with pytest.raises(ValueError):
        ex.build_argv("run", "main.py", entrypoint="main:app")


# Task 3
def test_find_default_path_uses_documented_priority_not_input_order():
    assert ex.find_default_path(["app/main.py", "api.py", "README.md"]) == "api.py"
    assert ex.find_default_path(iter(["app/api.py", "main.py"])) == "main.py"
    assert ex.find_default_path(["app/app.py", "app/api.py"]) == "app/app.py"


def test_find_default_path_none():
    assert ex.find_default_path([]) is None
    assert ex.find_default_path(["server.py", "src/main.py"]) is None


# Task 4
def test_read_entrypoint():
    text = '[project]\nname = "x"\n\n[tool.fastapi]\nentrypoint = "backend.main:app"\n'
    assert ex.read_entrypoint(text) == "backend.main:app"


def test_read_entrypoint_missing_returns_none():
    assert ex.read_entrypoint("") is None
    assert ex.read_entrypoint('[project]\nname = "x"\n') is None
    assert ex.read_entrypoint("[tool.ruff]\nline-length = 100\n") is None
    assert ex.read_entrypoint("[tool.fastapi]\n") is None


def test_read_entrypoint_must_be_a_string():
    with pytest.raises(TypeError):
        ex.read_entrypoint("[tool.fastapi]\nentrypoint = 3\n")


# Task 5
def test_split_entrypoint():
    assert ex.split_entrypoint("main:app") == ("main", "app")
    assert ex.split_entrypoint("backend.sub.main:api") == ("backend.sub.main", "api")


@pytest.mark.parametrize("bad", ["main", "main:", ":app", "", "a:b:c"])
def test_split_entrypoint_rejects_bad_format(bad):
    with pytest.raises(ValueError):
        ex.split_entrypoint(bad)


@pytest.fixture
def demo_package(tmp_path, monkeypatch):
    pkg = tmp_path / "ep_demo_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "web.py").write_text(
        textwrap.dedent(
            """\
            from fastapi import FastAPI

            app = FastAPI(title="demo")


            def make_app():
                return FastAPI()
            """
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    yield "ep_demo_pkg.web"
    for name in [n for n in sys.modules if n.startswith("ep_demo_pkg")]:
        del sys.modules[name]


def test_resolve_entrypoint_returns_the_app_object(demo_package):
    app = ex.resolve_entrypoint(f"{demo_package}:app")
    assert isinstance(app, FastAPI) and app.title == "demo"
    assert ex.resolve_entrypoint(f"{demo_package}:app") is app  # same module, same object


def test_resolve_entrypoint_errors(demo_package):
    with pytest.raises(ValueError):
        ex.resolve_entrypoint("no_colon")
    with pytest.raises(ModuleNotFoundError):
        ex.resolve_entrypoint("ep_missing_module_xyz:app")
    with pytest.raises(AttributeError):
        ex.resolve_entrypoint(f"{demo_package}:nope")
    with pytest.raises(TypeError):  # a factory is not an app: the CLI has no --factory
        ex.resolve_entrypoint(f"{demo_package}:make_app")


def test_resolve_entrypoint_of_the_lesson_module():
    app = ex.resolve_entrypoint("t04_fastapi_backend.m_25_fastapi_cli_and_cloud:app")
    assert isinstance(app, FastAPI)


# Task 6
def test_discovery_source_priority():
    assert ex.discovery_source() == "auto-discovery"
    assert ex.discovery_source(pyproject_entrypoint="a:app") == "entrypoint-pyproject"
    assert ex.discovery_source(entrypoint="b:app", pyproject_entrypoint="a:app") == (
        "entrypoint-option"
    )
    assert ex.discovery_source(path="main.py", pyproject_entrypoint="a:app") == "path-argument"
    assert ex.discovery_source(app="other") == "path-argument"


def test_discovery_source_entrypoint_conflicts_with_path_or_app():
    with pytest.raises(ValueError):
        ex.discovery_source(path="main.py", entrypoint="a:app")
    with pytest.raises(ValueError):
        ex.discovery_source(app="x", entrypoint="a:app")


# Task 7
def test_create_app_routes():
    client = TestClient(ex.create_app("staging"))
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/info").json() == {"env": "staging"}


def test_create_app_default_is_development_with_docs():
    client = TestClient(ex.create_app())
    assert client.get("/info").json() == {"env": "development"}
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_create_app_production_hides_docs():
    client = TestClient(ex.create_app("production"))
    assert client.get("/healthz").status_code == 200
    for url in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(url).status_code == 404


def test_create_app_returns_a_new_app_each_time():
    assert ex.create_app() is not ex.create_app()


def test_app_from_env():
    assert TestClient(ex.app_from_env({})).get("/info").json() == {"env": "development"}
    prod = TestClient(ex.app_from_env({"FASTAPI_ENV": "production", "OTHER": "x"}))
    assert prod.get("/info").json() == {"env": "production"}
    assert prod.get("/docs").status_code == 404
