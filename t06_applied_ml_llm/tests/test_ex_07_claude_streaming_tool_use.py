import pytest

pytest.importorskip("anthropic")
pytest.importorskip("pydantic")
import anthropic
import pydantic

from _loader import load

ex = load("t06_applied_ml_llm", "ex_07_claude_streaming_tool_use")

EVENT = pydantic.TypeAdapter(anthropic.types.RawMessageStreamEvent)


def event(payload):
    return EVENT.validate_python(payload)


def text_delta(index, text):
    return event(
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "text_delta", "text": text},
        }
    )


def tool_start(index, id_, name):
    block = {"type": "tool_use", "id": id_, "name": name, "input": {}}
    return event({"type": "content_block_start", "index": index, "content_block": block})


def json_delta(index, fragment):
    delta = {"type": "input_json_delta", "partial_json": fragment}
    return event({"type": "content_block_delta", "index": index, "delta": delta})


def make_message(blocks, stop_reason):
    return anthropic.types.Message.model_validate(
        {
            "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": blocks, "stop_reason": stop_reason, "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    )  # fmt: skip


def tool_use(id_, name, **input_):
    return {"type": "tool_use", "id": id_, "name": name, "input": input_}


def expect_runtime_error(fn):
    """pytest.raises(RuntimeError) would also swallow NotImplementedError (a subclass)."""
    try:
        fn()
    except NotImplementedError:
        raise
    except RuntimeError:
        return
    pytest.fail("RuntimeError not raised")


class ScriptedClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})  # snapshot
        return self.responses.pop(0)


def field(obj, name):
    return obj[name] if isinstance(obj, dict) else getattr(obj, name)


# ---- 1 collect_text ----
def test_collect_text_joins_only_text_deltas():
    events = [
        event(
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            }
        ),
        text_delta(0, "Hel"),
        json_delta(1, '{"a": 1}'),
        text_delta(0, "lo"),
        event({"type": "content_block_stop", "index": 0}),
    ]
    assert ex.collect_text(iter(events)) == "Hello"
    assert ex.collect_text([]) == ""


# ---- 2 collect_tool_calls ----
def test_collect_tool_calls_assembles_fragments_per_index():
    events = [
        tool_start(0, "toolu_a", "calculator"),
        tool_start(1, "toolu_b", "capital_of"),
        json_delta(0, '{"expres'),
        json_delta(1, '{"country": '),
        json_delta(0, 'sion": "2+2"}'),
        json_delta(1, '"France"}'),
    ]
    assert ex.collect_tool_calls(events) == [
        {"id": "toolu_a", "name": "calculator", "input": {"expression": "2+2"}},
        {"id": "toolu_b", "name": "capital_of", "input": {"country": "France"}},
    ]


def test_collect_tool_calls_empty_and_invalid_json():
    assert ex.collect_tool_calls([tool_start(0, "toolu_a", "now")]) == [
        {"id": "toolu_a", "name": "now", "input": {}}
    ]
    with pytest.raises(ValueError):
        ex.collect_tool_calls([tool_start(0, "toolu_a", "calc"), json_delta(0, '{"expr')])


# ---- 3 execute_tool_use ----
def block(name, id_="toolu_1", **input_):
    return anthropic.types.ToolUseBlock(type="tool_use", id=id_, name=name, input=input_)


def test_execute_tool_use_success():
    registry = {"add": lambda a, b: a + b}
    assert ex.execute_tool_use(block("add", a=2, b=3), registry) == {
        "type": "tool_result",
        "tool_use_id": "toolu_1",
        "content": "5",
        "is_error": False,
    }


def test_execute_tool_use_errors():
    def boom(**_):
        raise ZeroDivisionError("division by zero")

    out = ex.execute_tool_use(block("boom"), {"boom": boom})
    assert out["is_error"] is True and out["content"] == "ZeroDivisionError: division by zero"
    unknown = ex.execute_tool_use(block("nope", id_="toolu_9"), {})
    assert unknown["is_error"] is True and unknown["tool_use_id"] == "toolu_9"
    assert "nope" in unknown["content"]


# ---- 4 run_tool_loop ----
TOOLS = [{"name": "add", "description": "add", "input_schema": {"type": "object"}}]


def test_loop_with_parallel_tools_sends_one_result_message():
    first = make_message(
        [tool_use("toolu_a", "add", a=1, b=2), tool_use("toolu_b", "add", a=10, b=20)], "tool_use"
    )
    final = make_message([{"type": "text", "text": "3 and 30"}], "end_turn")
    client = ScriptedClient(first, final)
    answer = ex.run_tool_loop(client, "add stuff", TOOLS, {"add": lambda a, b: a + b})
    assert answer == "3 and 30"
    assert len(client.calls) == 2
    sent = client.calls[1]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert [field(b, "id") for b in sent[1]["content"]] == ["toolu_a", "toolu_b"]
    results = sent[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["toolu_a", "toolu_b"]
    assert [r["content"] for r in results] == ["3", "30"]
    assert client.calls[0]["tools"] == TOOLS and client.calls[0]["max_tokens"] > 0


def test_loop_without_tools_returns_text_immediately():
    client = ScriptedClient(make_message([{"type": "text", "text": "hi"}], "end_turn"))
    assert ex.run_tool_loop(client, "hello", TOOLS, {}) == "hi"
    assert len(client.calls) == 1


def test_loop_reports_tool_errors_to_the_model():
    first = make_message([tool_use("toolu_a", "missing")], "tool_use")
    final = make_message([{"type": "text", "text": "sorry"}], "end_turn")
    client = ScriptedClient(first, final)
    assert ex.run_tool_loop(client, "q", TOOLS, {}) == "sorry"
    (result,) = client.calls[1]["messages"][-1]["content"]
    assert result["is_error"] is True


def test_loop_gives_up_after_max_turns():
    forever = [
        make_message([tool_use(f"toolu_{i}", "add", a=1, b=1)], "tool_use") for i in range(10)
    ]
    client = ScriptedClient(*forever)
    expect_runtime_error(
        lambda: ex.run_tool_loop(client, "q", TOOLS, {"add": lambda a, b: a + b}, max_turns=3)
    )
    assert len(client.calls) == 3


# ---- 5 validate_tool_input ----
SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": "string"},
        "days": {"type": "integer"},
        "units": {"type": "number"},
        "hot": {"type": "boolean"},
    },
    "required": ["city", "days"],
    "additionalProperties": False,
}


def test_validate_tool_input_ok():
    assert (
        ex.validate_tool_input(SCHEMA, {"city": "Paris", "days": 3, "units": 1.5, "hot": True})
        == []
    )
    assert ex.validate_tool_input(SCHEMA, {"city": "Paris", "days": 3, "units": 2}) == []


def test_validate_tool_input_problems_sorted():
    problems = ex.validate_tool_input(SCHEMA, {"days": "3", "extra": 1})
    assert problems == ["missing: city", "unexpected: extra", "wrong type: days"]


def test_validate_tool_input_bool_is_not_a_number():
    assert ex.validate_tool_input(SCHEMA, {"city": "x", "days": True}) == ["wrong type: days"]
    assert ex.validate_tool_input(SCHEMA, {"city": "x", "days": 1, "units": False}) == [
        "wrong type: units"
    ]


def test_validate_tool_input_extra_keys_allowed_when_not_forbidden():
    loose = {**SCHEMA, "additionalProperties": True}
    assert ex.validate_tool_input(loose, {"city": "x", "days": 1, "extra": 1}) == []
