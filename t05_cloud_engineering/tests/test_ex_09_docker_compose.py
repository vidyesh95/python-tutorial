import pytest

from _loader import load

ex = load("t05_cloud_engineering", "ex_09_docker_compose")


def test_parse_env_file():
    text = """
# comment
A=1
export B = two words
C="quoted # not a comment"
D='single'
E=value # inline comment
F=a=b=c
G=
not a pair
"""
    assert ex.parse_env_file(text) == {
        "A": "1",
        "B": "two words",
        "C": "quoted # not a comment",
        "D": "single",
        "E": "value",
        "F": "a=b=c",
        "G": "",
    }


def test_interpolate():
    env = {"HOST": "db", "EMPTY": ""}
    assert ex.interpolate("postgres://${HOST}:5432", env) == "postgres://db:5432"
    assert ex.interpolate("${PORT:-5432}", env) == "5432"
    assert ex.interpolate("${EMPTY:-fallback}", env) == "fallback"
    assert ex.interpolate("${HOST:-x}", env) == "db"
    assert ex.interpolate("a${MISSING}b", env) == "ab"
    assert ex.interpolate("no vars", env) == "no vars"


def test_normalize_env():
    assert ex.normalize_env(None) == {}
    assert ex.normalize_env([]) == {}
    assert ex.normalize_env({"A": 1, "B": None, "C": "x"}) == {"A": "1", "B": "", "C": "x"}
    assert ex.normalize_env(["A=1", "URL=postgres://u:p@h/db?x=y", "FLAG"]) == {
        "A": "1",
        "URL": "postgres://u:p@h/db?x=y",
        "FLAG": "",
    }


def test_startup_order_with_dict_and_list_depends():
    compose = {
        "services": {
            "api": {"depends_on": {"postgres": {"condition": "service_healthy"}, "redis": {}}},
            "worker": {"depends_on": ["redis", "postgres"]},
            "redis": {},
            "postgres": {},
        }
    }
    assert ex.startup_order(compose) == ["postgres", "redis", "api", "worker"]


def test_startup_order_chain():
    compose = {"services": {"c": {"depends_on": ["b"]}, "b": {"depends_on": ["a"]}, "a": {}}}
    assert ex.startup_order(compose) == ["a", "b", "c"]


def test_startup_order_errors():
    with pytest.raises(ValueError):
        ex.startup_order({"services": {"a": {"depends_on": ["ghost"]}}})
    with pytest.raises(ValueError):
        ex.startup_order({"services": {"a": {"depends_on": ["b"]}, "b": {"depends_on": ["a"]}}})


def test_validate_clean_compose():
    compose = {
        "services": {
            "api": {
                "build": {"context": "."},
                "environment": {"DB_PASSWORD": "${DB_PASSWORD}", "LOG": "debug"},
                "depends_on": {"db": {"condition": "service_healthy"}},
            },
            "db": {"image": "postgres:17-alpine", "healthcheck": {"test": ["CMD", "true"]}},
        }
    }
    assert ex.validate_compose(compose) == []


def test_validate_reports_every_issue():
    compose = {
        "services": {
            "api": {
                "image": "myapp",
                "depends_on": {"db": {"condition": "service_healthy"}, "ghost": {}},
            },
            "db": {
                "image": "postgres:latest",
                "environment": ["POSTGRES_PASSWORD=hunter2", "TZ=UTC"],
            },
            "cache": {"image": "redis@sha256:abc", "environment": {"API_KEY": "abc"}},
        }
    }
    assert ex.validate_compose(compose) == [
        "inline-secret:cache:API_KEY",
        "inline-secret:db:POSTGRES_PASSWORD",
        "latest-tag:api",
        "latest-tag:db",
        "missing-healthcheck:db",
        "unknown-dependency:api:ghost",
    ]


def test_validate_registry_port_image_is_not_untagged():
    compose = {"services": {"a": {"image": "registry.local:5000/app:1.2"}}}
    assert ex.validate_compose(compose) == []
    compose = {"services": {"a": {"image": "registry.local:5000/app"}}}
    assert ex.validate_compose(compose) == ["latest-tag:a"]
