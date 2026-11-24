"""Reference solution for exercise 08."""

import hashlib
import json
import logging
import re
import traceback
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}
_SENSITIVE = re.compile(r"token|secret|password|authorization|api[_-]?key", re.I)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get(),
        }
        for key, value in vars(record).items():
            if key in STANDARD_ATTRS:
                continue
            entry[key] = "[REDACTED]" if _SENSITIVE.search(key) else value
        if record.exc_info:
            entry["exc"] = "".join(traceback.format_exception(*record.exc_info)).strip()
        return json.dumps(entry, default=str)


def group_by_correlation(lines: list[str]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        groups.setdefault(entry.get("correlation_id") or "-", []).append(entry)
    return groups


_FRAME = re.compile(r'^\s*File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>.+?)\s*$')


def last_app_frame(traceback_text: str, app_marker: str) -> tuple[str, int, str] | None:
    lines = traceback_text.splitlines()
    starts = [
        i for i, ln in enumerate(lines) if ln.startswith("Traceback (most recent call last):")
    ]
    block = lines[starts[-1] + 1 :] if starts else lines
    found = None
    for ln in block:
        m = _FRAME.match(ln)
        if m and app_marker in m["file"]:
            found = (m["file"], int(m["line"]), m["func"])
    return found


def first_bad(items: list, is_bad: Callable[[Any], bool]) -> Any | None:
    lo, hi, found = 0, len(items) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if is_bad(items[mid]):
            found, hi = items[mid], mid - 1
        else:
            lo = mid + 1
    return found


def rollout_enabled(flag: str, user_id: str, percent: int) -> bool:
    bucket = int(hashlib.sha256(f"{flag}:{user_id}".encode()).hexdigest(), 16) % 100
    return bucket < percent
