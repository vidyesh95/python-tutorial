import pytest

from _loader import load

ex = load("t07_robotics_infra", "ex_06_time_series_storage")

T0 = 1_699_999_800_000  # divisible by 300 and 1000


@pytest.fixture
def conn():
    c = ex.connect()
    yield c
    c.close()


def series(device: str, metric: str, n: int, step: int = 100, start: int = T0):
    return [(device, metric, start + i * step, float(i)) for i in range(n)]


def test_insert_is_idempotent(conn):
    rows = series("r1", "temp_c", 10)
    assert ex.insert_samples(conn, rows) == 10
    assert ex.insert_samples(conn, rows) == 0
    assert ex.insert_samples(conn, rows + [("r1", "temp_c", T0 + 5000, 1.0)]) == 1
    assert conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 11


def test_insert_keeps_existing_value_and_commits(conn):
    ex.insert_samples(conn, [("r1", "t", T0, 1.0)])
    ex.insert_samples(conn, [("r1", "t", T0, 99.0)])
    assert conn.in_transaction is False
    assert conn.execute("SELECT value FROM samples").fetchone()[0] == 1.0


def test_query_range_half_open_and_ordered(conn):
    ex.insert_samples(conn, list(reversed(series("r1", "temp_c", 10))))
    ex.insert_samples(conn, series("r2", "temp_c", 10))
    ex.insert_samples(conn, series("r1", "battery_v", 10))
    got = ex.query_range(conn, "r1", "temp_c", T0 + 200, T0 + 500)
    assert got == [(T0 + 200, 2.0), (T0 + 300, 3.0), (T0 + 400, 4.0)]
    assert ex.query_range(conn, "r1", "temp_c", T0 + 500, T0 + 500) == []
    assert ex.query_range(conn, "nobody", "temp_c", 0, T0 * 2) == []


def test_rollup_buckets(conn):
    rows = [("r1", "t", T0 + i * 100, float(v)) for i, v in enumerate([1, 3, 2, 10, 20, 30])]
    ex.insert_samples(conn, rows)
    got = ex.rollup(conn, "r1", "t", T0, T0 + 600, 300)
    assert [b[:2] for b in got] == [(T0, 3), (T0 + 300, 3)]
    assert got[0][2:] == (pytest.approx(2.0), 1.0, 3.0)
    assert got[1][2:] == (pytest.approx(20.0), 10.0, 30.0)


def test_rollup_respects_window_and_skips_empty_buckets(conn):
    rows = [("r1", "t", T0, 1.0), ("r1", "t", T0 + 2500, 5.0), ("r1", "t", T0 + 9999, 7.0)]
    ex.insert_samples(conn, rows)
    got = ex.rollup(conn, "r1", "t", T0, T0 + 5000, 1000)
    assert [b[0] for b in got] == [T0, T0 + 2000]
    assert ex.rollup(conn, "r2", "t", T0, T0 + 5000, 1000) == []


def test_apply_retention(conn):
    ex.insert_samples(conn, series("r1", "t", 5) + series("r2", "t", 5))
    assert ex.apply_retention(conn, T0 + 200) == 4  # ts T0, T0+100 for both devices
    assert conn.in_transaction is False
    assert [ts for ts, _ in ex.query_range(conn, "r1", "t", 0, T0 * 2)][0] == T0 + 200
    assert ex.apply_retention(conn, T0) == 0


def test_latest_per_device(conn):
    ex.insert_samples(conn, series("r1", "t", 5) + series("r2", "t", 3))
    ex.insert_samples(conn, series("r3", "other", 2))
    got = ex.latest_per_device(conn, "t")
    assert got == {"r1": (T0 + 400, 4.0), "r2": (T0 + 200, 2.0)}
