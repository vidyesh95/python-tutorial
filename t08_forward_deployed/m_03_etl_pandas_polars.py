# ETL with pandas and Polars
"""
Customer data arrives as CSV exports, JSON dumps and spreadsheets typed by humans. ETL
(extract, transform, load) turns it into something you can trust. The transform step is where
the value, and the bugs, are.

The workflow
1. EXTRACT   read everything as STRINGS first (`infer_schema=False`): type inference on messy
             data silently turns "007" into 7 and "N/A" into errors. Cast deliberately later.
2. CLEAN     strip whitespace, normalize case, parse dates in every format you actually see,
             strip currency symbols/thousands separators, map synonyms ("US", "usa" -> "US").
3. VALIDATE  split rows into `valid` and `rejects` (with a REASON). Never drop rows silently:
             reject reports are how you tell the customer their data has a problem.
4. LOAD      write Parquet (typed, compressed, fast) or upsert into a database.
5. REPORT    a data-quality report: counts, null rates, duplicate keys, rejects by reason.

Polars vs pandas
- Polars: expression API (`pl.col("a").str.strip_chars()`), multi-threaded, strict types, and a
  LAZY API: `df.lazy()...collect()` builds a query plan the optimizer prunes/pushes down
  (use `pl.scan_csv` / `scan_parquet` for files bigger than RAM). Prefer it for new pipelines.
- pandas: ubiquitous; the customer's notebooks and many libraries speak it. Convert at the edge:
  `df.to_pandas()` / `pl.from_pandas(pdf)` (needs pyarrow, installed).
- DuckDB: SQL over DataFrames and Parquet with no server. Great for joins/aggregates and for
  customers who think in SQL: `duckdb.sql("select ... from df").pl()`.

INCREMENTAL LOADS: do not re-import everything nightly. Keep a WATERMARK (max `updated_at` you
loaded), ask for rows with `updated_at > watermark`, UPSERT by primary key, and re-read a small
overlap window because customer clocks and "updated_at" are unreliable. Make loads idempotent:
running the same batch twice must not change the result.

PRIVACY: the raw export may contain PII you do not need. Drop or hash unneeded columns at the
extract step, keep raw files out of the repo and out of logs (print counts, not rows).

Run: uv run python -m t08_forward_deployed.m_03_etl_pandas_polars
"""

import io
import tempfile
from datetime import date
from pathlib import Path

import duckdb
import polars as pl

RAW_CSV = """id,email,amount,order_date,status,country
 1001 ,Ana@Example.com ,"$1,200.50",2026-03-01,Shipped,us
1002,bob@example,15,03/02/2026,SHIPPED,USA
1003,carol@example.com,N/A,2026-03-03,pending,de
1001,ana@example.com,"$1,200.50",2026-03-05,delivered,US
,dave@example.com,40,2026-03-06,pending,DE
1005,erin@example.com,-5,2026-03-07,pending,GB
1006,frank@example.com,99.9,31/31/2026,pending,GB
"""
COUNTRY_MAP = {"USA": "US", "UNITED STATES": "US", "UK": "GB"}


# Example 1: extract as strings
def extract(csv_text: str) -> pl.DataFrame:
    return pl.read_csv(io.StringIO(csv_text), infer_schema=False)  # every column is a string


# Example 2: clean with expressions (lazy: nothing runs until collect())
def clean(df: pl.DataFrame) -> pl.DataFrame:
    amount = pl.col("amount").str.strip_chars().str.replace_all(r"[$,]", "")
    order_date = pl.col("order_date").str.strip_chars()
    return (
        df.lazy()
        .with_columns(
            pl.col("id").str.strip_chars().replace("", None),
            pl.col("email").str.strip_chars().str.to_lowercase(),
            amount.cast(pl.Float64, strict=False).alias("amount"),
            pl.coalesce(  # try each date format we have seen in this customer's data
                order_date.str.to_date("%Y-%m-%d", strict=False),
                order_date.str.to_date("%m/%d/%Y", strict=False),
            ).alias("order_date"),
            pl.col("status").str.strip_chars().str.to_lowercase(),
            pl.col("country").str.strip_chars().str.to_uppercase().replace(COUNTRY_MAP),
        )
        .collect()
    )


