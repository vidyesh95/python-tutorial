# Track 06: Applied ML and LLMs

Goal: go from "I can call a model API" to "I can build, evaluate, and operate an LLM-backed
service". By the end you will use NumPy, pandas, scikit-learn, and PyTorch for data and ML
basics; call Claude and Gemini with their official SDKs (messages, streaming, tool use, prompt
caching, structured output); run open models locally with Ollama, vLLM, and Hugging Face
Transformers; store and search embeddings; build a retrieval-augmented (RAG) pipeline with
citations; write agents and an MCP server; measure quality with evals; understand LoRA
fine-tuning; and hide all of it behind one provider-agnostic interface.

Prerequisites: `t01_fundamentals` and `t02_intermediate` (type hints, dataclasses, generators,
pytest); `t04_fastapi_backend` for the capstone. Python 3.15, managed with `uv`.

## Setup

```bash
uv sync --group ml                # NumPy, pandas, scikit-learn, anthropic, google-genai, ollama, sqlite-vec, mcp
uv sync --group ml-torch          # OPTIONAL: torch, transformers, peft, accelerate (large download)
```

Every lesson, exercise, and test runs OFFLINE: no API keys, no model downloads, no servers.
When a real provider is configured the lessons use it; otherwise they print a notice and run the
same code against fakes (`httpx.MockTransport`, scripted fake models, a deterministic toy
embedding function).

| Variable | Enables | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | real Claude calls (default model `claude-opus-5-5`, override with `CLAUDE_MODEL`) | never print or commit it |
| `GEMINI_API_KEY` | real Gemini calls (default model `gemini-3.8-flash`, override with `GEMINI_MODEL`) | never print or commit it |
| `OLLAMA_HOST` | a running Ollama server (default `http://localhost:11434`) | checked with a 1 second timeout |
| `VLLM_BASE_URL` | an OpenAI-compatible vLLM server, e.g. `http://gpu-box:8000/v1` | vLLM itself is Linux + GPU only |
| `HF_RUN=1`, `LORA_RUN=1` | real Hugging Face model download / real LoRA training (m_10, m_17) | needs `--group ml-torch` |

API keys come from environment variables only. Use a git-ignored `.env` or export them in your
shell; never commit keys.

Note on vector databases: `chromadb` and `onnxruntime` do not publish Python 3.15 wheels yet, so
this track uses `sqlite-vec` (a SQLite extension) plus plain NumPy for vector search. The ideas
transfer directly to Chroma, pgvector, Qdrant, and friends (m_13 has a pgvector overview).

## Lessons

| #  | Lesson (`m_NN_*.py`)                         | You learn                                                                   | Status |
|----|----------------------------------------------|-----------------------------------------------------------------------------|--------|
| 01 | `m_01_numpy`                                 | arrays, vectorization, broadcasting                                         | ✅ |
| 02 | `m_02_pandas`                                | DataFrames, selection, groupby, joins                                       | ✅ |
| 03 | `m_03_matplotlib`                            | plotting data and model results                                             | ✅ |
| 04 | `m_04_scikit_learn`                          | pipelines, train/test split, metrics                                        | ✅ |
| 05 | `m_05_pytorch_basics`                        | tensors, autograd, a tiny training loop                                     | ✅ |
| 06 | `m_06_anthropic_claude_messages`             | the Claude Messages API with the `anthropic` SDK                            | ✅ |
| 07 | `m_07_claude_streaming_tool_use`             | streaming responses, tool use                                               | ✅ |
| 08 | `m_08_claude_prompt_caching_structured_output` | prompt caching, structured output                                         | ✅ |
| 09 | `m_09_google_gemini_genai`                   | Gemini with the `google-genai` SDK                                          | ✅ |
| 10 | `m_10_huggingface_transformers`              | tokenizers (toy BPE), `pipeline`, `generate`, decoding, devices             | ✅ |
| 11 | `m_11_ollama_local_models`                   | `ollama pull/run`, chat, streaming NDJSON, embeddings, Modelfile            | ✅ |
| 12 | `m_12_vllm_serving`                          | PagedAttention, continuous batching, OpenAI-compatible server and client    | ✅ |
| 13 | `m_13_embeddings_vector_db`                  | embeddings, cosine, chunking, sqlite-vec KNN, pgvector overview             | ✅ |
| 14 | `m_14_rag_pipeline`                          | ingest, chunk, embed, retrieve, rerank, prompt with citations, retrieval eval | ✅ |
| 15 | `m_15_agents_and_mcp`                        | agent loop, stop conditions, guardrails, an in-process MCP server           | ✅ |
| 16 | `m_16_llm_evals`                             | golden datasets, graders, LLM-as-judge, regression diffs, cost and latency  | ✅ |
| 17 | `m_17_fine_tuning_lora_peft`                 | fine-tune vs prompt vs RAG, dataset formats, LoRA/QLoRA math, PEFT config   | ✅ |
| 18 | `m_18_provider_abstraction_layer`            | `LLMClient` Protocol, adapters, retries, fallback chain, cost tracking      | ✅ |

Each lesson has a matching exercise `exercises/ex_NN_*.py` (stubs that raise
`NotImplementedError`), a reference implementation `solutions/ex_NN_*.py`, and tests in
`tests/test_ex_NN_*.py`.

## How to work

1. Run the lesson and read the code next to its output.
2. Open the exercise, read the docstring (it specifies every function), implement the stubs.
3. Run the tests for that exercise until they pass.
4. Only then compare with the solution.

### Run a lesson

```bash
uv run python -m t06_applied_ml_llm.m_14_rag_pipeline
```

