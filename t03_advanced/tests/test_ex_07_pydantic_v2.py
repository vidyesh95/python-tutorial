from datetime import date

import pytest
from pydantic import ValidationError

from _loader import load

ex = load("t03_advanced", "ex_07_pydantic_v2")


def test_product_cleans_and_computes_total():
    p = ex.Product(name="  Widget ", price="2.5", quantity="3")
    assert p.name == "Widget"
    assert p.price == 2.5 and p.quantity == 3
    assert p.total == 7.5
    assert p.model_dump()["total"] == 7.5


def test_product_default_quantity():
    assert ex.Product(name="a", price=1).quantity == 1


@pytest.mark.parametrize(
    "data",
    [
        {"name": "ok", "price": 0},
        {"name": "ok", "price": -3},
        {"name": "ok", "price": 1, "quantity": 0},
        {"name": "   ", "price": 1},
    ],
)
def test_product_rejects_invalid(data):
    with pytest.raises(ValidationError):
        ex.Product(**data)


def test_date_range():
    r = ex.DateRange(start="2025-01-01", end="2025-01-03")
    assert r.days == 3
    assert r.model_dump()["days"] == 3
    assert ex.DateRange(start=date(2025, 5, 5), end=date(2025, 5, 5)).days == 1


def test_date_range_rejects_reversed():
    with pytest.raises(ValidationError, match="end must not be before start"):
        ex.DateRange(start="2025-01-03", end="2025-01-01")


def test_parse_int_list():
    assert ex.parse_int_list('["1", 2, 3]') == [1, 2, 3]
    with pytest.raises(ValidationError):
        ex.parse_int_list('["a"]')
    with pytest.raises(ValidationError):
        ex.parse_int_list('{"a": 1}')


def test_error_fields():
    assert ex.error_fields({"name": "ok", "price": 2}) == []
    assert ex.error_fields({"name": "ok", "price": -1, "quantity": 0}) == ["price", "quantity"]
    assert ex.error_fields({"price": 1}) == ["name"]
    assert ex.error_fields({"name": "x", "price": "abc"}) == ["price"]


def test_strict_int():
    assert ex.strict_int(5) == 5
    with pytest.raises(ValidationError):
        ex.strict_int("5")
