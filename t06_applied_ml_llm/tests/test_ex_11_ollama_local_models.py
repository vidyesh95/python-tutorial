import json

import pytest

from _loader import load

ex = load("t06_applied_ml_llm", "ex_11_ollama_local_models")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "http://localhost:11434"),
        ("", "http://localhost:11434"),
        ("127.0.0.1:11434", "http://127.0.0.1:11434"),
        ("myhost", "http://myhost:11434"),
        ("http://gpu-box:9999/", "http://gpu-box:9999"),
        ("https://ollama.example.com", "https://ollama.example.com:11434"),
    ],
)
def test_normalize_host(raw, expected):
    assert ex.normalize_host(raw) == expected


def test_build_chat_payload_minimal():
    msgs = [{"role": "user", "content": "hi"}]
    assert ex.build_chat_payload("llama3.2", msgs) == {
        "model": "llama3.2",
        "messages": msgs,
        "stream": False,
    }


def test_build_chat_payload_stream_and_options():
    payload = ex.build_chat_payload("m", [], stream=True, options={"temperature": 0})
    assert payload["stream"] is True
    assert payload["options"] == {"temperature": 0}


def test_collect_stream_text_and_speed():
    lines = [
        json.dumps({"message": {"content": "Hel"}, "done": False}),
        "",
        json.dumps({"message": {"content": "lo"}, "done": False}),
        json.dumps(
            {
                "message": {"content": ""},
                "done": True,
                "eval_count": 30,
                "eval_duration": 2_000_000_000,
            }
        ),
    ]
    text, tps = ex.collect_stream(lines)
    assert text == "Hello"
    assert tps == pytest.approx(15.0)


def test_collect_stream_without_stats():
    text, tps = ex.collect_stream([json.dumps({"message": {"content": "x"}, "done": True})])
    assert (text, tps) == ("x", None)
    _, tps = ex.collect_stream([json.dumps({"done": True, "eval_count": 5, "eval_duration": 0})])
    assert tps is None


def test_render_modelfile():
    out = ex.render_modelfile("llama3.2", "Be brief.", temperature=0.2, num_ctx=4096)
    assert out.splitlines() == [
        "FROM llama3.2",
        "PARAMETER temperature 0.2",
        "PARAMETER num_ctx 4096",
        "SYSTEM Be brief.",
    ]
    assert ex.render_modelfile("m", "s") == "FROM m\nSYSTEM s"


def test_estimate_memory_gb():
    assert ex.estimate_memory_gb(8, 4) == pytest.approx(5.5)
    assert ex.estimate_memory_gb(70, 16, overhead_gb=0) == pytest.approx(140.0)
