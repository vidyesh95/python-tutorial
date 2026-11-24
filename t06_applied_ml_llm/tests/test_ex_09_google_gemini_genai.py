import pytest

pytest.importorskip("google.genai")
from google.genai import types

from _loader import load

ex = load("t06_applied_ml_llm", "ex_09_google_gemini_genai")


def expect_runtime_error(fn):
    """pytest.raises(RuntimeError) would also swallow NotImplementedError (a subclass)."""
    try:
        fn()
    except NotImplementedError:
        raise
    except RuntimeError:
        return
    pytest.fail("RuntimeError not raised")


def response(*parts):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))]
    )


def call(name, **args):
    return types.Part.from_function_call(name=name, args=args)


# ---- 1 build_contents ----
def test_build_contents_maps_roles_and_appends_user_message():
    contents = ex.build_contents(
        [("user", "hi"), ("assistant", "hello"), ("model", "more")], "next"
    )
    assert [c.role for c in contents] == ["user", "model", "model", "user"]
    assert [c.parts[0].text for c in contents] == ["hi", "hello", "more", "next"]
    assert all(isinstance(c, types.Content) for c in contents)


def test_build_contents_empty_history_and_bad_role():
    (only,) = ex.build_contents([], "solo")
    assert only.role == "user" and only.parts[0].text == "solo"
    with pytest.raises(ValueError):
        ex.build_contents([("system", "be nice")], "x")


# ---- 2 extract_text ----
def test_extract_text_skips_function_calls_and_thoughts():
    resp = response(
        types.Part(text="secret reasoning", thought=True),
        types.Part(text="Hello "),
        call("get_weather", city="Paris"),
        types.Part(text="world"),
    )
    assert ex.extract_text(resp) == "Hello world"


def test_extract_text_no_candidates():
    assert ex.extract_text(types.GenerateContentResponse()) == ""
    assert ex.extract_text(response(call("f"))) == ""


# ---- 3 get_function_calls ----
def test_get_function_calls():
    resp = response(
        call("a", x=1),
        types.Part(text="hmm"),
        call("b", y="z"),
        types.Part.from_function_call(name="c", args=None),
    )
    assert ex.get_function_calls(resp) == [("a", {"x": 1}), ("b", {"y": "z"}), ("c", {})]
    assert ex.get_function_calls(response(types.Part(text="plain"))) == []
    assert ex.get_function_calls(types.GenerateContentResponse()) == []


# ---- 4 function_response_content ----
def test_function_response_content():
    content = ex.function_response_content([("get_weather", {"temp_c": 18}), ("add", 5)])
    assert content.role == "user"
    assert [p.function_response.name for p in content.parts] == ["get_weather", "add"]
    assert content.parts[0].function_response.response == {"result": {"temp_c": 18}}
    assert content.parts[1].function_response.response == {"result": 5}


# ---- 5 run_function_loop ----
class ScriptedGenerate:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.seen = []

    def __call__(self, contents):
        self.seen.append(list(contents))
        return self.responses.pop(0)


def test_loop_runs_functions_then_returns_text():
    gen = ScriptedGenerate(
        response(call("add", a=2, b=3), call("shout", text="hi")),
        response(types.Part(text="The sum is 5.")),
    )
    registry = {"add": lambda a, b: a + b, "shout": lambda text: text.upper()}
    assert ex.run_function_loop(gen, "add 2 and 3", registry) == "The sum is 5."
    second = gen.seen[1]
    assert [c.role for c in second] == ["user", "model", "user"]
    assert second[0].parts[0].text == "add 2 and 3"
    assert [p.function_call.name for p in second[1].parts] == ["add", "shout"]
    results = second[2].parts
    assert [p.function_response.response for p in results] == [{"result": 5}, {"result": "HI"}]


def test_loop_without_function_calls():
    gen = ScriptedGenerate(response(types.Part(text="direct answer")))
    assert ex.run_function_loop(gen, "hi", {}) == "direct answer"
    assert len(gen.seen) == 1


def test_loop_tool_errors_become_error_results():
    def boom(**_):
        raise ValueError("bad input")

    gen = ScriptedGenerate(response(call("boom"), call("ghost")), response(types.Part(text="done")))
    assert ex.run_function_loop(gen, "q", {"boom": boom}) == "done"
    results = gen.seen[1][2].parts
    assert results[0].function_response.response == {"result": {"error": "bad input"}}
    assert "error" in results[1].function_response.response["result"]


def test_loop_gives_up_after_max_turns():
    gen = ScriptedGenerate(*[response(call("add", a=1, b=1)) for _ in range(6)])
    expect_runtime_error(
        lambda: ex.run_function_loop(gen, "q", {"add": lambda a, b: a + b}, max_turns=3)
    )
    assert len(gen.seen) == 3
