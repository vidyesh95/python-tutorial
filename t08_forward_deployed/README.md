# Track 08 — Forward-Deployed Engineering

**Who it's for:** Engineers who embed with customers, integrate their systems, and ship working solutions fast

## Goals

- Integrate messy customer APIs, data, and auth flows safely
- Prototype quickly and debug production issues calmly
- Document integrations so customers can operate them without you

## Prerequisite tracks

- t01_fundamentals, t02_intermediate, t04_fastapi_backend (t05_cloud_engineering recommended)

## Setup

```bash
uv sync --group fde
```

Note: Lessons assume a sandbox or mock customer API; never use real customer credentials in this repo. Keep all secrets in environment variables.

## Lessons

| File | Topic | Status |
|---|---|---|
| `m_01_role_of_fde.py` | The Forward-Deployed Engineer Role | STUB |
| `m_02_integrating_customer_apis.py` | Integrating Customer APIs | STUB |
| `m_03_etl_pandas_polars.py` | ETL with pandas and Polars | STUB |
| `m_04_auth_flows_oauth_api_keys.py` | Auth Flows: OAuth and API Keys | STUB |
| `m_05_webhooks.py` | Webhooks | STUB |
| `m_06_rapid_prototyping_streamlit_gradio.py` | Rapid Prototyping with Streamlit and Gradio | STUB |
| `m_07_llm_integration_in_customer_env.py` | LLM Integration in Customer Environments | STUB |
| `m_08_debugging_production.py` | Debugging Production Systems | STUB |
| `m_09_writing_runbooks_and_docs.py` | Writing Runbooks and Docs | STUB |

## Checklist

- [ ] m_01: The Forward-Deployed Engineer Role
- [ ] m_02: Integrating Customer APIs
- [ ] m_03: ETL with pandas and Polars
- [ ] m_04: Auth Flows: OAuth and API Keys
- [ ] m_05: Webhooks
- [ ] m_06: Rapid Prototyping with Streamlit and Gradio
- [ ] m_07: LLM Integration in Customer Environments
- [ ] m_08: Debugging Production Systems
- [ ] m_09: Writing Runbooks and Docs

## Capstone project

Build an end-to-end customer integration demo: a Streamlit front end that pulls records from a mocked customer REST API (paginated and rate-limited), normalizes them with a Polars ETL step, authenticates with OAuth2 PKCE, receives change events through a signed webhook, and summarizes records with an LLM behind a redaction filter. Include a runbook covering failure modes, a compose.yaml that runs the demo, and a README with the customer setup steps.
