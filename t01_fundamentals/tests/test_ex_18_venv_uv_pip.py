import sys

import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_18_venv_uv_pip")


def test_python_version_string():
    v = sys.version_info
    assert ex.python_version_string() == f"{v.major}.{v.minor}.{v.micro}"
    assert ex.python_version_string().count(".") == 2


def test_in_virtualenv():
    result = ex.in_virtualenv()
    assert isinstance(result, bool)
    assert result == (sys.prefix != sys.base_prefix)


def test_parse_requirement():
    assert ex.parse_requirement("requests>=2.32") == ("requests", ">=2.32")
    assert ex.parse_requirement("pytest == 8.3.1") == ("pytest", "==8.3.1")
    assert ex.parse_requirement("ruff") == ("ruff", "")
    assert ex.parse_requirement("  my-pkg~=1.0 ") == ("my-pkg", "~=1.0")


def test_read_dependencies():
    text = '[project]\nname = "x"\ndependencies = ["requests>=2", "httpx"]\n'
    assert ex.read_dependencies(text) == ["requests>=2", "httpx"]
    assert ex.read_dependencies('[project]\nname = "x"\n') == []
    assert ex.read_dependencies("") == []


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("pip install requests httpx", "uv add requests httpx"),
        ("pip uninstall requests", "uv remove requests"),
        ("pip install -r requirements.txt", "uv sync"),
        ("python -m venv .venv", "uv venv"),
        ("python app.py", "uv run python app.py"),
    ],
)
def test_pip_to_uv(command, expected):
    assert ex.pip_to_uv(command) == expected


def test_pip_to_uv_unsupported():
    with pytest.raises(ValueError):
        ex.pip_to_uv("npm install left-pad")
