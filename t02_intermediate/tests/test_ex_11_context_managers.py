import os
from pathlib import Path

import pytest

from _loader import load

ex = load("t02_intermediate", "ex_11_context_managers")


def test_timer():
    with ex.Timer() as t:
        sum(range(1000))
    assert isinstance(t.elapsed, float) and t.elapsed >= 0
    with pytest.raises(ValueError):
        with ex.Timer():
            raise ValueError("propagates")


class Thing:
    color = "red"


def test_temp_attr_restores_value():
    t = Thing()
    with ex.temp_attr(t, "color", "blue"):
        assert t.color == "blue"
    assert t.color == "red"


def test_temp_attr_restores_on_error_and_removes_new_attr():
    t = Thing()
    with pytest.raises(RuntimeError):
        with ex.temp_attr(t, "color", "green"):
            raise RuntimeError
    assert t.color == "red"
    with ex.temp_attr(t, "extra", 1):
        assert t.extra == 1
    assert not hasattr(t, "extra")


def test_cd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # make sure we restore to a known place
    sub = tmp_path / "sub"
    sub.mkdir()
    start = Path.cwd()
    with ex.cd(sub) as p:
        assert Path.cwd().resolve() == sub.resolve()
        assert p == sub
    assert Path.cwd() == start
    with pytest.raises(RuntimeError):
        with ex.cd(sub):
            raise RuntimeError
    assert Path.cwd() == start
    assert os.getcwd() == str(start)


def test_transaction_commits_on_success():
    store = {"a": 1}
    with ex.Transaction(store) as tx:
        tx["b"] = 2
        assert "b" not in store  # not applied yet
        del tx["a"]
    assert store == {"b": 2}


def test_transaction_discards_on_error():
    store = {"a": 1}
    with pytest.raises(ValueError):
        with ex.Transaction(store) as tx:
            tx["a"] = 99
            raise ValueError("fail")
    assert store == {"a": 1}


def test_ignore_errors():
    with ex.ignore_errors(KeyError, ZeroDivisionError):
        {}["x"]
    with ex.ignore_errors(ZeroDivisionError):
        _ = 1 / 0
    with pytest.raises(ValueError):
        with ex.ignore_errors(KeyError):
            raise ValueError("not ignored")
