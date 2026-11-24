"""Reference solution for Exercise 02: pandas."""

import io

import pandas as pd


def load_orders(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(
        io.StringIO(csv_text), parse_dates=["order_date"], dtype={"amount": "float64"}
    )


def revenue_by_customer(orders: pd.DataFrame) -> pd.Series:
    return (
        orders.groupby("customer_id")["amount"].sum().sort_values(ascending=False).rename("revenue")
    )


def fill_missing_amounts(orders: pd.DataFrame) -> pd.DataFrame:
    per_customer_median = orders.groupby("customer_id")["amount"].transform("median")
    return orders.assign(amount=orders["amount"].fillna(per_customer_median).fillna(0.0))


def join_customers(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    merged = orders.merge(customers, on="customer_id", how="left")
    merged["region"] = merged["region"].fillna("unknown")
    return merged


def monthly_revenue(orders: pd.DataFrame) -> pd.Series:
    return orders.set_index("order_date")["amount"].resample("MS").sum()
