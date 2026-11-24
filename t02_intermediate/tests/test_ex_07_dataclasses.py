import dataclasses

import pytest

from _loader import load

ex = load("t02_intermediate", "ex_07_dataclasses")


def test_product_validation_and_defaults():
    p = ex.Product("pen", 2.0)
    assert p.tags == []
    assert ex.Product("a", 1.0).tags is not ex.Product("b", 1.0).tags
    with pytest.raises(ValueError):
        ex.Product("bad", -1.0)
    assert ex.Product("free", 0.0).price == 0.0


def test_product_with_discount_returns_copy():
    p = ex.Product("pen", 10.0, ["office"])
    q = p.with_discount(25)
    assert q.price == 7.5 and p.price == 10.0
    assert q.tags == ["office"] and q.tags is not p.tags
    assert dataclasses.is_dataclass(q)


def test_version_frozen_and_ordered():
    v = ex.Version(1, 2, 3).bump_minor()  # also proves the class works before checking frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.major = 9
    assert ex.Version(1, 2) < ex.Version(1, 10)
    assert sorted([ex.Version(2), ex.Version(1, 5), ex.Version(1, 5, 1)]) == [
        ex.Version(1, 5),
        ex.Version(1, 5, 1),
        ex.Version(2),
    ]
    assert hash(ex.Version(1)) == hash(ex.Version(1))


def test_version_bump_minor():
    assert ex.Version(1, 2, 3).bump_minor() == ex.Version(1, 3, 0)
    v = ex.Version(0, 9, 9)
    assert v.bump_minor() is not v


def test_inventory():
    inv = ex.Inventory()
    inv.add("apple", 2)
    inv.add("apple")
    inv.add("pear", 5)
    assert inv.items == {"apple": 3, "pear": 5}
    assert inv.total() == 8
    assert ex.Inventory().items == {}  # no shared default dict
    with pytest.raises(ValueError):
        inv.add("x", 0)


def test_point3d_slots_and_kw_only():
    p = ex.Point3D(x=3.0, y=4.0)
    assert p.norm() == 5.0
    assert ex.Point3D().norm() == 0.0
    assert not hasattr(p, "__dict__")  # slots=True
    with pytest.raises(TypeError):
        ex.Point3D(1.0, 2.0, 3.0)  # kw_only=True
