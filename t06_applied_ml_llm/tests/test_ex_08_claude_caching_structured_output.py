import pytest

pytest.importorskip("anthropic")
pytest.importorskip("pydantic")
import anthropic
from pydantic import BaseModel

from _loader import load

ex = load("t06_applied_ml_llm", "ex_08_claude_caching_structured_output")


class Ticket(BaseModel):
    category: str
    urgency: int


def usage(input_tokens=0, write=None, read=None):
    return anthropic.types.Usage(
        input_tokens=input_tokens,
        output_tokens=10,
        cache_creation_input_tokens=write,
        cache_read_input_tokens=read,
    )


def message(text):
    return anthropic.types.Message.model_validate(
        {
            "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    )  # fmt: skip


class ScriptedClient:
    def __init__(self, *texts):
        self.replies = [message(t) for t in texts]
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.replies.pop(0)


# ---- 1 cache_savings ----
def test_cache_savings_cache_hit():
    out = ex.cache_savings(usage(input_tokens=1_000, read=99_000), input_price=4.0, read_mult=0.05)
    assert out["baseline_cost"] == pytest.approx(0.4)
    assert out["actual_cost"] == pytest.approx((1_000 + 99_000 * 0.05) * 4 / 1e6)
    assert out["saved"] == pytest.approx(out["baseline_cost"] - out["actual_cost"])
    assert out["hit_rate"] == pytest.approx(0.99)


def test_cache_savings_first_request_costs_more_than_baseline():
    out = ex.cache_savings(usage(input_tokens=100, write=10_000), input_price=10.0)
    assert out["actual_cost"] == pytest.approx((100 + 10_000 * 1.25) * 10 / 1e6)
    assert out["saved"] < 0
    assert out["hit_rate"] == 0.0


def test_cache_savings_handles_none_fields_and_zero_tokens():
    out = ex.cache_savings(usage(input_tokens=500), input_price=2.0)
    assert out["saved"] == pytest.approx(0.0)
    zero = ex.cache_savings(usage(0), input_price=2.0)
    assert zero == {"actual_cost": 0.0, "baseline_cost": 0.0, "saved": 0.0, "hit_rate": 0.0}


# ---- 2 build_cached_request ----
def test_build_cached_request_shape():
    req = ex.build_cached_request("BIG DOC", "Summarize?")
    assert req["model"] == ex.MODEL and req["max_tokens"] == 1024
    assert req["system"] == [
        {"type": "text", "text": "BIG DOC", "cache_control": {"type": "ephemeral"}}
    ]
    assert req["messages"] == [{"role": "user", "content": "Summarize?"}]
    assert "cache_control" not in str(req["messages"])


def test_build_cached_request_ttl():
    req = ex.build_cached_request("doc", "q", ttl="1h")
    assert req["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    with pytest.raises(ValueError):
        ex.build_cached_request("doc", "q", ttl="2h")


# ---- 3 parse_structured ----
def test_parse_structured_plain_and_fenced():
    assert ex.parse_structured('{"category": "bug", "urgency": 3}', Ticket) == Ticket(
        category="bug", urgency=3
    )
    fenced = '```json\n{"category": "bug", "urgency": 3}\n```'
    assert ex.parse_structured(fenced, Ticket).urgency == 3
    assert ex.parse_structured('```\n{"category": "x", "urgency": 1}\n```', Ticket).category == "x"


@pytest.mark.parametrize(
    "bad", ["not json", '{"category": "bug"}', '{"category": "bug", "urgency": "high"}', ""]
)
def test_parse_structured_errors(bad):
    with pytest.raises(ex.StructuredOutputError):
        ex.parse_structured(bad, Ticket)


# ---- 4 extract_with_retry ----
def test_extract_with_retry_succeeds_first_time():
    client = ScriptedClient('{"category": "billing", "urgency": 2}')
    assert ex.extract_with_retry(client, "I was double charged", Ticket).category == "billing"
    assert len(client.calls) == 1
    assert client.calls[0]["messages"] == [{"role": "user", "content": "I was double charged"}]


def test_extract_with_retry_feeds_error_back():
    client = ScriptedClient("sorry, here you go: nope", '{"category": "bug", "urgency": 4}')
    result = ex.extract_with_retry(client, "app crashes", Ticket)
    assert result == Ticket(category="bug", urgency=4)
    second = client.calls[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    assert second[1]["content"] == "sorry, here you go: nope"
    assert "invalid" in second[2]["content"].lower()


def test_extract_with_retry_gives_up():
    client = ScriptedClient("x", "y", "z", '{"category": "bug", "urgency": 1}')
    with pytest.raises(ex.StructuredOutputError):
        ex.extract_with_retry(client, "q", Ticket, max_attempts=3)
    assert len(client.calls) == 3


# ---- 5 break_even_requests ----
@pytest.mark.parametrize(
    ("write", "read", "expected"),
    [(1.25, 0.1, 2), (2.0, 0.1, 3), (1.25, 0.05, 2), (3.0, 0.0, 4)],
)
def test_break_even_requests(write, read, expected):
    assert ex.break_even_requests(write, read) == expected


def test_break_even_never():
    with pytest.raises(ValueError):
        ex.break_even_requests(1.25, 1.0)