Lessons print what they do, finish in a few seconds, and leave no files behind (temporary
directories only). Set an API key or server variable from the table above to switch a lesson
from the fake to the real provider.

### Run the tests

```bash
uv run pytest t06_applied_ml_llm                     # all exercises (fail until you implement them)
uv run pytest t06_applied_ml_llm -k ex_14            # one exercise by keyword
uv run pytest t06_applied_ml_llm -x                  # stop at the first failure
SOLUTIONS=1 uv run pytest t06_applied_ml_llm         # test the reference solutions instead
```

Before you start, failures are `NotImplementedError`. That is expected.

### Lint and format

```bash
uv run ruff check t06_applied_ml_llm && uv run ruff format t06_applied_ml_llm
```

## Progress checklist

- [ ] 01 NumPy arrays and vectorization: lesson read, exercise passing
- [ ] 02 pandas DataFrames: lesson read, exercise passing
- [ ] 03 Plotting with matplotlib: lesson read, exercise passing
- [ ] 04 scikit-learn pipelines: lesson read, exercise passing
- [ ] 05 PyTorch basics: lesson read, exercise passing
- [ ] 06 Claude Messages API: lesson read, exercise passing
- [ ] 07 Claude streaming and tool use: lesson read, exercise passing
- [ ] 08 Prompt caching and structured output: lesson read, exercise passing
- [ ] 09 Google Gemini with google-genai: lesson read, exercise passing
- [ ] 10 Hugging Face Transformers: lesson read, exercise passing
- [ ] 11 Local models with Ollama: lesson read, exercise passing
- [ ] 12 Serving models with vLLM: lesson read, exercise passing
- [ ] 13 Embeddings and vector databases: lesson read, exercise passing
- [ ] 14 Retrieval-augmented generation pipeline: lesson read, exercise passing
- [ ] 15 Agents and the Model Context Protocol: lesson read, exercise passing
- [ ] 16 LLM evaluation: lesson read, exercise passing
- [ ] 17 Fine-tuning with LoRA and PEFT: lesson read, exercise passing
- [ ] 18 Provider abstraction layer: lesson read, exercise passing
- [ ] Capstone below finished, tested, and containerized
- [ ] `uv run ruff check t06_applied_ml_llm` is clean

## Capstone project: RAG service with a swappable LLM backend

Build `docqa`, a retrieval-augmented question-answering service behind FastAPI. Put it in its
own folder (for example `capstone_t06/`) so the lesson files stay untouched. Treat it as a
service you would be happy to deploy.

### Requirements

1. **Ingest endpoint**: `POST /ingest` accepts documents (text or markdown plus metadata),
   chunks them with overlap, embeds the chunks, and stores vectors and metadata in sqlite-vec
   (a file path from settings; `:memory:` in tests). Re-ingesting an unchanged document is a
   no-op (content hash).
2. **Query endpoint with citations**: `POST /ask` retrieves top-k chunks, reranks, builds a
   numbered-source prompt, calls the selected LLM, and returns `answer`, `citations` (source,
   chunk id, snippet), and `usage`. It answers "I don't know" when retrieval is weak and rejects
   citations that point at sources that were never supplied.
3. **Swappable backend**: a `provider` setting/request field selects Claude, Gemini, or a local
   model (Ollama or vLLM through the OpenAI-compatible adapter), all behind the lesson 18
   `LLMClient` Protocol, with retries, timeouts, and an optional fallback chain. A `FakeLLM`
   is the default in tests and when no keys are configured.
4. **Streaming**: `POST /ask/stream` streams the answer as server-sent events and ends with a
   final event carrying the citations.
5. **Eval suite**: a script plus a golden JSONL dataset that reports retrieval metrics
   (hit-rate@k, MRR) and answer metrics (exact/regex/semantic and an LLM-judge with a fake
   judge in CI) per provider, diffs against the previous run, and fails when quality regresses.
6. **Cost and latency tracking**: record tokens, dollars, and latency per request; expose
   totals at `GET /metrics` (p50/p95 latency, cost per provider).
7. **Configuration and secrets**: `pydantic-settings`; `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
   `OLLAMA_HOST`, `VLLM_BASE_URL` read only from the environment (`SecretStr`); no keys in git,
   logs, or error messages.
8. **Tests**: pytest with `TestClient` and fake embedder/LLM/providers; no network; cover
   ingest idempotency, citation validation, provider fallback, and the streaming format.
9. **Docker**: a multi-stage `Dockerfile` (uv, non-root, healthcheck) and a `compose.yaml` that
   starts the API with a volume for the vector database (and optionally an Ollama container).

### Suggested layout

```
capstone_t06/
├── pyproject.toml
├── Dockerfile
├── compose.yaml
├── .env.example
├── src/docqa/
│   ├── main.py            # FastAPI app, lifespan, routes
│   ├── settings.py        # pydantic-settings
│   ├── store.py           # sqlite-vec schema, ingest, retrieve
│   ├── chunking.py        # chunker with overlap
│   ├── embeddings.py      # Embedder protocol, toy + real implementations
│   ├── rag.py             # rerank, prompt, citations, abstain logic
│   ├── llm/               # LLMClient Protocol, Claude, Gemini, OpenAI-compatible, FakeLLM
│   └── metrics.py         # token/cost/latency tracking
├── evals/
│   ├── golden.jsonl
│   └── run_evals.py
└── tests/
```

Stretch: hybrid search (BM25 plus vectors with reciprocal-rank fusion), an MCP server that
exposes `ask` as a tool, per-tenant isolation with metadata filters, and a LoRA-tuned local
model compared against the prompted baseline in your eval suite.
