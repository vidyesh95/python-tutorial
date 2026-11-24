# Track 06 — Applied ML and LLMs

**Who it's for:** ML and AI engineers building data pipelines, model integrations, and LLM-backed services

## Goals

- Work fluently with NumPy, pandas, and scikit-learn for data tasks
- Call Claude, Gemini, and local models through one consistent interface
- Build, evaluate, and serve a retrieval-augmented (RAG) service

## Prerequisite tracks

- t01_fundamentals, t02_intermediate, t04_fastapi_backend (for the capstone)

## Setup

```bash
uv sync --group ml
```

Note: API keys are read from environment variables: `ANTHROPIC_API_KEY` for Claude and `GEMINI_API_KEY` for Gemini. Never commit keys. Use a local `.env` that is git-ignored, or export them in your shell. Local-model lessons (Ollama, vLLM) need a machine with enough RAM or a GPU.

## Lessons

| File | Topic | Status |
|---|---|---|
| `m_01_numpy.py` | NumPy Arrays and Vectorization | STUB |
| `m_02_pandas.py` | pandas DataFrames | STUB |
| `m_03_matplotlib.py` | Plotting with matplotlib | STUB |
| `m_04_scikit_learn.py` | scikit-learn Pipelines | STUB |
| `m_05_pytorch_basics.py` | PyTorch Basics | STUB |
| `m_06_anthropic_claude_messages.py` | Claude Messages API | STUB |
| `m_07_claude_streaming_tool_use.py` | Claude Streaming and Tool Use | STUB |
| `m_08_claude_prompt_caching_structured_output.py` | Prompt Caching and Structured Output | STUB |
| `m_09_google_gemini_genai.py` | Google Gemini with the google-genai SDK | STUB |
| `m_10_huggingface_transformers.py` | Hugging Face Transformers | STUB |
| `m_11_ollama_local_models.py` | Local Models with Ollama | STUB |
| `m_12_vllm_serving.py` | Serving Models with vLLM | STUB |
| `m_13_embeddings_vector_db.py` | Embeddings and Vector Databases | STUB |
| `m_14_rag_pipeline.py` | Retrieval-Augmented Generation Pipeline | STUB |
| `m_15_agents_and_mcp.py` | Agents and the Model Context Protocol | STUB |
| `m_16_llm_evals.py` | LLM Evaluation | STUB |
| `m_17_fine_tuning_lora_peft.py` | Fine-Tuning with LoRA and PEFT | STUB |
| `m_18_provider_abstraction_layer.py` | Provider Abstraction Layer | STUB |

## Checklist

- [ ] m_01: NumPy Arrays and Vectorization
- [ ] m_02: pandas DataFrames
- [ ] m_03: Plotting with matplotlib
- [ ] m_04: scikit-learn Pipelines
- [ ] m_05: PyTorch Basics
- [ ] m_06: Claude Messages API
- [ ] m_07: Claude Streaming and Tool Use
- [ ] m_08: Prompt Caching and Structured Output
- [ ] m_09: Google Gemini with the google-genai SDK
- [ ] m_10: Hugging Face Transformers
- [ ] m_11: Local Models with Ollama
- [ ] m_12: Serving Models with vLLM
- [ ] m_13: Embeddings and Vector Databases
- [ ] m_14: Retrieval-Augmented Generation Pipeline
- [ ] m_15: Agents and the Model Context Protocol
- [ ] m_16: LLM Evaluation
- [ ] m_17: Fine-Tuning with LoRA and PEFT
- [ ] m_18: Provider Abstraction Layer

## Capstone project

Build a RAG service behind FastAPI with a swappable backend. Requirements: /ingest and /ask endpoints; documents chunked, embedded, and stored in a vector database; retrieval results passed to a provider selected at runtime (Claude, Gemini, or a local Ollama model) through the lesson 18 abstraction layer; answers that include source citations; an eval script that reports retrieval and answer metrics per provider; and API keys supplied only through the ANTHROPIC_API_KEY and GEMINI_API_KEY environment variables.
