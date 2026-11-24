"""Exercise 06: testable prototype logic, a Streamlit script and a Gradio Blocks app.

Tasks
1. account_metrics: summary numbers for the dashboard header.
2. mask_email: never show raw PII in a demo.
3. counter_app: a Streamlit script, tested headlessly with AppTest (no server).
4. build_lookup_demo: build (but do NOT launch) a Gradio Blocks app around a function.

Run: uv run pytest t08_forward_deployed -k ex_06
"""

from collections.abc import Callable


def account_metrics(rows: list[dict]) -> dict:
    """Rows look like {"name": str, "region": str, "arr": int}. Return
    {"accounts": count, "total_arr": sum, "avg_arr": round(total / count) (0 if no rows),
     "top_region": the region with the largest summed ARR (None if no rows; ties -> the
     alphabetically first region)}.
    """
    raise NotImplementedError


def mask_email(email: str) -> str:
    """ "jane.doe@example.com" -> "j***@example.com": keep the first character of the local part
    and the whole domain. If there is no "@" (or the local part is empty) return "***".
    """
    raise NotImplementedError


def counter_app() -> None:
    """A Streamlit script (it is executed from its own source, so do ALL imports inside it).

    - st.title("Counter")
    - keep an integer in st.session_state.count, starting at 0
    - st.button("Increment"): adds 1 to it
    - st.button("Reset"): sets it back to 0
    - show the value with st.metric("Count", st.session_state.count)
    Remember the whole script re-runs on every click: initialize state only if missing, and
    handle the buttons BEFORE drawing the metric.
    """
    raise NotImplementedError


def build_lookup_demo(lookup: Callable[[str], str]):
    """Return a `gradio.Blocks` (import gradio inside the function) containing
    - a Textbox labelled "Query" (input)
    - a Button labelled "Search"
    - a Textbox labelled "Result" (output, interactive=False)
    where clicking the button calls `lookup(query)` and writes the return value to "Result".
    Do not call .launch().
    """
    raise NotImplementedError
