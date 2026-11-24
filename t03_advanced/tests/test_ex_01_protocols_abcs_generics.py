import pytest

from _loader import load

ex = load("t03_advanced", "ex_01_protocols_abcs_generics")


class Good:
    def send(self, message):
        return True


class Bad:
    def send(self, message):
        return False


def test_notify_all_counts_successes():
    assert ex.notify_all([Good(), Bad(), Good()], "hi") == 2
    assert ex.notify_all([], "hi") == 0


def test_notify_all_passes_message():
    seen = []

    class Rec:
        def send(self, message):
            seen.append(message)
            return True

    assert ex.notify_all([Rec()], "hello") == 1
    assert seen == ["hello"]


def test_plugin_is_abstract():
    with pytest.raises(TypeError):
        ex.Plugin()

    class Incomplete(ex.Plugin):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_plugins_work():
    u, r = ex.Upper(), ex.Reverse()
    assert u.run("abc") == "ABC" and r.run("abc") == "cba"
    assert u.describe() == "name: upper" and r.describe() == "name: reverse"
    assert isinstance(u, ex.Plugin)


def test_typed_queue_fifo():
    q = ex.TypedQueue[int]()
    assert len(q) == 0
    q.put(1)
    q.put(2)
    assert len(q) == 2
    assert q.get() == 1 and q.get() == 2
    with pytest.raises(IndexError):
        q.get()


def test_max_by():
    assert ex.max_by(["a", "ccc", "bb"], key=len) == "ccc"
    assert ex.max_by([(1, "x"), (3, "y")], key=lambda t: t[0]) == (3, "y")
    with pytest.raises(ValueError):
        ex.max_by([], key=len)


def test_safe_div():
    ok = ex.safe_div(6, 3)
    assert isinstance(ok, ex.Ok) and ok.value == 2
    err = ex.safe_div(1, 0)
    assert isinstance(err, ex.Err) and err.reason == "division by zero"
