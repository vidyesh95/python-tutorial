import json

import pytest

pytest.importorskip("mcap")
from mcap.reader import make_reader  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t07_robotics_infra", "ex_07_rosbag_mcap_data")
MS = 1_000_000
SCHEMA = {"type": "object", "properties": {"v": {"type": "number"}}}


def make_file(tmp_path, times_ms, topic="/sensor/a", metadata=None):
    path = tmp_path / "data.mcap"
    records = [(t * MS, {"v": float(t)}) for t in times_ms]
    ex.write_json_mcap(path, topic, records, SCHEMA, metadata)
    return path


def test_write_produces_valid_mcap_with_schema_and_metadata(tmp_path):
    path = make_file(tmp_path, [0, 10, 20], metadata={"robot": "r1"})
    with open(path, "rb") as f:
        reader = make_reader(f)
        summary = reader.get_summary()
        assert summary is not None  # writer was finished
        schemas = list(summary.schemas.values())
        assert [s.encoding for s in schemas] == ["jsonschema"]
        assert json.loads(schemas[0].data) == SCHEMA
        channel = next(iter(summary.channels.values()))
        assert (channel.topic, channel.message_encoding) == ("/sensor/a", "json")
        assert [m.metadata for m in reader.iter_metadata()] == [{"robot": "r1"}]
        messages = [m for _s, _c, m in reader.iter_messages()]
    assert [m.log_time for m in messages] == [0, 10 * MS, 20 * MS]
    assert all(m.publish_time == m.log_time for m in messages)
    assert json.loads(messages[2].data) == {"v": 20.0}


def test_read_window_is_half_open_and_ordered(tmp_path):
    path = make_file(tmp_path, range(0, 100, 10))
    got = ex.read_window(path, "/sensor/a", 20 * MS, 50 * MS)
    assert [t for t, _ in got] == [20 * MS, 30 * MS, 40 * MS]  # end is exclusive
    assert got[0][1] == {"v": 20.0}
    assert ex.read_window(path, "/sensor/a", 200 * MS, 300 * MS) == []
    assert ex.read_window(path, "/other", 0, 10**12) == []


def test_read_window_filters_by_topic(tmp_path):
    a, b = tmp_path / "a.mcap", tmp_path / "b.mcap"
    ex.write_json_mcap(a, "/x", [(5, {"k": 1})], SCHEMA)
    ex.write_json_mcap(b, "/y", [(5, {"k": 2})], SCHEMA)
    assert ex.read_window(a, "/x", 0, 10) == [(5, {"k": 1})]
    assert ex.read_window(a, "/y", 0, 10) == []


def test_summarize_from_summary(tmp_path):
    path = make_file(tmp_path, [5, 15, 25, 35])
    assert ex.summarize(path) == {
        "message_count": 4,
        "start_ns": 5 * MS,
        "end_ns": 35 * MS,
        "topics": {"/sensor/a": 4},
    }


def test_find_gaps(tmp_path):
    path = make_file(tmp_path, [0, 10, 20, 90, 100, 300])
    assert ex.find_gaps(path, "/sensor/a", 50 * MS) == [(20 * MS, 90 * MS), (100 * MS, 300 * MS)]
    assert ex.find_gaps(path, "/sensor/a", 10 * MS) == [(20 * MS, 90 * MS), (100 * MS, 300 * MS)]
    assert ex.find_gaps(path, "/sensor/a", 500 * MS) == []
    assert ex.find_gaps(path, "/missing", 1) == []


def test_find_gaps_threshold_is_strict(tmp_path):
    path = make_file(tmp_path, [0, 10, 20])
    assert ex.find_gaps(path, "/sensor/a", 10 * MS) == []  # equal to threshold is not a gap
