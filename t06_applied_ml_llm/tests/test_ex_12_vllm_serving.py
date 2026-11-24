import json

import pytest

from _loader import load

ex = load("t06_applied_ml_llm", "ex_12_vllm_serving")
MSGS = [{"role": "user", "content": "hi"}]


def test_build_chat_request_defaults():
    assert ex.build_chat_request("m", MSGS) == {
        "model": "m",
        "messages": MSGS,
        "max_tokens": 256,
        "temperature": 0.0,
    }


def test_build_chat_request_options():
    body = ex.build_chat_request(
        "m", MSGS, max_tokens=10, temperature=0.7, stream=True, stop=["\n\n"]
    )
    assert body["stream"] is True
    assert body["stop"] == ["\n\n"]
    assert body["max_tokens"] == 10 and body["temperature"] == 0.7
    assert "stream" not in ex.build_chat_request("m", MSGS)
    assert "stop" not in ex.build_chat_request("m", MSGS, stop=None)


def _event(text):
    return "data: " + json.dumps({"choices": [{"delta": {"content": text}}]})


def test_parse_sse_collects_deltas():
    lines = [
        ": keep-alive",
        _event("Hel"),
        "",
        "data: " + json.dumps({"choices": [{"delta": {"role": "assistant"}}]}),
        _event("lo"),
        "data: [DONE]",
        _event("ignored"),
    ]
    assert ex.parse_sse(lines) == ["Hel", "lo"]


def test_parse_sse_empty():
    assert ex.parse_sse([]) == []


def test_kv_bytes_per_token_llama3_8b():
    assert ex.kv_bytes_per_token(32, 8, 128) == 131072
    assert ex.kv_bytes_per_token(32, 8, 128, dtype_bytes=1) == 65536


def test_max_concurrent_sequences():
    per_token = ex.kv_bytes_per_token(32, 8, 128)
    # (80*0.9 - 16) = 56 GiB budget; one 8k sequence = 1 GiB
    assert ex.max_concurrent_sequences(80, 16, 0.9, per_token, 8192) == 56
    assert ex.max_concurrent_sequences(80, 16, 0.9, per_token, 32768) == 14


def test_max_concurrent_sequences_never_negative():
    assert ex.max_concurrent_sequences(24, 30, 0.9, 131072, 4096) == 0


@pytest.mark.parametrize(
    ("lengths", "batch", "expected"),
    [
        ([], 4, 0),
        ([5], 4, 5),
        ([3, 3, 3], 3, 3),
        ([10, 1, 1, 1], 2, 10),
        ([4, 1, 1, 4], 2, 6),
        ([2, 2, 2, 2], 1, 8),
    ],
)
def test_continuous_batching_steps(lengths, batch, expected):
    assert ex.continuous_batching_steps(lengths, batch) == expected
