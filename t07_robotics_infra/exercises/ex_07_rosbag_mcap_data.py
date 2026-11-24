"""Exercise 07: write and query MCAP files (JSON messages) in a temp directory.

`path` is always a `pathlib.Path` to a `.mcap` file. Times are integer nanoseconds.

Tasks
1. write_json_mcap: write one channel of JSON records with a JSON schema, plus metadata.
2. read_window: time-range query [start_ns, end_ns) for a topic, ordered by log_time.
3. summarize: per-topic counts and overall time span from the SUMMARY (no message scan).
4. find_gaps: detect data dropouts: consecutive messages further apart than a threshold.

Run: uv run pytest t07_robotics_infra -k rosbag_mcap
"""

from pathlib import Path
from typing import Any


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
    raise NotImplementedError


def read_window(
    path: Path, topic: str, start_ns: int, end_ns: int
) -> list[tuple[int, dict[str, Any]]]:
    """Return [(log_time, decoded_json)] for messages on `topic` with
    start_ns <= log_time < end_ns, ordered by log_time. Use the reader's
    `iter_messages(topics=..., starting_at=..., ending_before=...)`.
    """
    raise NotImplementedError


def summarize(path: Path) -> dict[str, Any]:
    """Read ONLY the summary section (`reader.get_summary()`), not the messages. Return
    {"message_count": int, "start_ns": int, "end_ns": int, "topics": {topic: count}}.
    """
    raise NotImplementedError


def find_gaps(path: Path, topic: str, threshold_ns: int) -> list[tuple[int, int]]:
    """Return (previous_log_time, next_log_time) for every pair of consecutive messages on
    `topic` (in time order) whose difference is GREATER than `threshold_ns`.
    """
    raise NotImplementedError
