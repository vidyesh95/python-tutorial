"""Reference solution for exercise 06."""

from collections import defaultdict
from collections.abc import Callable


def account_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {"accounts": 0, "total_arr": 0, "avg_arr": 0, "top_region": None}
    total = sum(r["arr"] for r in rows)
    by_region: dict[str, int] = defaultdict(int)
    for r in rows:
        by_region[r["region"]] += r["arr"]
    top = min(by_region, key=lambda region: (-by_region[region], region))
    return {
        "accounts": len(rows),
        "total_arr": total,
        "avg_arr": round(total / len(rows)),
        "top_region": top,
    }


def mask_email(email: str) -> str:
    local, at, domain = email.partition("@")
    if not at or not local:
        return "***"
    return f"{local[0]}***@{domain}"


def counter_app() -> None:
    import streamlit as st

    st.title("Counter")
    if "count" not in st.session_state:
        st.session_state.count = 0
    if st.button("Increment"):
        st.session_state.count += 1
    if st.button("Reset"):
        st.session_state.count = 0
    st.metric("Count", st.session_state.count)


def build_lookup_demo(lookup: Callable[[str], str]):
    import gradio as gr

    with gr.Blocks() as demo:
        query = gr.Textbox(label="Query")
        button = gr.Button("Search")
        result = gr.Textbox(label="Result", interactive=False)
        button.click(lookup, inputs=query, outputs=result)
    return demo
