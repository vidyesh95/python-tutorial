import pytest

from _loader import load

ex = load("t03_advanced", "ex_02_descriptors_metaclasses")


def test_bounded_validates_and_is_per_instance():
    class Dial:
        level = ex.Bounded(0, 10)

    a, b = Dial(), Dial()
    a.level = 3
    b.level = 7
    assert (a.level, b.level) == (3, 7)
    with pytest.raises(ValueError):
        a.level = 11
    with pytest.raises(ValueError):
        a.level = -1
    assert a.level == 3  # failed set keeps old value
    assert isinstance(Dial.level, ex.Bounded)


def test_bounded_edges_inclusive():
    class Dial:
        level = ex.Bounded(0, 10)

    d = Dial()
    d.level = 0
    d.level = 10
    assert d.level == 10


def test_readonly_set_once():
    class Config:
        token = ex.ReadOnly()

        def __init__(self, token):
            self.token = token

    c = Config("abc")
    assert c.token == "abc"
    with pytest.raises(AttributeError):
        c.token = "new"
    assert Config("zzz").token == "zzz"  # other instances unaffected


def test_counted_access():
    class Box:
        item = ex.CountedAccess()

    b = Box()
    b.item = 42
    assert b.item == 42 and b.item == 42
    assert Box.item.reads(b) == 2
    other = Box()
    other.item = 1
    assert Box.item.reads(other) == 0


def test_command_registry():
    class Base(ex.Command):
        pass

    class Run(Base):
        pass

    class Other(ex.Command, name="go"):
        pass

    assert ex.Command.registry["run"] is Run
    assert ex.Command.registry["go"] is Other
    assert ex.Command.registry["base"] is Base


def test_singleton_meta():
    class Settings(metaclass=ex.SingletonMeta):
        def __init__(self):
            self.n = 1

    class Other(metaclass=ex.SingletonMeta):
        pass

    assert Settings() is Settings()
    assert Other() is Other()
    assert Settings() is not Other()
