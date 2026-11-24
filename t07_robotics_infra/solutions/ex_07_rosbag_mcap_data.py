"""Exercise 07: write and query MCAP files (JSON messages) in a temp directory.

`path` is always a `pathlib.Path` to a `.mcap` file. Times are integer nanoseconds.

Tasks
1. write_json_mcap: write one channel of JSON records with a JSON schema, plus metadata.
2. read_window: time-range query [start_ns, end_ns) for a topic, ordered by log_time.
3. summarize: per-topic counts and overall time span from the SUMMARY (no message scan).
4. find_gaps: detect data dropouts: consecutive messages further apart than a threshold.

Run: uv run pytest t07_robotics_infra -k rosbag_mcap
"""

import json
from pathlib import Path
from typing import Any

from mcap.reader import make_reader
from mcap.writer import Writer


def write_json_mcap(
    path: Path,
    topic: str,
    records: list[tuple[int, dict[str, Any]]],
    schema: dict[str, Any],
    metadata: dict[str, str] | None = None,
) -> None:
    """Create an MCAP file with ONE channel: schema encoding "jsonschema" (name
    "Record", data = JSON-encoded `schema`), message_encoding "json", topic `topic`. Add
    each (log_time_ns, payload) as a message (publish_time = log_time, data = JSON-encoded
    payload). If `metadata` is given, add it as a metadata record named "run". Finish the
    writer so the summary is written.
    """
    with open(path, "wb") as f:
        writer = Writer(f)
        writer.start(profile="", library="t07-exercise")
        schema_id = writer.register_schema(
            name="Record", encoding="jsonschema", data=json.dumps(schema).encode()
        )
        channel_id = writer.register_channel(
            topic=topic, message_encoding="json", schema_id=schema_id
        )
        for log_time, payload in records:
            writer.add_message(
                channel_id,
                log_time=log_time,
                publish_time=log_time,
                data=json.dumps(payload).encode(),
            )
        if metadata:
            writer.add_metadata("run", metadata)
        writer.finish()


def read_window(
    path: Path, topic: str, start_ns: int, end_ns: int
) -> list[tuple[int, dict[str, Any]]]:
    """Return [(log_time, decoded_json)] for messages on `topic` with
    start_ns <= log_time < end_ns, ordered by log_time. Use the reader's
    `iter_messages(topics=..., starting_at=..., ending_before=...)`.
    """
    with open(path, "rb") as f:
        reader = make_reader(f)
        return [
            (message.log_time, json.loads(message.data))
            for _schema, _channel, message in reader.iter_messages(
                topics=[topic], starting_at=start_ns, ending_before=end_ns
            )
        ]


def summarize(path: Path) -> dict[str, Any]:
    """Read ONLY the summary section (`reader.get_summary()`), not the messages. Return
    {"message_count": int, "start_ns": int, "end_ns": int, "topics": {topic: count}}.
    """
    with open(path, "rb") as f:
        summary = make_reader(f).get_summary()
    if summary is None or summary.statistics is None:
        raise ValueError("MCAP file has no summary")
    stats = summary.statistics
    return {
        "message_count": stats.message_count,
        "start_ns": stats.message_start_time,
        "end_ns": stats.message_end_time,
        "topics": {
            summary.channels[cid].topic: count
            for cid, count in stats.channel_message_counts.items()
        },
    }


def find_gaps(path: Path, topic: str, threshold_ns: int) -> list[tuple[int, int]]:
    """Return (previous_log_time, next_log_time) for every pair of consecutive messages on
    `topic` (in time order) whose difference is GREATER than `threshold_ns`.
    """
    with open(path, "rb") as f:
        reader = make_reader(f)
        times = [m.log_time for _s, _c, m in reader.iter_messages(topics=[topic])]
    times.sort()
    return [(a, b) for a, b in zip(times, times[1:], strict=False) if b - a > threshold_ns]
