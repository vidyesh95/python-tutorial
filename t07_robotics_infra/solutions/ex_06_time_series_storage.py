"""Exercise 06: time-series storage with sqlite3.

`connect()` and the schema are given (see the lesson). Every function takes an open
`sqlite3.Connection`. Timestamps are integer epoch milliseconds. A sample row is
(device_id, metric, ts_ms, value) stored in the `samples` table.

Tasks
1. insert_samples: batched, idempotent insert; return how many rows were new.
2. query_range: half-open time-range query for one series.
3. rollup: bucketed count/avg/min/max.
4. apply_retention: delete old raw samples.
5. latest_per_device: newest (ts_ms, value) for a metric, per device.

Run: uv run pytest t07_robotics_infra -k time_series
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    device_id TEXT    NOT NULL,
    metric    TEXT    NOT NULL,
    ts_ms     INTEGER NOT NULL,
    value     REAL    NOT NULL,
    PRIMARY KEY (device_id, metric, ts_ms)
) WITHOUT ROWID
"""

Row = tuple[str, str, int, float]
Bucket = tuple[int, int, float, float, float]


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    return conn


def insert_samples(conn: sqlite3.Connection, rows: list[Row]) -> int:
    """Insert `rows` in a single transaction. A row whose (device_id, metric, ts_ms) already
    exists is ignored (no error, existing value kept). Return the number of NEW rows.
    Hint: INSERT OR IGNORE + executemany; conn.total_changes before/after.
    """
    before = conn.total_changes
    with conn:
        conn.executemany("INSERT OR IGNORE INTO samples VALUES (?, ?, ?, ?)", rows)
    return conn.total_changes - before


def query_range(
    conn: sqlite3.Connection, device: str, metric: str, start_ms: int, end_ms: int
) -> list[tuple[int, float]]:
    """Return [(ts_ms, value), ...] for one series with start_ms <= ts_ms < end_ms
    (half-open), ordered by time ascending.
    """
    cur = conn.execute(
        "SELECT ts_ms, value FROM samples"
        " WHERE device_id = ? AND metric = ? AND ts_ms >= ? AND ts_ms < ? ORDER BY ts_ms",
        (device, metric, start_ms, end_ms),
    )
    return cur.fetchall()


def rollup(
    conn: sqlite3.Connection, device: str, metric: str, start_ms: int, end_ms: int, bucket_ms: int
) -> list[Bucket]:
    """Downsample one series over [start_ms, end_ms) into buckets of `bucket_ms`.

    Return [(bucket_start_ms, count, avg, min, max), ...] ordered by bucket. bucket_start is
    ts_ms rounded DOWN to a multiple of bucket_ms (integer division). Empty buckets are
    omitted.
    """
    cur = conn.execute(
        "SELECT (ts_ms / :b) * :b AS bucket, COUNT(*), AVG(value), MIN(value), MAX(value)"
        " FROM samples WHERE device_id = :d AND metric = :m AND ts_ms >= :s AND ts_ms < :e"
        " GROUP BY bucket ORDER BY bucket",
        {"b": bucket_ms, "d": device, "m": metric, "s": start_ms, "e": end_ms},
    )
    return cur.fetchall()


def apply_retention(conn: sqlite3.Connection, cutoff_ms: int) -> int:
    """Delete every sample (all devices and metrics) with ts_ms < cutoff_ms and commit.
    A sample exactly AT the cutoff is kept. Return the number of rows deleted.
    """
    with conn:
        return conn.execute("DELETE FROM samples WHERE ts_ms < ?", (cutoff_ms,)).rowcount


def latest_per_device(conn: sqlite3.Connection, metric: str) -> dict[str, tuple[int, float]]:
    """For `metric`, return {device_id: (ts_ms, value)} of each device's newest sample.
    Devices with no sample for the metric are absent.
    """
    cur = conn.execute(
        "SELECT device_id, MAX(ts_ms), value FROM samples WHERE metric = ? GROUP BY device_id",
        (metric,),
    )
    return {device: (ts, value) for device, ts, value in cur}
