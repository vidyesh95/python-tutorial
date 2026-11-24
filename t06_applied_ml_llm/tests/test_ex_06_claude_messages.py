import pytest

pytest.importorskip("anthropic")
import anthropic

try:  # anthropic 1.x+ uses httpx2
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    httpx = pytest.importorskip("httpx")

from _loader import load  # noqa: E402

ex = load("t06_applied_ml_llm", "ex_06_claude_messages")


def make_message(blocks, stop_reason="end_turn"):
    return anthropic.types.Message.model_validate(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": blocks,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    )


def text_block(text):
    return {"type": "text", "text": text}


class FakeClient:
    def __init__(self, message):
        self.calls = []
        self._message = message
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._message


def status_error(cls, code):
    request = httpx.Request("POST", "https://api.example.test/v1/messages")
    return cls("boom", response=httpx.Response(code, request=request), body=None)


# ---- 1 build_request ----
def test_build_request_basic_and_no_mutation():
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    req = ex.build_request(history, "what next?", system="Be brief.", max_tokens=200)
    assert req["model"] == ex.MODEL and req["max_tokens"] == 200 and req["system"] == "Be brief."
    assert req["messages"][-1] == {"role": "user", "content": "what next?"}
    assert len(req["messages"]) == 3
    assert len(history) == 2  # unchanged


def test_build_request_omits_system_when_missing():
    req = ex.build_request([], "hello")
    assert "system" not in req
    assert req["messages"] == [{"role": "user", "content": "hello"}]
    assert req["max_tokens"] == 1024


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user_text": "   "},
        {"user_text": "ok", "max_tokens": 0},
        {"user_text": "ok", "history": [{"role": "system", "content": "x"}]},
    ],
)
def test_build_request_validation(kwargs):
    params = {"history": [], **kwargs}
    with pytest.raises(ValueError):
        ex.build_request(params.pop("history"), params.pop("user_text"), **params)


# ---- 2 extract_text ----
def test_extract_text_skips_non_text_blocks():
    msg = make_message(
        [
            {"type": "thinking", "thinking": "hmm", "signature": "sig"},
            text_block("Hello, "),
            {"type": "tool_use", "id": "toolu_1", "name": "t", "input": {}},
            text_block("world"),
        ]
    )
    assert ex.extract_text(msg) == "Hello, world"
    assert ex.extract_text(make_message([])) == ""


# ---- 3 ask ----
def test_ask_returns_text_and_sends_request():
    client = FakeClient(make_message([text_block("Paris")]))
    assert ex.ask(client, "Capital of France?", system="Be brief.") == "Paris"
    (call,) = client.calls
    assert call["system"] == "Be brief."
    assert call["messages"] == [{"role": "user", "content": "Capital of France?"}]
    assert call["max_tokens"] > 0


def test_ask_refusal_and_truncation():
    with pytest.raises(ex.RefusalError):
        ex.ask(FakeClient(make_message([], "refusal")), "x")
    with pytest.raises(ex.TruncatedError):
        ex.ask(FakeClient(make_message([text_block("partial")], "max_tokens")), "x")


# ---- 4 is_retryable ----
@pytest.mark.parametrize(
    ("cls", "code", "expected"),
    [
        (anthropic.RateLimitError, 429, True),
        (anthropic.InternalServerError, 500, True),
        (anthropic.InternalServerError, 503, True),
        (anthropic.APIStatusError, 408, True),
        (anthropic.APIStatusError, 409, True),
        (anthropic.BadRequestError, 400, False),
        (anthropic.AuthenticationError, 401, False),
        (anthropic.NotFoundError, 404, False),
    ],
)
def test_is_retryable_status_errors(cls, code, expected):
    assert ex.is_retryable(status_error(cls, code)) is expected


def test_is_retryable_connection_and_other():
    request = httpx.Request("POST", "https://api.example.test")
    assert ex.is_retryable(anthropic.APIConnectionError(request=request)) is True
    assert ex.is_retryable(anthropic.APITimeoutError(request=request)) is True
    assert ex.is_retryable(ValueError("nope")) is False


# ---- 5 call_with_retry ----
def test_call_with_retry_backoff_then_success():
    attempts, sleeps = [], []

    def flaky():
        attempts.append(1)
        if len(attempts) < 4:
            raise status_error(anthropic.RateLimitError, 429)
        return "ok"

    assert ex.call_with_retry(flaky, max_attempts=5, sleep=sleeps.append) == "ok"
    assert sleeps == [1.0, 2.0, 4.0]


def test_call_with_retry_caps_delay():
    sleeps = []

    def always_fails():
        raise status_error(anthropic.InternalServerError, 500)

    with pytest.raises(anthropic.InternalServerError):
        ex.call_with_retry(
            always_fails, max_attempts=5, base_delay=10, max_delay=25, sleep=sleeps.append
        )
    assert sleeps == [10, 20, 25, 25]  # 4 sleeps for 5 attempts


def test_call_with_retry_non_retryable_raises_immediately():
    calls, sleeps = [], []

    def bad():
        calls.append(1)
        raise status_error(anthropic.BadRequestError, 400)

    with pytest.raises(anthropic.BadRequestError):
        ex.call_with_retry(bad, sleep=sleeps.append)
    assert len(calls) == 1 and sleeps == []