# Example 3: validate into (valid, rejects-with-reason); the first failing rule wins
def split_valid(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    reason = (
        pl.when(pl.col("id").is_null())
        .then(pl.lit("missing_id"))
        .when(~pl.col("email").str.contains(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$"))
        .then(pl.lit("bad_email"))
        .when(pl.col("amount").is_null() | (pl.col("amount") < 0))
        .then(pl.lit("bad_amount"))
        .when(pl.col("order_date").is_null())
        .then(pl.lit("bad_date"))
        .otherwise(None)
        .alias("reason")
    )
    tagged = df.with_columns(reason)
    valid = tagged.filter(pl.col("reason").is_null()).drop("reason")
    return valid, tagged.filter(pl.col("reason").is_not_null())


# Example 4: incremental upsert with a watermark
def upsert(existing: pl.DataFrame, incoming: pl.DataFrame, key: str, version: str) -> pl.DataFrame:
    both = pl.concat(
        [
            existing.with_columns(pl.lit(0).alias("_src")),
            incoming.with_columns(pl.lit(1).alias("_src")),
        ]
    )
    return (
        both.sort([key, version, "_src"])  # newest version wins; ties go to the incoming batch
        .unique(subset=[key], keep="last", maintain_order=True)
        .drop("_src")
        .sort(key)
    )


# Example 5: data-quality report
def quality_report(raw: pl.DataFrame, valid: pl.DataFrame, rejects: pl.DataFrame) -> dict:
    return {
        "rows_in": raw.height,
        "rows_valid": valid.height,
        "rows_rejected": rejects.height,
        "rejects_by_reason": dict(rejects["reason"].value_counts().iter_rows()),
        "null_counts": {c: n for c, n in raw.null_count().row(0, named=True).items() if n},
        "duplicate_ids": valid["id"].is_duplicated().sum(),
    }


# Example 6: DuckDB SQL over a Polars frame and over Parquet
def sql_demo(valid: pl.DataFrame) -> None:
    deduped = valid.sort("order_date").unique(subset=["id"], keep="last")
    # duckdb finds the local variable `deduped` by name (a "replacement scan")
    print(
        duckdb.sql(
            "select country, count(*) as orders, round(sum(amount), 2) as revenue "
            "from deduped group by country order by revenue desc"
        ).pl()
    )
    with tempfile.TemporaryDirectory() as tmp:  # cleaned up: no files left behind
        path = Path(tmp) / "orders.parquet"
        deduped.write_parquet(path)
        rows = duckdb.sql(f"select sum(amount) from read_parquet('{path}')").fetchall()
        print("parquet total:", rows[0][0])
        lazy_total = pl.scan_parquet(path).select(pl.col("amount").sum()).collect().item()
        print("same total via lazy scan:", lazy_total)


def run_demo() -> None:
    raw = extract(RAW_CSV)
    cleaned = clean(raw)
    valid, rejects = split_valid(cleaned)
    print(cleaned.select("id", "email", "amount", "order_date", "country"), "\n")
    print("rejects:\n", rejects.select("id", "email", "reason"), "\n")
    print("quality:", quality_report(raw, valid, rejects), "\n")

    batch2 = pl.DataFrame(
        {
            "id": ["1003"],
            "email": ["carol@example.com"],
            "amount": [30.0],
            "order_date": [date(2026, 3, 9)],
            "status": ["shipped"],
            "country": ["DE"],
        }
    )
    merged = upsert(valid, batch2.cast({c: t for c, t in valid.schema.items()}), "id", "order_date")
    print("after incremental load:", merged.height, "rows; ids:", merged["id"].to_list(), "\n")
    sql_demo(merged)

    pdf = merged.to_pandas()  # the pandas edge, for customer notebooks
    print("pandas mean amount:", round(float(pdf["amount"].mean()), 2))


"""
Common mistakes:
- Letting the CSV reader infer types: leading zeros, IDs and "N/A" get mangled.
- `.cast(...)` with strict=True on dirty data (crash) or strict=False without counting the
  nulls it creates (silent data loss). Compare null counts before and after.
- Dropping bad rows instead of routing them to a rejects file with a reason.
- Dedupe without a defined winner ("latest by updated_at, ties to the newest batch").
- Row-by-row Python loops or `apply` on millions of rows; use expressions.
- Parsing dates without knowing the day/month order. 03/02/2026 is ambiguous: ask the customer.
- Building SQL with f-strings from untrusted input; use duckdb parameters (`?`) for values.

Production notes:
- Validate schemas at the boundary (column names, types) and fail fast with a clear message.
- Keep raw -> cleaned -> curated layers; never overwrite raw, so you can replay after a fix.
- Make loads idempotent (upsert by key) and keep a watermark per source.
- Log counts and rejects-by-reason, never row contents. Encrypt data at rest; delete temp files.
- For data bigger than memory use `scan_*` + lazy + `sink_parquet`, or DuckDB on Parquet.
"""

if __name__ == "__main__":
    run_demo()
