# Logging
"""
Use `logging`, not print(), for anything that should live beyond your terminal.
Levels (low to high): DEBUG(10) < INFO(20) < WARNING(30) < ERROR(40) < CRITICAL(50).
A logger only emits records at or above its level.
Pieces:
    Logger     -> what your code calls (logger.info(...)); named hierarchically
    Handler    -> where records go (console, file, network)
    Formatter  -> how records look
Convention: in each module, `logger = logging.getLogger(__name__)`; only the application
entry point configures handlers (logging.basicConfig or dictConfig).
Loggers form a tree: "app.db" propagates to its parent "app" and then to the root.
"""

import io
import json
import logging

# Example: basicConfig in an app's entry point
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    force=True,  # reconfigure even if something configured logging already
)
logger = logging.getLogger(__name__)  # __name__ is "t02_intermediate.m_14_logging" or "__main__"

logger.debug("hidden: below INFO")
logger.info("started")
logger.warning("disk at %d%%", 91)  # lazy %-formatting: only built if the record is emitted

# Example: exceptions with tracebacks
try:
    _ = 1 / 0
except ZeroDivisionError:
    logger.exception("calculation failed")  # ERROR level + traceback

# Example: custom handler and formatter writing to memory (instead of a file)
stream = io.StringIO()
handler = logging.StreamHandler(stream)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))

app_logger = logging.getLogger("app")
app_logger.setLevel(logging.DEBUG)
app_logger.addHandler(handler)
app_logger.propagate = False  # don't also send to the root handler

child = logging.getLogger("app.db")  # child of "app"
child.debug("query took %.1f ms", 12.34)
child.error("connection lost")
for line in stream.getvalue().splitlines():
    print("captured:", line.split(" | ", 1)[1])  # drop the timestamp so output is stable


# Example: structured-ish logging with `extra` and a JSON formatter
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("user_id", "request_id"):  # fields passed via extra=
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, sort_keys=True)


json_stream = io.StringIO()
json_handler = logging.StreamHandler(json_stream)
json_handler.setFormatter(JsonFormatter())
api = logging.getLogger("api")
api.setLevel(logging.INFO)
api.addHandler(json_handler)
api.propagate = False

api.info("login ok", extra={"user_id": 42, "request_id": "abc123"})
print(json_stream.getvalue().strip())

# Example: filtering by level and checking before expensive work
print("debug enabled for app:", app_logger.isEnabledFor(logging.DEBUG))
print("effective level of app.db:", logging.getLevelName(child.getEffectiveLevel()))


# Example: a Filter adds or drops records
class NoSecrets(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "password" not in record.getMessage()


app_logger.addFilter(NoSecrets())
app_logger.info("password=hunter2")  # dropped
print("filtered lines:", len(stream.getvalue().splitlines()))

# Real apps usually add a FileHandler or RotatingFileHandler("app.log", maxBytes=...)

"""
Common mistakes
- Using print() for diagnostics; you lose levels, timestamps and routing.
- f-strings in log calls (logger.info(f"x={x}")) do the work even when the record is dropped.
  Prefer logger.info("x=%s", x).
- Calling basicConfig in library code, or on every import. Only the app configures logging.
- Using logging.info(...) on the root logger everywhere instead of getLogger(__name__).
- Logging secrets, tokens or personal data.
- Forgetting handlers have their own level in addition to the logger's.
"""

"""
Where this shows up in backend/ML work
- Every web service: request logs, error logs and audit trails shipped to a log platform.
- uvicorn/FastAPI use the logging module; JSON logs make them searchable (Datadog, Loki).
- Correlation IDs via `extra` or contextvars trace one request through many services.
- Training jobs log metrics and warnings so long runs can be debugged afterwards.
"""
