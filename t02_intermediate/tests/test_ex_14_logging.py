import io
import json
import logging

from _loader import load

ex = load("t02_intermediate", "ex_14_logging")


def test_setup_logger_writes_to_stream():
    stream = io.StringIO()
    logger = ex.setup_logger("t02.setup.a", stream, logging.INFO)
    logger.debug("hidden")
    logger.info("hello")
    logger.error("bad")
    assert stream.getvalue().splitlines() == ["INFO:t02.setup.a:hello", "ERROR:t02.setup.a:bad"]
    assert logger.propagate is False


def test_setup_logger_is_idempotent():
    stream = io.StringIO()
    ex.setup_logger("t02.setup.b", stream)
    logger = ex.setup_logger("t02.setup.b", stream)
    assert len(logger.handlers) == 1
    logger.warning("once")
    assert stream.getvalue().count("once") == 1


def test_run_safely_returns_result():
    assert ex.run_safely(lambda: 42, logging.getLogger("t02.safe")) == 42


def test_run_safely_logs_exception(caplog):
    def boom():
        raise ValueError("kaboom")

    logger = logging.getLogger("t02.safe")
    with caplog.at_level(logging.ERROR, logger="t02.safe"):
        assert ex.run_safely(boom, logger) is None
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None  # traceback attached (logger.exception)
    assert "task failed" in caplog.text


def test_json_formatter():
    direct = json.loads(ex.JsonFormatter().format(_record(logging.INFO)))
    assert direct["level"] == "INFO" and direct["message"] == "msg"
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ex.JsonFormatter())
    logger = logging.getLogger("t02.json")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info("login %s", "ok", extra={"request_id": "r-1"})
    logger.warning("plain")
    first, second = (json.loads(line) for line in stream.getvalue().splitlines())
    assert first == {
        "level": "INFO",
        "logger": "t02.json",
        "message": "login ok",
        "request_id": "r-1",
    }
    assert second == {"level": "WARNING", "logger": "t02.json", "message": "plain"}


def _record(level: int) -> logging.LogRecord:
    return logging.LogRecord("x", level, __file__, 1, "msg", None, None)


def test_count_by_level():
    records = [_record(logging.INFO), _record(logging.ERROR), _record(logging.INFO)]
    assert ex.count_by_level(records) == {"INFO": 2, "ERROR": 1}
    assert ex.count_by_level([]) == {}


def test_max_level_filter():
    f = ex.MaxLevelFilter(logging.INFO)
    assert f.filter(_record(logging.DEBUG))
    assert f.filter(_record(logging.INFO))
    assert not f.filter(_record(logging.WARNING))
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(ex.MaxLevelFilter(logging.INFO))
    logger = logging.getLogger("t02.filter")
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info("kept")
    logger.error("dropped")
    assert stream.getvalue() == "kept\n"
