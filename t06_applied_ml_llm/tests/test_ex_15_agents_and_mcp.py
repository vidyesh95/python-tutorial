from _loader import load

ex = load("t06_applied_ml_llm", "ex_15_agents_and_mcp")


def add(a: int, b: int) -> int:
    """Add two integers.

    Longer text that must not appear in the description.
    """
    return a + b


def greet(name: str, shout: bool = False, times: float = 1.0) -> str:
    return name


def scripted(*turns):
    queue = list(turns)
    seen: list[list[dict]] = []

    def model(messages):
        seen.append([dict(m) for m in messages])
        return queue.pop(0)

    model.seen = seen
    return model


def call(name, **args):
    return {"name": name, "args": args}


def test_tool_spec_from_function():
    assert ex.tool_spec_from_function(add) == {
        "name": "add",
        "description": "Add two integers.",
        "input_schema": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    }


def test_tool_spec_defaults_and_types():
    spec = ex.tool_spec_from_function(greet)
    assert spec["description"] == ""
    assert spec["input_schema"]["required"] == ["name"]
    assert spec["input_schema"]["properties"]["shout"] == {"type": "boolean"}
    assert spec["input_schema"]["properties"]["times"] == {"type": "number"}


def test_is_looping():
    a, b = ("search", {"q": "x"}), ("search", {"q": "y"})
    assert ex.is_looping([a, a, a])
    assert not ex.is_looping([a, a])
    assert not ex.is_looping([a, a, b])
    assert not ex.is_looping([b, a, a])
    assert ex.is_looping([b, a, a, a])
    assert ex.is_looping([a, a], limit=2)


def test_check_tool_call_allowlist_and_approval():
    assert ex.check_tool_call("add", {}) is None
    assert ex.check_tool_call("rm", {}, allowed={"add"}) == "tool 'rm' is not allowed"
    danger = frozenset({"rm"})
    assert ex.check_tool_call("rm", {}, dangerous=danger) == "tool 'rm' requires approval"
    assert (
        ex.check_tool_call("rm", {}, dangerous=danger, approve=lambda n, a: False)
        == "tool 'rm' requires approval"
    )
    assert (
        ex.check_tool_call("rm", {"f": 1}, dangerous=danger, approve=lambda n, a: a["f"] == 1)
        is None
    )


def test_agent_tool_then_final_and_observation_fed_back():
    model = scripted({"tool_calls": [call("add", a=2, b=3)]}, {"final": "The sum is 5"})
    result = ex.run_agent("2+3?", model, {"add": add})
    assert (result.answer, result.stop_reason, result.steps) == ("The sum is 5", "final", 2)
    assert result.trace == [("add", {"a": 2, "b": 3}, "5")]
    second_turn_messages = model.seen[1]
    assert second_turn_messages[0] == {"role": "user", "content": "2+3?"}
    assert second_turn_messages[-1] == {"role": "tool", "name": "add", "content": "5"}
    assert second_turn_messages[1]["role"] == "assistant"


def test_agent_immediate_final():
    result = ex.run_agent("hi", scripted({"final": "hello"}), {})
    assert (result.answer, result.stop_reason, result.steps, result.trace) == (
        "hello",
        "final",
        1,
        [],
    )


def test_agent_max_steps():
    turns = [{"tool_calls": [call("add", a=i, b=1)]} for i in range(10)]
    result = ex.run_agent("x", scripted(*turns), {"add": add}, max_steps=3)
    assert (result.answer, result.stop_reason, result.steps) == (None, "max_steps", 3)
    assert len(result.trace) == 3


def test_agent_detects_loop():
    turns = [{"tool_calls": [call("add", a=1, b=1)]} for _ in range(10)]
    result = ex.run_agent("x", scripted(*turns), {"add": add}, max_steps=10)
    assert result.stop_reason == "loop"
    assert result.steps == 3
    assert len(result.trace) == 2  # the third identical call is not executed


def test_agent_errors_become_observations():
    model = scripted(
        {"tool_calls": [call("nope"), call("add", a="x", b=1), call("add", b=1)]}, {"final": "ok"}
    )

    def flaky(a: int, b: int) -> int:
        if not isinstance(a, int):
            raise ValueError("a must be an int")
        return a + b

    result = ex.run_agent("x", model, {"add": flaky})
    obs = [o for _, _, o in result.trace]
    assert obs[0] == "error: unknown tool 'nope'"
    assert obs[1] == "error: a must be an int"
    assert obs[2].startswith("error:")
    assert result.stop_reason == "final"


def test_agent_guardrails_block_without_running():
    ran: list[str] = []

    def rm(path: str) -> str:
        ran.append(path)
        return "deleted"

    model = scripted({"tool_calls": [call("rm", path="/")]}, {"final": "done"})
    result = ex.run_agent("x", model, {"rm": rm}, dangerous=frozenset({"rm"}))
    assert result.trace[0][2] == "blocked: tool 'rm' requires approval"
    assert ran == []

    model = scripted({"tool_calls": [call("rm", path="/tmp/x")]}, {"final": "done"})
    result = ex.run_agent(
        "x",
        model,
        {"rm": rm},
        dangerous=frozenset({"rm"}),
        approve=lambda n, a: a["path"].startswith("/tmp"),
    )
    assert result.trace[0][2] == "deleted" and ran == ["/tmp/x"]

    model = scripted({"tool_calls": [call("rm", path="/")]}, {"final": "done"})
    result = ex.run_agent("x", model, {"rm": rm}, allowed={"add"})
    assert result.trace[0][2] == "blocked: tool 'rm' is not allowed"


def test_trace_is_independent_between_runs():
    r1 = ex.run_agent(
        "x", scripted({"tool_calls": [call("add", a=1, b=1)]}, {"final": "a"}), {"add": add}
    )
    r2 = ex.run_agent("x", scripted({"final": "b"}), {"add": add})
    assert len(r1.trace) == 1 and r2.trace == []
