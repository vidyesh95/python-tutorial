from datetime import date

import pytest

pl = pytest.importorskip("polars")
pytest.importorskip("duckdb")

from _loader import load  # noqa: E402

ex = load("t08_forward_deployed", "ex_03_etl_pandas_polars")

RAW = pl.DataFrame(
    {
        "id": [" 1 ", "2", "", "4", "5", "6"],
        "email": ["Ana@Example.COM ", "bob@example", "c@x.io", "d@x.io", "e@x.io", "f@x.io"],
        "amount": ["$1,200.50", "15", "7", "N/A", "-3", "9.5"],
        "order_date": [
            "2026-03-01",
            "03/02/2026",
            "2026-03-03",
            "2026-03-04",
            "2026-03-05",
            "31/31/2026",
        ],
        "status": [" Shipped", "PENDING", "pending", "pending", "pending", "pending"],
    }
)


def test_clean_orders_normalizes_everything():
    out = ex.clean_orders(RAW)
    assert out.columns == RAW.columns and out.height == RAW.height
    assert out["id"].to_list() == ["1", "2", None, "4", "5", "6"]
    assert out["email"][0] == "ana@example.com"
    assert out["amount"].dtype == pl.Float64
    assert out["amount"].to_list() == [1200.5, 15.0, 7.0, None, -3.0, 9.5]
    assert out["order_date"].dtype == pl.Date
    assert out["order_date"].to_list() == [
        date(2026, 3, 1),
        date(2026, 3, 2),
        date(2026, 3, 3),
        date(2026, 3, 4),
        date(2026, 3, 5),
        None,
    ]
    assert out["status"].to_list()[:2] == ["shipped", "pending"]


def test_split_valid_reasons_in_priority_order():
    cleaned = ex.clean_orders(RAW)
    valid, rejects = ex.split_valid(cleaned)
    assert valid["id"].to_list() == ["1"]
    assert "reason" not in valid.columns
    assert rejects["reason"].to_list() == [
        "bad_email",  # id 2
        "missing_id",  # empty id
        "bad_amount",  # N/A
        "bad_amount",  # negative
        "bad_date",
    ]
    assert rejects.columns == [*cleaned.columns, "reason"]


def _frame(rows):
    return pl.DataFrame(
        rows, schema={"id": pl.String, "amount": pl.Float64, "updated": pl.Date}, orient="row"
    )


def test_merge_incremental_newest_wins_and_idempotent():
    existing = _frame([("a", 1.0, date(2026, 1, 1)), ("b", 2.0, date(2026, 1, 5))])
    incoming = _frame(
        [
            ("b", 20.0, date(2026, 1, 9)),
            ("a", 99.0, date(2025, 12, 1)),
            ("c", 3.0, date(2026, 1, 2)),
        ]
    )
    merged = ex.merge_incremental(existing, incoming, "id", "updated")
    assert merged.rows() == [
        ("a", 1.0, date(2026, 1, 1)),  # older incoming row loses
        ("b", 20.0, date(2026, 1, 9)),
        ("c", 3.0, date(2026, 1, 2)),
    ]
    assert ex.merge_incremental(merged, incoming, "id", "updated").rows() == merged.rows()


def test_merge_incremental_tie_goes_to_incoming():
    existing = _frame([("a", 1.0, date(2026, 1, 1))])
    incoming = _frame([("a", 5.0, date(2026, 1, 1))])
    assert ex.merge_incremental(existing, incoming, "id", "updated")["amount"].to_list() == [5.0]


def test_revenue_by_status_sql():
    df = pl.DataFrame({"status": ["a", "b", "a", "c", "b"], "amount": [10.0, 5.0, 10.0, 25.0, 5.0]})
    out = ex.revenue_by_status(df)
    assert out.columns == ["status", "orders", "revenue"]
    assert out.rows() == [("c", 1, 25.0), ("a", 2, 20.0), ("b", 2, 10.0)]


def test_quality_report():
    df = pl.DataFrame(
        {"id": ["1", "1", "2", None, "3", "3", "3"], "v": [1, None, None, 4, 5, 6, 7]}
    )
    report = ex.quality_report(df, "id")
    assert report == {"rows": 7, "null_counts": {"id": 1, "v": 2}, "duplicate_keys": 2}
