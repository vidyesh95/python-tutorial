# Track 04 — FastAPI Backend

**Who it's for:** Backend engineers building HTTP APIs and services in Python

## Goals

- Design and validate REST APIs with FastAPI and Pydantic
- Persist data with SQLAlchemy 2.0 and Alembic on Postgres
- Secure, test, containerize, and observe a production-style API

## Prerequisite tracks

- t01_fundamentals, t02_intermediate (t03_advanced recommended)

## Setup

```bash
uv sync --group backend
```

Note: All lessons use the `backend` dependency group. Run the Postgres and Redis lessons with Docker running.

## Lessons

| File | Topic | Status |
|---|---|---|
| `m_01_http_rest_basics.py` | HTTP and REST Basics | STUB |
| `m_02_first_fastapi_app.py` | Your First FastAPI App | STUB |
| `m_03_path_query_body_params.py` | Path, Query and Body Parameters | STUB |
| `m_04_pydantic_models_validation.py` | Pydantic Models and Validation | STUB |
| `m_05_dependency_injection.py` | Dependency Injection with Depends | STUB |
| `m_06_routers_project_structure.py` | APIRouter and Project Structure | STUB |
| `m_07_sqlalchemy_2_orm.py` | SQLAlchemy 2.0 ORM | STUB |
| `m_08_alembic_migrations.py` | Database Migrations with Alembic | STUB |
| `m_09_postgres_in_docker.py` | PostgreSQL in Docker | STUB |
| `m_10_auth_oauth2_jwt.py` | OAuth2 Password Flow and JWT | STUB |
| `m_11_background_tasks.py` | Background Tasks | STUB |
| `m_12_websockets.py` | WebSockets | STUB |
| `m_13_middleware_cors.py` | Middleware and CORS | STUB |
| `m_14_testing_fastapi.py` | Testing FastAPI Apps | STUB |
| `m_15_redis_caching.py` | Redis Caching | STUB |
| `m_16_task_queues_arq_celery.py` | Task Queues with arq and Celery | STUB |
| `m_17_observability_opentelemetry.py` | Observability with OpenTelemetry | STUB |
| `m_18_dockerizing_fastapi.py` | Dockerizing FastAPI | STUB |
| `m_19_settings_and_secrets.py` | Settings and Secrets | STUB |

## Checklist

- [ ] m_01: HTTP and REST Basics
- [ ] m_02: Your First FastAPI App
- [ ] m_03: Path, Query and Body Parameters
- [ ] m_04: Pydantic Models and Validation
- [ ] m_05: Dependency Injection with Depends
- [ ] m_06: APIRouter and Project Structure
- [ ] m_07: SQLAlchemy 2.0 ORM
- [ ] m_08: Database Migrations with Alembic
- [ ] m_09: PostgreSQL in Docker
- [ ] m_10: OAuth2 Password Flow and JWT
- [ ] m_11: Background Tasks
- [ ] m_12: WebSockets
- [ ] m_13: Middleware and CORS
- [ ] m_14: Testing FastAPI Apps
- [ ] m_15: Redis Caching
- [ ] m_16: Task Queues with arq and Celery
- [ ] m_17: Observability with OpenTelemetry
- [ ] m_18: Dockerizing FastAPI
- [ ] m_19: Settings and Secrets

## Capstone project

Build a task-management API: a FastAPI service with users, projects, and tasks. Requirements: JWT authentication via the OAuth2 password flow, SQLAlchemy 2.0 models with Alembic migrations targeting Postgres, Redis-cached task listings with invalidation on writes, a background job that flags overdue tasks, and typed settings read from the environment. Ship a pytest suite that overrides the database dependency, a multi-stage Dockerfile, and a compose.yaml that starts the API, Postgres, and Redis together.
