"""Exercise 14: Logging.

Tasks
1. setup_logger: configure a logger with a stream handler, once.
2. run_safely: log an exception with traceback instead of crashing.
3. JsonFormatter: structured log lines.
4. count_by_level: summarise captured records.
5. MaxLevelFilter: let only low-severity records through.

Tests use caplog or in-memory streams.

Run: uv run pytest t02_intermediate -k logging
"""

import logging
from collections.abc import Callable
from typing import Any, TextIO


def setup_logger(name: str, stream: TextIO, level: int = logging.INFO) -> logging.Logger:
    """Return logging.getLogger(name) configured to write to `stream`.

    - set the logger level to `level`
    - attach ONE StreamHandler with format '%(levelname)s:%(name)s:%(message)s'
      (calling this function twice must not add a second handler)
    - set propagate = False
    """
    raise NotImplementedError


def run_safely(func: Callable[[], Any], logger: logging.Logger) -> Any | None:
    """Call func(). Return its result. If it raises Exception, log it with
    logger.exception('task failed') and return None.
    """
    raise NotImplementedError


class JsonFormatter(logging.Formatter):
    """Format records as one JSON object per line.

    Keys: 'level', 'logger', 'message' (plus 'request_id' if the record has it via extra=).
    """

    def format(self, record: logging.LogRecord) -> str:
        raise NotImplementedError


def count_by_level(records: list[logging.LogRecord]) -> dict[str, int]:
    """Count records per level name.

    >>> # two INFO records and one ERROR -> {'INFO': 2, 'ERROR': 1}
    """
    raise NotImplementedError


class MaxLevelFilter(logging.Filter):
    """Allow only records whose level is <= max_level (e.g. send INFO to stdout, not ERROR)."""

    def __init__(self, max_level: int) -> None:
        raise NotImplementedError

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True to keep the record."""
        raise NotImplementedError
