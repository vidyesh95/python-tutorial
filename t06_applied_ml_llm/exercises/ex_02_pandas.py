"""Exercise 02: pandas.

Use pandas operations (no Python row loops). Functions must NOT mutate their inputs.

Tasks
1. load_orders(csv_text): parse CSV text (in-memory string) into a DataFrame where the
   `order_date` column is datetime and `amount` is float.
2. revenue_by_customer(orders): Series of total `amount` per `customer_id`, sorted from highest
   to lowest, named "revenue" (NaN amounts are ignored).
3. fill_missing_amounts(orders): return a copy where a missing `amount` is replaced by the
   median amount of that customer's other orders; if the customer has no amounts at all, use 0.0.
4. join_customers(orders, customers): LEFT-merge on `customer_id`, keeping every order (same
   row count and order). Orders whose customer is unknown get region "unknown".
5. monthly_revenue(orders): Series of summed `amount` per calendar month, indexed by the
   month START timestamp, including months with no orders (value 0).

Run: uv run pytest t06_applied_ml_llm -k ex_02
"""

import io  # noqa: F401

import pandas as pd


def load_orders(csv_text: str) -> pd.DataFrame:
    raise NotImplementedError


def revenue_by_customer(orders: pd.DataFrame) -> pd.Series:
    raise NotImplementedError


def fill_missing_amounts(orders: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def join_customers(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def monthly_revenue(orders: pd.DataFrame) -> pd.Series:
    raise NotImplementedError
