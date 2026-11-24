"""Reference solution for exercise 03."""

import duckdb
import polars as pl


def clean_orders(df: pl.DataFrame) -> pl.DataFrame:
    order_date = pl.col("order_date").str.strip_chars()
    return df.with_columns(
        pl.col("id").str.strip_chars().replace("", None),
        pl.col("email").str.strip_chars().str.to_lowercase(),
        pl.col("amount")
        .str.strip_chars()
        .str.replace_all(r"[$,]", "")
        .cast(pl.Float64, strict=False)
        .alias("amount"),
        pl.coalesce(
            order_date.str.to_date("%Y-%m-%d", strict=False),
            order_date.str.to_date("%m/%d/%Y", strict=False),
        ).alias("order_date"),
        pl.col("status").str.strip_chars().str.to_lowercase(),
    )


def split_valid(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    reason = (
        pl.when(pl.col("id").is_null())
        .then(pl.lit("missing_id"))
        .when(~pl.col("email").str.contains(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$").fill_null(False))
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
    rejects = tagged.filter(pl.col("reason").is_not_null())
    return valid, rejects


def merge_incremental(
    existing: pl.DataFrame, incoming: pl.DataFrame, key: str, version: str
) -> pl.DataFrame:
    both = pl.concat(
        [
            existing.with_columns(pl.lit(0).alias("_src")),
            incoming.select(existing.columns).with_columns(pl.lit(1).alias("_src")),
        ]
    )
    return (
        both.sort([key, version, "_src"])
        .unique(subset=[key], keep="last", maintain_order=True)
        .drop("_src")
        .sort(key)
    )


def revenue_by_status(df: pl.DataFrame) -> pl.DataFrame:
    return duckdb.sql(
        "select status, count(*)::BIGINT as orders, sum(amount) as revenue "
        "from df group by status order by revenue desc, status asc"
    ).pl()


def quality_report(df: pl.DataFrame, key: str) -> dict:
    nulls = {c: n for c, n in df.null_count().row(0, named=True).items() if n > 0}
    counts = df.drop_nulls(key).group_by(key).len()
    return {
        "rows": df.height,
        "null_counts": nulls,
        "duplicate_keys": counts.filter(pl.col("len") > 1).height,
    }
