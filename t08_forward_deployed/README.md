# Track 08: Forward-Deployed Engineering

Goal: work like a Forward-Deployed Engineer: embed with a customer, integrate their messy
systems, and leave them with something they can run without you. By the end you will scope an
engagement, build a defensive client for a rate-limited customer API, clean and load messy data
with Polars and DuckDB, handle OAuth and API keys safely, receive and send signed webhooks,
demo a prototype in Streamlit or Gradio, add an LLM behind PII redaction and evals, debug
production calmly, and write the runbook and handoff docs.

Prerequisites: `t01_fundamentals`, `t02_intermediate` and `t04_fastapi_backend` (`t05_cloud_engineering`
recommended; `t06_applied_ml_llm` helps for lesson 07). Python 3.15, managed with `uv`.

## Setup

```bash
uv sync --group fde
```

Need more than one track's tools? Combine groups in one command, for example
`uv sync --group fde --group ml` (or `--group cloud`, `--group backend`). Syncing replaces the
environment with exactly the groups you list, so always pass every group you still want.

Every lesson, exercise, and test runs OFFLINE with no customer, no cloud account and no keys:
- Customer HTTP APIs are mocked with `respx` or `httpx.MockTransport`; webhook receivers are
  exercised with FastAPI's in-process `TestClient`.
- OAuth, JWT and API-key flows use local keys and mocked token endpoints. Secrets in the code
  are obvious fakes and the lessons never print real credentials.
- LLM calls are real only if you set `ANTHROPIC_API_KEY` (or `GEMINI_API_KEY`); otherwise the
  same adapter code runs against an in-process fake server. Model ids are configuration:
  `CLAUDE_MODEL` (default `claude-opus-5-5`) and `GEMINI_MODEL` (default `gemini-3.8-flash`).
- Streamlit apps are tested with `streamlit.testing.v1.AppTest` and Gradio apps are built
  without `.launch()`, so no server or port is ever opened by a lesson or a test.
- No file is left behind: temporary Parquet files live in a `TemporaryDirectory`.

### Security habits this track drills

- Customer data stays in the customer's environment; redact PII before logs, prompts and demos.
- Least privilege: read-only service accounts, scoped tokens, a model-invoke-only identity.
- Secrets come from environment variables or a secret manager; never from code, tickets or logs.
- Verify webhook signatures with a constant-time compare, bound the timestamp, dedupe events.
- Treat every customer document as untrusted input (prompt injection) and validate model output.

## Lessons

| #  | Lesson (`m_NN_*.py`)                       | You learn                                                                    | Status |
|----|--------------------------------------------|------------------------------------------------------------------------------|--------|
| 01 | `m_01_role_of_fde`                         | the role, engagement phases and exit gates, discovery checklist, risk register | ✅ |
| 02 | `m_02_integrating_customer_apis`           | httpx client design, pagination, 429/Retry-After, tenacity retries, idempotency keys | ✅ |
| 03 | `m_03_etl_pandas_polars`                   | messy CSV cleaning, validation, Polars lazy API, DuckDB SQL, incremental loads | ✅ |
| 04 | `m_04_auth_flows_oauth_api_keys`           | API keys, client credentials, auth code + PKCE, token cache/refresh, JWT validation | ✅ |
| 05 | `m_05_webhooks`                            | FastAPI receiver, HMAC + replay protection, idempotency, queue handoff, dead letters | ✅ |
| 06 | `m_06_rapid_prototyping_streamlit_gradio`  | Streamlit and Gradio demos, headless testing, demo security                   | ✅ |
| 07 | `m_07_llm_integration_in_customer_env`     | private deployments, PII redaction, injection defenses, extraction, evals, cost | ✅ |
| 08 | `m_08_debugging_production`                | structured logs, correlation ids, tracebacks, py-spy/tracemalloc, replay, bisect, flags | ✅ |
| 09 | `m_09_writing_runbooks_and_docs`           | runbooks, ADRs, handoff docs, generating and linting Markdown                | ✅ |

Each lesson has a matching exercise `exercises/ex_NN_*.py` (stubs that raise
`NotImplementedError`), a reference implementation `solutions/ex_NN_*.py`, and tests in
`tests/test_ex_NN_*.py`.

## How to work

1. Run the lesson and read the code next to its output.
2. Open the exercise, read the docstrings (they specify exact behavior and edge cases), and
   implement the stubs.
3. Run the tests for that exercise until they pass.
4. Only then compare with the solution.

### Run a lesson

```bash
uv run python -m t08_forward_deployed.m_02_integrating_customer_apis
# Streamlit demo UI (opens a local server on 127.0.0.1):
uv run python -m streamlit run t08_forward_deployed/m_06_rapid_prototyping_streamlit_gradio.py
# Gradio demo UI (opt-in, local only):
uv run python t08_forward_deployed/m_06_rapid_prototyping_streamlit_gradio.py --gradio
```

### Run the tests

