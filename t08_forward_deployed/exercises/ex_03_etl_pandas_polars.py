"""Exercise 03: a Polars cleaning pipeline, validation, incremental merge, SQL and a DQ report.

Input frames (from `pl.read_csv(..., infer_schema=False)`) have only string columns:
id, email, amount, order_date, status.

Tasks
1. clean_orders: normalize strings, amounts and dates.
2. split_valid: (valid, rejects) with a `reason` column on rejects.
3. merge_incremental: upsert a new batch into existing data by key and version column.
4. revenue_by_status: aggregate with DuckDB SQL.
5. quality_report: counts and null/duplicate stats as a dict.

Run: uv run pytest t08_forward_deployed -k ex_03
"""

import duckdb  # noqa: F401  (used by the solution)
import polars as pl


def clean_orders(df: pl.DataFrame) -> pl.DataFrame:
    """Return a frame with the same columns, in the same order, but cleaned:
    - id, email, status: whitespace stripped; email and status lower-cased; an empty id -> null
    - amount (Float64): strip whitespace, remove "$" and ","; unparseable ("N/A") -> null
    - order_date (Date): strip, then parse "%Y-%m-%d" or else "%m/%d/%Y"; unparseable -> null
    Never raise on dirty values. Row count and order must not change.
    Hint: pl.coalesce([...]) over `.str.to_date(fmt, strict=False)` expressions.
    """
    raise NotImplementedError


def split_valid(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Split a CLEANED frame into (valid, rejects).

    A row is rejected for the FIRST failing rule, in this order:
      "missing_id"  : id is null
      "bad_email"   : email does not look like name@domain.tld (regex r"^[^@\\s]+@[^@\\s]+\\.[a-z]{2,}$")
      "bad_amount"  : amount is null or negative
      "bad_date"    : order_date is null
    `valid` has the original columns; `rejects` has the original columns plus a string
    column `reason`. Preserve row order in both.
    """
    raise NotImplementedError


def merge_incremental(
    existing: pl.DataFrame, incoming: pl.DataFrame, key: str, version: str
) -> pl.DataFrame:
    """Upsert `incoming` into `existing` (same schema) and return a frame sorted by `key`.

    For each key keep the row with the highest `version` value. If versions tie, the row from
    `incoming` wins. Rows that only exist on one side are kept. Running the same merge twice
    must give the same result (idempotent).
    """
    raise NotImplementedError


def revenue_by_status(df: pl.DataFrame) -> pl.DataFrame:
    """Use DuckDB SQL over `df` to return columns [status, orders, revenue] where orders is the
    row count and revenue is sum(amount), ordered by revenue descending, then status ascending.
    Hint: duckdb.sql("select ... from df").pl() sees the local variable `df`.
    """
    raise NotImplementedError


def quality_report(df: pl.DataFrame, key: str) -> dict:
    """Return {"rows": int, "null_counts": {col: n for cols with n > 0},
    "duplicate_keys": number of DISTINCT key values that appear more than once (nulls ignored)}.
    """
    raise NotImplementedError
