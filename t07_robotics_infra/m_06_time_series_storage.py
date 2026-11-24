# Time-Series Storage
"""
Telemetry is append-mostly data keyed by time: "device 7, battery_v, 12.4, at 10:00:00.250".
You write it constantly, almost never update it, and read it back as time RANGES, latest
values, or aggregates ("average temperature per minute"). Storage design follows from that.

SCHEMA DESIGN
- NARROW (long) table: one row per (device, metric, ts, value). New metrics need no schema
  change; sparse data is cheap; but every sample repeats the keys, so it is bigger.
- WIDE table: one row per (device, ts) with a column per metric. Compact and fast for
  "give me all metrics at time t", but adding a metric means a migration and missing
  readings become NULLs. Use wide when sensors are sampled together on a fixed schema.
- Timestamps: store INTEGERS (epoch milliseconds or nanoseconds, UTC), never local-time
  strings. Integers sort, compare, bucket (`ts / bucket * bucket`) and index cheaply.
  Convert to datetimes only at the API edge. The sample time is when the SENSOR measured,
  not when the server received it (keep both if you care about lag).
- Primary key (device_id, metric, ts_ms) makes writes idempotent (a retried batch cannot
  duplicate rows) and clusters one series together on disk. In SQLite `WITHOUT ROWID`
  stores the table AS that key's B-tree, so a range scan on one series is a sequential read.

QUERYING
- Time ranges are HALF-OPEN: `ts >= start AND ts < end`. Adjacent windows then never
  double-count the boundary sample.
- Always put the series key first, then time, in the index or you scan the whole table.
  `EXPLAIN QUERY PLAN` tells you whether the index is used (see Example 4).
- ROLLUPS (downsampling): `GROUP BY ts / bucket_ms` with count, avg, min, max. Keep min and
  max, not just avg: a one-second brake spike disappears in a one-minute average.
- RETENTION: raw data is kept for days, rollups for months or years. Delete by time range
  on a schedule (or drop whole partitions, which is much cheaper than row deletes).

WRITING FAST
- Batch: one transaction with `executemany` beats a commit per row by 10-100x.
- Keep the connection pragmas sane: WAL journal (readers do not block the writer) and
  `synchronous=NORMAL` trade a little crash durability for much more throughput.

WHEN SQLITE IS NOT ENOUGH (concepts only, nothing here needs them)
- TimescaleDB: PostgreSQL extension. Hypertables auto-partition by time, native compression,
  continuous aggregates (incremental rollups), retention policies. Full SQL and joins.
- InfluxDB: purpose-built TSDB. Tags (indexed identity) vs fields (values), line protocol,
  Flux/SQL queries, retention policies built in.
- QuestDB: very fast ingest, SQL with `SAMPLE BY 1m` and `LATEST ON` extensions.
- Parquet (+ DuckDB/Polars): columnar FILES on object storage. Cheap, great compression and
  scans, ideal for the analytics/archive tier; not for low-latency single-row writes.
A common shape: hot data in a TSDB/Postgres, cold data as Parquet, raw streams as MCAP (m_07).

Common mistakes
- Local-time or string timestamps (sorting, DST bugs); mixing seconds and milliseconds.
- One commit per sample; no primary key or index, so every query is a full scan.
- Closed-closed ranges that double count boundaries; averaging averages of unequal buckets
  (store sum and count, or the raw count, to re-aggregate correctly).
- Unbounded retention: telemetry fills the disk silently.
- Trusting the device clock: a robot that booted without NTP reports 1970. Validate sample
  timestamps against server time and flag or clamp the outliers.

Production notes
- High-cardinality labels (a new series per request id) blow up TSDB indexes: keep series
  keys to device and metric.
- Late and out-of-order samples are normal over flaky links; idempotent upserts handle them.
- Monitor ingest lag (server time minus sample time) and disk growth per device.
- Back up before changing retention, and test restores.
"""

import random
import sqlite3
import tempfile
from pathlib import Path

NARROW_SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    device_id TEXT    NOT NULL,
    metric    TEXT    NOT NULL,
    ts_ms     INTEGER NOT NULL,   -- epoch milliseconds, UTC
    value     REAL    NOT NULL,
    PRIMARY KEY (device_id, metric, ts_ms)
) WITHOUT ROWID
"""

WIDE_SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    device_id TEXT    NOT NULL,
    ts_ms     INTEGER NOT NULL,
    battery_v REAL,
    temp_c    REAL,
    PRIMARY KEY (device_id, ts_ms)
) WITHOUT ROWID
"""

Row = tuple[str, str, int, float]  # (device_id, metric, ts_ms, value)
Bucket = tuple[int, int, float, float, float]  # (bucket_start_ms, count, avg, min, max)


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")  # no-op for :memory:
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(NARROW_SCHEMA)
    conn.execute(WIDE_SCHEMA)
    return conn


