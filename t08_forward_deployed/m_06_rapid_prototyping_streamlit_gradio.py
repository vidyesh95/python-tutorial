# Rapid Prototyping with Streamlit and Gradio
"""
In week one the customer needs to SEE something working. Streamlit and Gradio turn a Python
function into a web UI in minutes, so stakeholders can click through your integration, give
feedback, and stop imagining it. They are prototypes: great for demos and internal tools, not
a replacement for a real product front end.

Streamlit: the whole script RE-RUNS top to bottom on every interaction.
- Widgets return their current value: `region = st.selectbox("Region", [...])`.
- `st.session_state` keeps values between reruns (counters, selections, fetched data).
- `@st.cache_data(ttl=300)` caches function results (e.g. an API call) so reruns are instant.
- Layout: `st.sidebar`, `st.columns`, `st.tabs`; output: `st.dataframe`, `st.metric`, `st.bar_chart`.
- Run:  uv run python -m streamlit run t08_forward_deployed/m_06_rapid_prototyping_streamlit_gradio.py

Gradio: you declare components and wire events to plain functions.
- `gr.Blocks()` + `button.click(fn, inputs=[...], outputs=[...])`; `gr.Interface(fn, ...)` for
  the one-function case. Gradio also exposes every function as an API.
- Run:  uv run python t08_forward_deployed/m_06_rapid_prototyping_streamlit_gradio.py --gradio
  (this lesson never launches a server on its own).

HOW TO KEEP IT TESTABLE: put the logic in plain functions (`filter_accounts`, `account_metrics`)
and keep the UI code thin. Then test the UI headlessly:
- Streamlit: `streamlit.testing.v1.AppTest.from_function(app).run()`, then click buttons and
  read `at.metric`, `at.dataframe` (no browser, no server). The function must be self-contained:
  it is executed from its SOURCE, so imports go inside it.
- Gradio: build the `Blocks` object WITHOUT `.launch()` and call the wired function directly.

Security for demos (they leak data fast)
- Demo data only: synthetic or heavily masked. Never wire a prototype to production PII.
- Streamlit/Gradio bind to localhost by default; keep it so. NEVER `share=True` in Gradio (a
  public tunnel URL). To expose it, put it behind the customer's SSO / VPN / reverse proxy, or use
  `st.login()` (OIDC) / `launch(auth=...)`.
- Secrets via `st.secrets` or env vars, never in the script or widgets. Mask PII on screen.
- Demos get copied: assume the screenshot ends up in a customer-wide email.

Run: uv run python -m t08_forward_deployed.m_06_rapid_prototyping_streamlit_gradio
"""

import logging
import sys

ACCOUNTS: list[dict] = [
    {
        "name": "Acme Logistics",
        "region": "NA",
        "arr": 480_000,
        "health": "good",
        "contact": "ana.ruiz@acme.example",
    },
    {
        "name": "Borealis Bank",
        "region": "EU",
        "arr": 910_000,
        "health": "at risk",
        "contact": "j.mertens@borealis.example",
    },
    {
        "name": "Cobalt Retail",
        "region": "NA",
        "arr": 125_000,
        "health": "good",
        "contact": "sam@cobalt.example",
    },
    {
        "name": "Delta Health",
        "region": "APAC",
        "arr": 350_000,
        "health": "good",
        "contact": "li.wei@delta.example",
    },
    {
        "name": "Evergreen Energy",
        "region": "EU",
        "arr": 220_000,
        "health": "at risk",
        "contact": "k.berg@evergreen.example",
    },
]
REGIONS = ["All", "NA", "EU", "APAC"]


# Example 1: the logic lives in plain, testable functions
def filter_accounts(rows: list[dict], region: str = "All", min_arr: int = 0) -> list[dict]:
    return [r for r in rows if region in ("All", r["region"]) and r["arr"] >= min_arr]


def account_metrics(rows: list[dict]) -> dict:
    total = sum(r["arr"] for r in rows)
    return {
        "accounts": len(rows),
        "total_arr": total,
        "at_risk": sum(r["health"] == "at risk" for r in rows),
        "avg_arr": round(total / len(rows)) if rows else 0,
    }


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def public_view(rows: list[dict]) -> list[dict]:
    """What the UI may show: PII masked, nothing the viewer does not need."""
    return [
        {
            **{k: r[k] for k in ("name", "region", "arr", "health")},
            "contact": mask_email(r["contact"]),
        }
        for r in rows
    ]


def summarize(row: dict) -> str:  # stand-in for the LLM call in lesson 07
    return f"{row['name']} ({row['region']}): ${row['arr']:,} ARR, health is {row['health']}."


