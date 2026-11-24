import pytest
from typer.testing import CliRunner

from _loader import load

ex = load("t03_advanced", "ex_08_cli_with_typer")


def invoke(app, *args):
    return CliRunner().invoke(app, list(args))


def test_add():
    app = ex.build_app()
    r = invoke(app, "add", "2", "40")
    assert r.exit_code == 0
    assert r.stdout.strip() == "42"


def test_add_rejects_non_int():
    app = ex.build_app()
    assert invoke(app, "add", "x", "1").exit_code == 2


def test_greet_default_and_options():
    app = ex.build_app()
    assert invoke(app, "greet", "Ada").stdout.strip() == "Hello, Ada!"
    r = invoke(app, "greet", "Ada", "--greeting", "Hi", "--shout")
    assert r.stdout.strip() == "HI, ADA!"


def test_divide_ok_and_error():
    app = ex.build_app()
    assert invoke(app, "divide", "9", "2").stdout.strip() == "4.5"
    r = invoke(app, "divide", "1", "0")
    assert r.exit_code == 1
    assert "division by zero" in r.stderr
    assert "division by zero" not in r.stdout


def test_tags_group_keeps_state_per_app_instance():
    a, b = ex.build_app(), ex.build_app()
    assert invoke(a, "tags", "list").stdout.strip() == "(none)"
    assert invoke(a, "tags", "add", "x").stdout.strip() == "added x"
    invoke(a, "tags", "add", "y")
    assert invoke(a, "tags", "list").stdout.split() == ["x", "y"]
    assert invoke(b, "tags", "list").stdout.strip() == "(none)"


def test_run_cli():
    code, out = ex.run_cli(ex.build_app(), ["add", "1", "2"])
    assert code == 0 and out.strip() == "3"
    code, _ = ex.run_cli(ex.build_app(), ["nope"])
    assert code == 2


def test_parse_kv():
    assert ex.parse_kv(["a=1", "b=x=y"]) == {"a": "1", "b": "x=y"}
    assert ex.parse_kv([]) == {}
    with pytest.raises(ValueError):
        ex.parse_kv(["novalue"])