# Example 1: batched, idempotent writes
def insert_samples(conn: sqlite3.Connection, rows: list[Row]) -> int:
    """Insert rows in ONE transaction; duplicates of an existing key are ignored.
    Returns how many rows were actually new."""
    before = conn.total_changes
    with conn:  # commit on success, rollback on error
        conn.executemany("INSERT OR IGNORE INTO samples VALUES (?, ?, ?, ?)", rows)
    return conn.total_changes - before


def make_rows(device: str, metric: str, start_ms: int, n: int, hz: int, seed: int) -> list[Row]:
    rng = random.Random(seed)  # seeded: the lesson output is reproducible
    step = 1000 // hz
    return [
        (device, metric, start_ms + i * step, round(20.0 + rng.gauss(0, 0.5) + i * 0.001, 4))
        for i in range(n)
    ]


# Example 2: half-open time-range query
def query_range(
    conn: sqlite3.Connection, device: str, metric: str, start_ms: int, end_ms: int
) -> list[tuple[int, float]]:
    cur = conn.execute(
        "SELECT ts_ms, value FROM samples"
        " WHERE device_id = ? AND metric = ? AND ts_ms >= ? AND ts_ms < ? ORDER BY ts_ms",
        (device, metric, start_ms, end_ms),
    )
    return cur.fetchall()


# Example 3: rollups and retention
def rollup(
    conn: sqlite3.Connection, device: str, metric: str, start_ms: int, end_ms: int, bucket_ms: int
) -> list[Bucket]:
    cur = conn.execute(
        "SELECT (ts_ms / :b) * :b AS bucket, COUNT(*), AVG(value), MIN(value), MAX(value)"
        " FROM samples WHERE device_id = :d AND metric = :m AND ts_ms >= :s AND ts_ms < :e"
        " GROUP BY bucket ORDER BY bucket",
        {"b": bucket_ms, "d": device, "m": metric, "s": start_ms, "e": end_ms},
    )
    return cur.fetchall()


def apply_retention(conn: sqlite3.Connection, cutoff_ms: int) -> int:
    """Delete raw samples older than the cutoff; return how many were removed."""
    with conn:
        return conn.execute("DELETE FROM samples WHERE ts_ms < ?", (cutoff_ms,)).rowcount


def latest_per_device(conn: sqlite3.Connection, metric: str) -> dict[str, tuple[int, float]]:
    cur = conn.execute(
        "SELECT device_id, MAX(ts_ms), value FROM samples WHERE metric = ? GROUP BY device_id",
        (metric,),
    )  # SQLite returns the row's `value` that belongs to MAX(ts_ms) (bare-column rule)
    return {device: (ts, value) for device, ts, value in cur}


# Example 4: does the query use the index?
def explain(conn: sqlite3.Connection, device: str) -> str:
    plan = conn.execute(
        "EXPLAIN QUERY PLAN SELECT value FROM samples"
        " WHERE device_id = ? AND metric = 'temp_c' AND ts_ms >= 0 AND ts_ms < 10",
        (device,),
    ).fetchall()
    return plan[0][-1]


# Example 5: a wide table, for fixed schemas sampled together
def insert_wide(conn: sqlite3.Connection, rows: list[tuple[str, int, float, float]]) -> None:
    with conn:
        conn.executemany("INSERT OR REPLACE INTO telemetry VALUES (?, ?, ?, ?)", rows)


def run_demo() -> None:
    conn = connect()
    t0 = 1_700_000_000_000  # an arbitrary epoch-ms start
    rows = make_rows("r1", "temp_c", t0, n=600, hz=10, seed=7)  # 60 s at 10 Hz
    rows += make_rows("r2", "temp_c", t0, n=300, hz=10, seed=8)
    print("inserted:", insert_samples(conn, rows))
    print("re-insert same batch (idempotent):", insert_samples(conn, rows))

    window = query_range(conn, "r1", "temp_c", t0, t0 + 500)
    print("first half second:", len(window), "samples")
    print("half-open boundary:", len(query_range(conn, "r1", "temp_c", t0, t0 + 100)), "(expect 1)")

    for start, count, avg, low, high in rollup(conn, "r1", "temp_c", t0, t0 + 60_000, 20_000):
        print(f"bucket +{(start - t0) // 1000:>2}s n={count} avg={avg:.2f} min={low} max={high}")

    print("latest:", latest_per_device(conn, "temp_c")["r2"][0] - t0, "ms after start for r2")
    print("plan:", explain(conn, "r1"))
    print("retention removed:", apply_retention(conn, t0 + 30_000), "rows")

    insert_wide(conn, [("r1", t0, 12.4, 31.0), ("r1", t0 + 1000, 12.3, 31.2)])
    print("wide rows:", conn.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0])

    with tempfile.TemporaryDirectory() as tmp:  # a file-backed DB, cleaned up afterwards
        path = Path(tmp) / "telemetry.db"
        file_conn = connect(str(path))
        insert_samples(file_conn, rows)
        mode = file_conn.execute("PRAGMA journal_mode").fetchone()[0]
        print("file db journal mode:", mode)
        file_conn.close()


if __name__ == "__main__":
    run_demo()