```bash
uv run pytest t08_forward_deployed                    # all exercises (fail until you implement them)
uv run pytest t08_forward_deployed -k webhooks        # one exercise by keyword
uv run pytest t08_forward_deployed -x                 # stop at the first failure
SOLUTIONS=1 uv run pytest t08_forward_deployed        # test the reference solutions instead
```

Before you start, failures are `NotImplementedError`. That is expected.

### Lint and format

```bash
uv run ruff check t08_forward_deployed && uv run ruff format t08_forward_deployed
```

## Progress checklist

- [ ] 01 The Forward-Deployed Engineer role: lesson read, exercise passing
- [ ] 02 Integrating customer APIs: lesson read, exercise passing
- [ ] 03 ETL with pandas and Polars: lesson read, exercise passing
- [ ] 04 Auth flows: OAuth and API keys: lesson read, exercise passing
- [ ] 05 Webhooks: lesson read, exercise passing
- [ ] 06 Rapid prototyping with Streamlit and Gradio: lesson read, exercise passing
- [ ] 07 LLM integration in customer environments: lesson read, exercise passing
- [ ] 08 Debugging production systems: lesson read, exercise passing
- [ ] 09 Writing runbooks and docs: lesson read, exercise passing
- [ ] Capstone below finished, tested, containerized and handed off
- [ ] `uv run ruff check t08_forward_deployed` is clean

## Capstone project: an end-to-end customer integration

Pretend you are embedded at "Acme Logistics". Build, in its own folder (for example
`capstone_t08/`) so the lesson files stay untouched, an integration that pulls their data,
makes it useful with an LLM, serves it back, and is documented well enough to hand over. Everything
must run offline against mocks; keys are optional and only enable live LLM calls.

### Requirements

1. **Mock customer API** (`respx` or a small FastAPI app): OAuth2 client-credentials token
   endpoint, a paginated `/invoices` endpoint (cursor), rate limiting that returns 429 with
   `Retry-After`, and an occasional 503. Credentials come from environment variables.
2. **Ingest**: an httpx client with timeouts, a token cache that refreshes before expiry,
   tenacity retries with jitter that honor `Retry-After`, a resumable cursor/watermark, and
   typed pydantic models. Tests prove the retry, pagination and refresh behavior.
3. **ETL**: clean and validate with Polars (strings first, typed after), route bad rows to a
   rejects table with reasons, upsert incrementally by key and version, write Parquet, and
   answer questions with DuckDB SQL. Emit a data-quality report.
4. **LLM step**: extract structured fields or a summary from invoice text with the provider-agnostic
   client from m_07 (Claude by default, `CLAUDE_MODEL`/`GEMINI_MODEL` overrides, a fake when no
   key). Redact PII before the prompt, defend against injected documents, validate the output,
   and add an eval set with a pass threshold that fails CI when quality drops. Report the
   estimated monthly cost.
5. **Service**: a FastAPI app exposing `/health`, `/invoices` and `/invoices/{id}/summary`, with
   API-key auth (hashed keys, constant-time compare), JSON logs with correlation ids, and no PII
   or secrets in logs. Add a signed outgoing webhook (`invoice.summarized`) with retries, and an
   incoming webhook receiver with signature + timestamp verification and idempotent processing
   that hands events to a worker queue with a dead-letter list.
6. **Demo UI**: a Streamlit (or Gradio) app that shows ingestion status, the cleaned table with
   masked PII, rejects, and the LLM summaries. Test it headlessly (`AppTest` or Blocks
   construction); no `share=True`.
7. **Docs and handoff**: generate a runbook (alerts, first steps, rollback, escalation) from a
   dataclass spec and lint it; write two ADRs (for example "queue between receiver and worker" and
   "where PII is redacted"); write a handoff doc with owners, locations of secrets (never the
   secrets), known issues and a first-week checklist for the customer's engineer.
8. **Quality and packaging**: pytest covering every step (offline), `ruff check` clean, a
   multi-stage non-root `Dockerfile` and a `compose.yaml` that runs the API, the worker and the UI
   with secrets from an env file that is git-ignored.

### Suggested layout

```
capstone_t08/
├── fake_customer.py          # mocked OAuth + paginated + rate-limited API
├── ingest.py                 # client, token cache, retries, resumable sync
├── etl.py                    # Polars cleaning, validation, upsert, DuckDB queries
├── llm.py                    # provider-agnostic client, redaction, extraction, evals
├── service.py                # FastAPI app, API-key auth, webhooks, worker
├── ui.py                     # Streamlit or Gradio demo
├── docs/
│   ├── runbook.md            # generated from a dataclass spec, then linted
│   ├── adr/0001-queue-between-receiver-and-worker.md
│   └── handoff.md
├── tests/                    # one test module per step, all offline
├── Dockerfile
├── compose.yaml
└── .env.example              # variable NAMES only, no values
```

Stretch: deploy the service to the cloud from t05 with secrets in a secret manager; add OpenTelemetry
traces keyed by correlation id; replay recorded customer traffic in a regression test; run the
LLM step on Bedrock or Vertex instead of the Anthropic API; add a canary feature flag for the
new summarizer.
