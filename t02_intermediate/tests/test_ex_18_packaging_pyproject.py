import pytest

from _loader import load

ex = load("t02_intermediate", "ex_18_packaging_pyproject")

PYPROJECT = """
[project]
name = "demo"
version = "0.3.1"
dependencies = ["httpx>=0.28", "rich"]

[project.scripts]
demo = "demo.cli:main"
"""


def test_parse_version():
    assert ex.parse_version("1.12.0") == (1, 12, 0)
    assert ex.parse_version(" 0.0.1 ") == (0, 0, 1)
    assert ex.parse_version("0.3.1") < ex.parse_version("0.10.0")  # numeric, not string, compare
    for bad in ("1.2", "1.2.3.4", "a.b.c", "", "1.2.x", "v1.2.3"):
        with pytest.raises(ValueError):
            ex.parse_version(bad)


def test_bump_version():
    assert ex.bump_version("1.2.3", "patch") == "1.2.4"
    assert ex.bump_version("1.2.3", "minor") == "1.3.0"
    assert ex.bump_version("1.2.3", "major") == "2.0.0"
    assert ex.bump_version("0.9.9", "minor") == "0.10.0"
    with pytest.raises(ValueError):
        ex.bump_version("1.2.3", "huge")
    with pytest.raises(ValueError):
        ex.bump_version("bad", "patch")


def test_read_project_metadata():
    meta = ex.read_project_metadata(PYPROJECT)
    assert meta == {
        "name": "demo",
        "version": "0.3.1",
        "dependencies": ["httpx>=0.28", "rich"],
        "scripts": {"demo": "demo.cli:main"},
    }


def test_read_project_metadata_defaults_and_errors():
    meta = ex.read_project_metadata('[project]\nname = "x"\nversion = "1.0.0"\n')
    assert meta["dependencies"] == [] and meta["scripts"] == {}
    with pytest.raises(KeyError):
        ex.read_project_metadata("[tool.ruff]\nline-length = 100\n")
    with pytest.raises(KeyError):
        ex.read_project_metadata('[project]\nname = "x"\n')


def test_parse_entry_point():
    assert ex.parse_entry_point("log_analyzer.cli:main") == ("log_analyzer.cli", "main")
    assert ex.parse_entry_point("pkg:run") == ("pkg", "run")
    for bad in ("nocolon", "a:b:c", ":main", "pkg:", "pkg.cli:1x", ""):
        with pytest.raises(ValueError):
            ex.parse_entry_point(bad)


def test_resolve_entry_point():
    import json
    import os.path

    assert ex.resolve_entry_point("json:dumps") is json.dumps
    assert ex.resolve_entry_point("os.path:join") is os.path.join
    with pytest.raises(ModuleNotFoundError):
        ex.resolve_entry_point("no_such_module_xyz:main")
    with pytest.raises(AttributeError):
        ex.resolve_entry_point("json:no_such_function")