# Example 2: Streamlit app. Self-contained on purpose: AppTest and `streamlit run` execute it as
# a script, so everything it needs is imported inside the function.
def streamlit_app() -> None:
    import streamlit as st

    from t08_forward_deployed.m_06_rapid_prototyping_streamlit_gradio import (
        ACCOUNTS,
        REGIONS,
        account_metrics,
        filter_accounts,
        public_view,
        summarize,
    )

    st.title("Account explorer")
    region = st.sidebar.selectbox("Region", REGIONS, key="region")
    min_arr = st.sidebar.slider("Minimum ARR", 0, 1_000_000, 0, step=50_000, key="min_arr")

    rows = filter_accounts(ACCOUNTS, region, min_arr)
    metrics = account_metrics(rows)
    left, middle, right = st.columns(3)
    left.metric("Accounts", metrics["accounts"])
    middle.metric("Total ARR", f"${metrics['total_arr']:,}")
    right.metric("At risk", metrics["at_risk"])

    if rows:
        st.dataframe(public_view(rows), hide_index=True)
        st.bar_chart({r["name"]: r["arr"] for r in rows})
    else:
        st.warning("No accounts match these filters.")

    if "summaries" not in st.session_state:  # survives reruns
        st.session_state.summaries = 0
    if st.button("Summarize top account", disabled=not rows):
        st.session_state.summaries += 1
        st.info(summarize(max(rows, key=lambda r: r["arr"])))
    st.caption(f"Summaries generated this session: {st.session_state.summaries}")


# Example 3: Gradio Blocks (constructed, never launched here)
def build_gradio_app():
    import gradio as gr

    def lookup(region: str, min_arr: float) -> tuple[list[list], str]:
        rows = filter_accounts(ACCOUNTS, region, int(min_arr))
        table = [[r["name"], r["region"], r["arr"], r["health"]] for r in public_view(rows)]
        return table, f"{len(rows)} accounts, ${sum(r['arr'] for r in rows):,} ARR"

    with gr.Blocks(title="Account explorer") as demo:
        gr.Markdown("## Account explorer (demo data)")
        region = gr.Dropdown(REGIONS, value="All", label="Region")
        min_arr = gr.Slider(0, 1_000_000, value=0, step=50_000, label="Minimum ARR")
        button = gr.Button("Search")
        table = gr.Dataframe(headers=["name", "region", "arr", "health"], label="Accounts")
        summary = gr.Textbox(label="Summary", interactive=False)
        button.click(lookup, inputs=[region, min_arr], outputs=[table, summary])
    return demo


def run_demo() -> None:
    from streamlit.testing.v1 import AppTest

    for name in ("streamlit", "streamlit.runtime.scriptrunner_utils.script_run_context"):
        logging.getLogger(name).setLevel(logging.ERROR)  # quiet the "bare mode" warnings

    at = AppTest.from_function(streamlit_app).run()
    print("title:", at.title[0].value, "| metrics:", [(m.label, m.value) for m in at.metric])
    at.sidebar.selectbox(key="region").select("EU").run()
    print("EU only:", [(m.label, m.value) for m in at.metric])
    at.button[0].click().run()
    print("after click:", at.info[0].value, "|", at.caption[0].value)
    at.sidebar.slider(key="min_arr").set_value(1_000_000).run()
    print("nothing matches:", at.warning[0].value, "| summarize disabled:", at.button[0].disabled)
    print("exceptions:", len(at.exception))

    demo = build_gradio_app()  # no .launch(): no port opened
    fn = next(iter(demo.fns.values())).fn
    print("gradio handler:", fn("NA", 200_000)[1], "| components:", len(demo.blocks))


"""
Common mistakes:
- Heavy work at the top of a Streamlit script without `st.cache_data`: it re-runs on every click.
- Expecting normal variables to persist: they reset each rerun; use `st.session_state`.
- Business logic buried in callbacks, so nothing can be tested without a browser.
- `share=True` (Gradio) or binding to 0.0.0.0 on a laptop that holds customer data.
- Calling a live customer API on every widget change (rate limits!). Cache, or add a "Refresh"
  button.
- Shipping the prototype as the product. When it needs auth, roles, SLAs, or scale, rebuild it.

In the field:
- Demo against a sandbox or synthetic data, narrate the happy path, then show one failure
  (what the user sees when the API is down). Capture feedback live in a shared doc.
- Deploy internal prototypes where the customer already has SSO (Streamlit Community Cloud is
  public by default: do not use it for customer data). A container behind their proxy is fine.
- Pin versions in a `uv` group (done: `uv sync --group fde`) so the demo still runs in a month.
"""

if __name__ == "__main__":
    try:  # `streamlit run` executes this file as __main__ inside a script run context
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        in_streamlit = get_script_run_ctx(suppress_warning=True) is not None
    except ImportError:  # pragma: no cover
        in_streamlit = False
    if in_streamlit:
        streamlit_app()
    elif "--gradio" in sys.argv:  # explicit opt-in: opens a local port on 127.0.0.1
        build_gradio_app().launch(server_name="127.0.0.1", share=False)
    else:
        run_demo()
