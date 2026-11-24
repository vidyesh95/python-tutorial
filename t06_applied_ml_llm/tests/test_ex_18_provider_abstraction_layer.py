import pytest

from _loader import load

ex = load("t06_applied_ml_llm", "ex_18_provider_abstraction_layer")
MSGS = [{"role": "user", "content": "hi"}]


class HttpError(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (ex.RetryableError("x"), True),
        (TimeoutError(), True),
        (ConnectionError(), True),
        (HttpError(429), True),
        (HttpError(503), True),
        (HttpError(408), True),
        (HttpError(400), False),
        (HttpError(401), False),
        (HttpError(404), False),
        (ValueError("bad"), False),
    ],
)
def test_is_retryable(exc, expected):
    assert ex.is_retryable(exc) is expected


def test_backoff_delays():
    assert ex.backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]
    assert ex.backoff_delays(6, base=1, cap=5) == [1, 2, 4, 5, 5, 5]
    assert ex.backoff_delays(0) == []


def test_backoff_delays_factor():
    assert ex.backoff_delays(3, base=1, factor=3, cap=100) == [1, 3, 9]


def test_retry_succeeds_after_transient_errors():
    attempts, sleeps = [], []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise ex.RetryableError("busy")
        return "done"

    assert ex.call_with_retry(flaky, max_attempts=3, sleep=sleeps.append) == "done"
    assert len(attempts) == 3
    assert sleeps == [0.5, 1.0]


def test_retry_gives_up_and_reraises_without_trailing_sleep():
    sleeps = []

    def always():
        raise ex.RetryableError("down")

    with pytest.raises(ex.RetryableError):
        ex.call_with_retry(always, max_attempts=3, sleep=sleeps.append)
    assert sleeps == [0.5, 1.0]  # two waits between three attempts


def test_retry_non_retryable_raises_immediately():
    sleeps, calls = [], []

    def bad():
        calls.append(1)
        raise HttpError(400)

    with pytest.raises(HttpError):
        ex.call_with_retry(bad, sleep=sleeps.append)
    assert len(calls) == 1 and sleeps == []


def test_retry_uses_custom_base_and_single_attempt():
    sleeps = []
    calls = []

    def f():
        calls.append(1)
        raise ex.RetryableError("x")

    with pytest.raises(ex.RetryableError):
        ex.call_with_retry(f, max_attempts=1, sleep=sleeps.append)
    assert calls == [1] and sleeps == []
    with pytest.raises(ex.RetryableError):
        ex.call_with_retry(f, max_attempts=2, base=2.0, sleep=sleeps.append)
    assert sleeps == [2.0]


def test_fallback_uses_first_success():
    a, b = ex.FakeLLM(["from a"], name="a"), ex.FakeLLM(["from b"], name="b")
    chain = ex.FallbackChain([a, b])
    assert chain.complete(MSGS).text == "from a"
    assert chain.last_used == "a"
    assert b.calls == 0


def test_fallback_skips_failures():
    a = ex.FakeLLM([ex.RetryableError("429")], name="claude")
    b = ex.FakeLLM([HttpError(400)], name="gemini")
    c = ex.FakeLLM(["local answer"], name="ollama")
    chain = ex.FallbackChain([a, b, c])
    assert chain.complete(MSGS).text == "local answer"
    assert chain.last_used == "ollama"


def test_fallback_all_fail():
    e1, e2 = ex.RetryableError("one"), ValueError("two")
    chain = ex.FallbackChain([ex.FakeLLM([e1], name="a"), ex.FakeLLM([e2], name="b")])
    with pytest.raises(ex.AllProvidersFailed) as info:
        chain.complete(MSGS)
    assert info.value.errors == [e1, e2]


def test_fallback_empty_chain():
    with pytest.raises(ex.AllProvidersFailed) as info:
        ex.FallbackChain([]).complete(MSGS)
    assert info.value.errors == []


def test_cost_tracker():
    tracker = ex.CostTracker({"opus": (4.0, 20.0), "haiku": (0.1, 0.5)})
    tracker.record("opus", 1_000_000, 100_000)  # 4.00 + 2.00
    tracker.record("haiku", 2_000_000, 1_000_000)  # 0.20 + 0.50
    tracker.record("local", 5_000, 5_000)  # free / unknown
    assert tracker.calls == 3
    assert tracker.total_cost == pytest.approx(6.70)
    assert tracker.by_model() == pytest.approx({"opus": 6.0, "haiku": 0.7, "local": 0.0})


def test_cost_tracker_starts_empty():
    tracker = ex.CostTracker({})
    assert (tracker.calls, tracker.total_cost, tracker.by_model()) == (0, 0.0, {})
