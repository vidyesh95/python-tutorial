import pytest

pytest.importorskip("pandas")
import pandas as pd

from _loader import load

ex = load("t06_applied_ml_llm", "ex_02_pandas")

CSV = """order_id,customer_id,order_date,amount
1,10,2026-01-05,100.0
2,11,2026-01-20,50.0
3,10,2026-01-25,
4,10,2026-04-02,300.0
5,12,2026-04-10,
"""

CUSTOMERS = pd.DataFrame({"customer_id": [10, 11], "region": ["EU", "US"]})


def test_load_orders_types():
    df = ex.load_orders(CSV)
    assert len(df) == 5
    assert pd.api.types.is_datetime64_any_dtype(df["order_date"])
    assert pd.api.types.is_float_dtype(df["amount"])
    assert df["amount"].isna().sum() == 2


def test_revenue_by_customer_sorted_and_named():
    df = ex.load_orders(CSV)
    rev = ex.revenue_by_customer(df)
    assert rev.name == "revenue"
    assert rev.index.tolist() == [10, 11, 12]
    assert rev.tolist() == [400.0, 50.0, 0.0]


def test_fill_missing_amounts_uses_customer_median_and_does_not_mutate():
    df = ex.load_orders(CSV)
    out = ex.fill_missing_amounts(df)
    assert df["amount"].isna().sum() == 2  # input untouched
    assert out["amount"].isna().sum() == 0
    assert out.loc[2, "amount"] == 200.0  # median of customer 10's 100 and 300
    assert out.loc[4, "amount"] == 0.0  # customer 12 has no amounts at all
    assert out.loc[0, "amount"] == 100.0


def test_join_customers_left_keeps_all_orders_in_order():
    df = ex.load_orders(CSV)
    out = ex.join_customers(df, CUSTOMERS)
    assert len(out) == len(df)
    assert out["order_id"].tolist() == [1, 2, 3, 4, 5]
    assert out["region"].tolist() == ["EU", "US", "EU", "EU", "unknown"]


def test_monthly_revenue_includes_empty_months():
    df = ex.fill_missing_amounts(ex.load_orders(CSV))
    monthly = ex.monthly_revenue(df)
    assert [d.strftime("%Y-%m-%d") for d in monthly.index] == [
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
    ]
    assert monthly.tolist() == [350.0, 0.0, 0.0, 300.0]
