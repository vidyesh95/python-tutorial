import pytest

from _loader import load

ex = load("t08_forward_deployed", "ex_06_rapid_prototyping_streamlit_gradio")


def test_account_metrics():
    rows = [
        {"name": "a", "region": "NA", "arr": 100},
        {"name": "b", "region": "EU", "arr": 300},
        {"name": "c", "region": "NA", "arr": 250},
    ]
    assert ex.account_metrics(rows) == {
        "accounts": 3,
        "total_arr": 650,
        "avg_arr": 217,
        "top_region": "NA",
    }


def test_account_metrics_empty_and_tie():
    assert ex.account_metrics([]) == {
        "accounts": 0,
        "total_arr": 0,
        "avg_arr": 0,
        "top_region": None,
    }
    tie = [{"name": "a", "region": "NA", "arr": 5}, {"name": "b", "region": "EU", "arr": 5}]
    assert ex.account_metrics(tie)["top_region"] == "EU"


@pytest.mark.parametrize(
    ("raw", "masked"),
    [
        ("jane.doe@example.com", "j***@example.com"),
        ("a@b.io", "a***@b.io"),
        ("no-at-sign", "***"),
        ("@example.com", "***"),
        ("", "***"),
    ],
)
def test_mask_email(raw, masked):
    assert ex.mask_email(raw) == masked


def _run(script, **kwargs):
    """Run a Streamlit script headlessly; re-raise NotImplementedError from unfinished stubs."""
    at = pytest.importorskip("streamlit.testing.v1").AppTest.from_function(script, **kwargs).run()
    for exc in at.exception:
        trace = "".join(exc.stack_trace)
        if "NotImplementedError" in trace:
            raise NotImplementedError("counter_app is not implemented yet")
        raise AssertionError(f"app raised: {exc.value}\n{trace}")
    return at


def test_counter_app_initial_render():
    at = _run(ex.counter_app)
    assert at.title[0].value == "Counter"
    assert at.metric[0].label == "Count" and at.metric[0].value == "0"
    assert [b.label for b in at.button] == ["Increment", "Reset"]


def test_counter_app_increment_and_reset():
    at = _run(ex.counter_app)
    at.button[0].click().run()
    at.button[0].click().run()
    assert at.session_state.count == 2
    assert at.metric[0].value == "2"
    at.button[1].click().run()
    assert at.session_state.count == 0 and at.metric[0].value == "0"


def test_build_lookup_demo_wires_function_without_launching():
    gr = pytest.importorskip("gradio")
    demo = ex.build_lookup_demo(lambda q: f"found:{q}")
    assert isinstance(demo, gr.Blocks)
    labels = {getattr(b, "label", None) for b in demo.blocks.values()}
    assert {"Query", "Result"} <= labels
    assert any(getattr(b, "value", None) == "Search" for b in demo.blocks.values())
    (handler,) = demo.fns.values()
    assert handler.fn("acme") == "found:acme"
    result = next(b for b in demo.blocks.values() if getattr(b, "label", None) == "Result")
    assert result.interactive is False
