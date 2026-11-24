# pandas DataFrames
"""
pandas adds labels to NumPy: a `Series` is a labeled 1-D array, a `DataFrame` is a table of
Series (one per column) sharing an index. It is the workhorse for tabular data cleaning
before modeling.

Core ideas:
- IO: `pd.read_csv(io.StringIO(text))` reads from memory; real files/URLs work the same.
  Pass `parse_dates=[...]` and `dtype=...` to avoid slow, wrong type inference.
- SELECT: `df["col"]` (Series), `df[["a", "b"]]` (DataFrame), `.loc[rows, cols]` (labels),
  `.iloc[...]` (positions). Filter with boolean masks: `df[df.amount > 10]`.
- ASSIGN: `df.assign(total=df.price * df.qty)` returns a new frame (chain-friendly).
- GROUPBY: split -> apply -> combine. `df.groupby("k").agg(total=("amount", "sum"))`.
- MERGE: SQL-style joins: `left.merge(right, on="id", how="left")`.
- MISSING DATA: NaN/NA. `isna()`, `fillna()`, `dropna()`. Decide per column, don't blanket-fill.
- TIME SERIES: a DatetimeIndex enables `resample("MS").sum()` (month-start buckets), `.rolling()`.

Run: uv run python -m t06_applied_ml_llm.m_02_pandas
"""

import io

import pandas as pd

ORDERS_CSV = """order_id,customer_id,order_date,amount,status
1,10,2026-01-05,120.0,paid
2,11,2026-01-20,80.5,paid
3,10,2026-02-02,,paid
4,12,2026-02-14,45.0,refunded
5,11,2026-03-01,200.0,paid
6,13,2026-03-09,60.0,paid
"""

CUSTOMERS_CSV = """customer_id,name,region
10,Ada,EU
11,Grace,US
12,Linus,EU
"""


# Example: IO from an in-memory CSV, with explicit types
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    orders = pd.read_csv(io.StringIO(ORDERS_CSV), parse_dates=["order_date"])
    customers = pd.read_csv(io.StringIO(CUSTOMERS_CSV))
    print(orders.dtypes.to_dict())
    return orders, customers


# Example: selecting and filtering
def select_demo(orders: pd.DataFrame) -> None:
    print(orders.loc[orders["status"] == "paid", ["order_id", "amount"]])
    big = orders.query("amount > 100")  # query() reads nicely for simple filters
    print(big["order_id"].tolist())
    print(orders["amount"].describe().round(1).to_dict())


# Example: missing data (the amount of order 3 is NaN)
def missing_demo(orders: pd.DataFrame) -> pd.DataFrame:
    print("NaN per column:", orders.isna().sum().to_dict())
    # Fill with the customer's own median: a domain-aware fill beats a global constant.
    per_customer = orders.groupby("customer_id")["amount"].transform("median")
    return orders.assign(amount=orders["amount"].fillna(per_customer))


# Example: groupby + named aggregation, then merge
def groupby_merge_demo(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    summary = orders.groupby("customer_id").agg(
        total=("amount", "sum"), n_orders=("order_id", "count")
    )
    # how="left" keeps customer 13 even though customers.csv has no row for them
    joined = summary.reset_index().merge(customers, on="customer_id", how="left")
    joined["region"] = joined["region"].fillna("unknown")
    return joined


# Example: time series basics
def time_series_demo(orders: pd.DataFrame) -> pd.Series:
    monthly = orders.set_index("order_date")["amount"].resample("MS").sum()
    print(monthly.round(1).to_dict())
    print(monthly.rolling(2).mean().round(1).tolist())  # 2-month moving average
    return monthly


"""
Common mistakes:
- Chained assignment (`df[df.x > 0]["y"] = 1`): it may write to a temporary copy. Use
  `df.loc[mask, "y"] = 1`.
- Row-by-row `iterrows()`/`apply(axis=1)` loops; use vectorized column ops instead.
- Merging without checking key uniqueness: duplicate keys multiply rows. Use
  `merge(..., validate="many_to_one")` to fail loudly.
- Blindly `fillna(0)`: zero is a value, not "unknown". Keep a missing-indicator column if useful.
- Letting dates stay as strings; sorting and resampling then silently do the wrong thing.
- `how="inner"` merges quietly dropping rows you wanted to keep.

Production notes:
- Memory: `category` dtype for low-cardinality strings, `float32`/`int32` where range allows,
  `usecols=` to read only needed columns, `chunksize=` for files bigger than RAM.
- Prefer Parquet over CSV for storage: typed, compressed, columnar (and faster to read).
- pandas is single-threaded; for >10 GB or heavy groupbys consider Polars/DuckDB (t08).
- Put validation (schema, null rates, row counts) right after loading; fail the pipeline early.
"""

if __name__ == "__main__":
    orders_df, customers_df = load()
    select_demo(orders_df)
    filled = missing_demo(orders_df)
    print(filled["amount"].tolist())
    print(groupby_merge_demo(filled, customers_df))
    time_series_demo(filled)
