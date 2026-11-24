# Python Tutorial — Basics to Production

A hands-on curriculum to learn Python from zero to advanced, then apply it as a:

- **Backend engineer** (FastAPI)
- **Cloud engineer** (AWS / GCP, IaC, containers)
- **Applied ML / LLM engineer** (Anthropic Claude, Google Gemini, open-source models via Hugging Face / Ollama / vLLM)
- **Robotics infrastructure engineer** (ROS 2, telemetry, MCAP, on-device inference)
- **Forward deployed engineer** (customer integrations, rapid prototyping, LLM apps in customer environments)

## Tracks

| # | Track | Status | What you learn |
|---|-------|--------|----------------|
| 01 | [`t01_fundamentals`](t01_fundamentals/README.md) | ✅ Written | Syntax, data types, control flow, collections, functions, errors, files, modules, venv/uv |
| 02 | [`t02_intermediate`](t02_intermediate/README.md) | ✅ Written | OOP, dataclasses, generators, decorators, context managers, typing, logging, regex, pytest, packaging |
| 03 | [`t03_advanced`](t03_advanced/README.md) | ✅ Written | Protocols/generics, metaclasses, concurrency & GIL, asyncio, profiling, pydantic, typer, patterns |
| 04 | [`t04_fastapi_backend`](t04_fastapi_backend/README.md) | ✅ Written | REST, FastAPI, DI, SQLAlchemy 2 + Alembic, auth/JWT, WebSockets, Redis, queues, OTel, Docker |
| 05 | [`t05_cloud_engineering`](t05_cloud_engineering/README.md) | ✅ Written | boto3, Lambda, DynamoDB, SQS, GCP SDK, CDK/Pulumi, Kubernetes, CI/CD, serverless FastAPI |
| 06 | [`t06_applied_ml_llm`](t06_applied_ml_llm/README.md) | ✅ Written | numpy/pandas/sklearn/PyTorch, Claude & Gemini SDKs, HF/Ollama/vLLM, embeddings, RAG, agents/MCP, evals, LoRA |
| 07 | [`t07_robotics_infra`](t07_robotics_infra/README.md) | 🚧 Stubs | Binary protocols, serial/CAN, ROS 2 rclpy, telemetry pipelines, MCAP, simulation, ONNX on device |
| 08 | [`t08_forward_deployed`](t08_forward_deployed/README.md) | 🚧 Stubs | Customer API integration, ETL, OAuth/webhooks, Streamlit/Gradio, LLM integration, prod debugging |

## Role-based paths

Everyone does **t01 → t02 → t03** first. Then:

| Role | Path after t03 |
|------|----------------|
| Backend engineer | t04 → t05 |
| Cloud engineer | t04 → t05 (deep) |
| Applied ML / LLM engineer | t04 → t06 → t05 |
| Robotics infra engineer | t04 → t07 → t06 (lessons 05, 10–12) → t05 |
| Forward deployed engineer | t04 → t06 → t08 → t05 |

## Setup

Requires [uv](https://docs.astral.sh/uv/). Python 3.15 is pinned in `.python-version`; uv installs it automatically.

```bash
# `uv sync` is exact: it installs ONLY the groups you name (plus dev/advanced defaults)
# and removes the rest. Combine flags, e.g. `uv sync --group backend --group ml`,
# or install everything with `uv sync --all-groups`.
uv sync                      # dev tools (pytest, ruff) + pydantic/typer (t03)
uv sync --group backend      # FastAPI stack (t04)
uv sync --group cloud        # boto3 + moto (offline AWS mocks), GCP, k8s (t05)
uv sync --group ml           # numpy, pandas, sklearn, anthropic, google-genai, ollama, sqlite-vec, mcp (t06)
uv sync --group ml-torch     # torch, transformers, peft (t06 PyTorch / HF / LoRA lessons; large download)
uv sync --group robotics     # mcap (t07)
uv sync --group fde          # polars, streamlit (t08)
```

## How to study

Each track has the same layout:

```
tNN_track/
├── README.md              goals, lesson table, checklist, capstone
├── m_NN_<topic>.py        lesson — read it, run it, tweak it
├── exercises/ex_NN_*.py   your work — replace `raise NotImplementedError`
├── solutions/ex_NN_*.py   reference answers (peek only when stuck)
└── tests/test_ex_NN_*.py  checks your exercises
```

```bash
# 1. Run a lesson
uv run python -m t01_fundamentals.m_04_strings

# 2. Solve the matching exercise, then test it
uv run pytest t01_fundamentals -k strings

# 3. Run all tests against the reference solutions
SOLUTIONS=1 uv run pytest

# Lint / format
uv run ruff check . && uv run ruff format .
```

Secrets (e.g. `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, AWS credentials) go in environment variables or a local `.env`. `.env` is git-ignored — never commit keys.

## Progress

- [ ] t01 Fundamentals
- [ ] t02 Intermediate
- [ ] t03 Advanced
- [ ] t04 FastAPI Backend
- [ ] t05 Cloud Engineering
- [ ] t06 Applied ML & LLMs
- [ ] t07 Robotics Infra
- [ ] t08 Forward Deployed Engineering

## Extra references

1. [Official Python Tutorial](https://docs.python.org/3/tutorial/)
2. [PYTHON.LAND](https://python.land/python-tutorial)
3. [w3schools](https://www.w3schools.com/python/)
4. [Geeks For Geeks](https://www.geeksforgeeks.org/python-programming-language/)
5. [FastAPI docs](https://fastapi.tiangolo.com/)
