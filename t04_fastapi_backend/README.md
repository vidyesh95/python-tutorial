# Track 04: FastAPI Backend

Goal: go from "I can write Python" to "I can design, build, test, ship, and operate a
production-style HTTP API". By the end you will know FastAPI and Pydantic well, persist data
with SQLAlchemy 2.0 and Alembic on Postgres, secure an API with OAuth2 + JWT, and add the
things real services need: background jobs, WebSockets, caching, tests, observability,
containers, and proper configuration.

Prerequisites: `t01_fundamentals` and `t02_intermediate` (decorators, type hints, context
managers and pytest are used constantly); `t03_advanced` (async, threading) is recommended.
Python 3.15, managed with `uv`.

## Setup

```bash
uv sync --group backend
```

Every lesson, exercise, and test runs OFFLINE: no network, no Docker, no real Postgres or
Redis. Databases use in-memory SQLite and Redis uses `fakeredis`. Docker is only needed if you
want to try the container and Postgres lessons for real (m_09, m_18) or point a lesson at a
real Redis (`REDIS_URL=redis://localhost:6379/0`).

## Lessons

| #  | Lesson (`m_NN_*.py`)                  | You learn                                                              | Status |
|----|---------------------------------------|------------------------------------------------------------------------|--------|
| 01 | `m_01_http_rest_basics`               | HTTP methods, status codes, headers, REST resource design              | ✅ |
| 02 | `m_02_first_fastapi_app`              | `FastAPI()`, routes, uvicorn, automatic OpenAPI docs                   | ✅ |
| 03 | `m_03_path_query_body_params`         | path/query/body parameters, validation, `Annotated`                    | ✅ |
| 04 | `m_04_pydantic_models_validation`     | Pydantic v2 models, validators, response models, serialization         | ✅ |
| 05 | `m_05_dependency_injection`           | `Depends`, sub-dependencies, `yield` resources, overrides              | ✅ |
| 06 | `m_06_routers_project_structure`      | `APIRouter`, prefixes, tags, scalable project layout                   | ✅ |
| 07 | `m_07_sqlalchemy_2_orm`               | declarative models, sessions, relationships, queries, async engine     | ✅ |
| 08 | `m_08_alembic_migrations`             | revisions, autogenerate, upgrade/downgrade, safe schema changes        | ✅ |
| 09 | `m_09_postgres_in_docker`             | running Postgres in Docker, connection URLs, pooling                   | ✅ |
| 10 | `m_10_auth_oauth2_jwt`                | password hashing, OAuth2 password flow, JWT access tokens             | ✅ |
| 11 | `m_11_background_tasks`               | `BackgroundTasks`, error handling, when to use a real queue            | ✅ |
| 12 | `m_12_websockets`                     | WebSocket endpoints, connection manager, broadcast, disconnects        | ✅ |
| 13 | `m_13_middleware_cors`                | request-id/timing middleware, CORS, exception handlers, lifespan       | ✅ |
| 14 | `m_14_testing_fastapi`                | `TestClient`, `dependency_overrides`, `AsyncClient`, pytest fixtures   | ✅ |
| 15 | `m_15_redis_caching`                  | cache-aside, TTL, key design, invalidation, rate limiting, fakeredis   | ✅ |
| 16 | `m_16_task_queues_arq_celery`         | producer/broker/worker, retries, idempotency, arq vs Celery            | ✅ |
| 17 | `m_17_observability_opentelemetry`    | JSON logs, request ids, traces/spans, metrics, health/readiness        | ✅ |
| 18 | `m_18_dockerizing_fastapi`            | multi-stage uv Dockerfile, non-root, healthcheck, compose              | ✅ |
| 19 | `m_19_settings_and_secrets`           | pydantic-settings, `.env`, `SecretStr`, per-environment config         | ✅ |
| 20 | `m_20_auth_schema_sessions`           | Better Auth-style schema, DB sessions, JWT refresh rotation, OAuth link | ✅ |

Each lesson has a matching exercise `exercises/ex_NN_*.py` (stubs that raise
`NotImplementedError`), a reference implementation `solutions/ex_NN_*.py`, and tests in
`tests/test_ex_NN_*.py`. Lesson 18 also ships `docker/Dockerfile` and `docker/compose.yaml`
(the Postgres lesson adds `docker/compose.postgres.yaml`).

## How to work

1. Run the lesson and read the code next to its output. Most lessons expose a module-level
   `app`, so you can also serve it live (below).
2. Open the exercise, read the docstrings (they include examples), implement the stubs.
3. Run the tests for that exercise until they pass.
4. Only then compare with the solution.

### Run a lesson

```bash
uv run python -m t04_fastapi_backend.m_11_background_tasks
```

The `__main__` block exercises the app with `TestClient` and prints the results. It needs no
server, no input, and no network.

### Serve a lesson live

```bash
uv run fastapi dev t04_fastapi_backend/m_11_background_tasks.py
```

Then open http://127.0.0.1:8000/docs (Swagger UI) or http://127.0.0.1:8000/redoc. `fastapi
dev` auto-reloads on save. Use `uv run fastapi run <file>` for a production-style run.

### Run the tests

```bash
uv run pytest t04_fastapi_backend                    # all exercises (fail until you implement them)
uv run pytest t04_fastapi_backend -k background_tasks  # one exercise by keyword
uv run pytest t04_fastapi_backend -x                 # stop at the first failure
SOLUTIONS=1 uv run pytest t04_fastapi_backend        # test the reference solutions instead
```

Before you start, failures are `NotImplementedError`. That is expected.

### Lint and format

```bash
uv run ruff check t04_fastapi_backend && uv run ruff format t04_fastapi_backend
```

## Progress checklist

- [ ] 01 HTTP and REST basics: lesson read, exercise passing
- [ ] 02 First FastAPI app: lesson read, exercise passing
- [ ] 03 Path, query and body parameters: lesson read, exercise passing
- [ ] 04 Pydantic models and validation: lesson read, exercise passing
- [ ] 05 Dependency injection: lesson read, exercise passing
- [ ] 06 Routers and project structure: lesson read, exercise passing
- [ ] 07 SQLAlchemy 2.0 ORM: lesson read, exercise passing
- [ ] 08 Alembic migrations: lesson read, exercise passing
- [ ] 09 PostgreSQL in Docker: lesson read, exercise passing
- [ ] 10 OAuth2 and JWT auth: lesson read, exercise passing
- [ ] 11 Background tasks: lesson read, exercise passing
- [ ] 12 WebSockets: lesson read, exercise passing
- [ ] 13 Middleware and CORS: lesson read, exercise passing
- [ ] 14 Testing FastAPI apps: lesson read, exercise passing
- [ ] 15 Redis caching: lesson read, exercise passing
- [ ] 16 Task queues (arq and Celery): lesson read, exercise passing
- [ ] 17 Observability with OpenTelemetry: lesson read, exercise passing
- [ ] 18 Dockerizing FastAPI: lesson read, exercise passing
- [ ] 19 Settings and secrets: lesson read, exercise passing
- [ ] 20 Auth schema, sessions and token rotation: lesson read, exercise passing
- [ ] Capstone below finished, tested, and containerized
- [ ] `uv run ruff check t04_fastapi_backend` is clean

## Capstone project: task-management API

Build `taskboard`, a multi-user task-management API. Put it in its own folder (for example
`capstone_t04/`) so the lesson files stay untouched. Treat it as a service you would be happy
to deploy.

### Requirements

1. **Users and auth**: register and log in; passwords hashed with `pwdlib` (argon2); OAuth2
   password flow issuing short-lived JWT access tokens; a `get_current_user` dependency;
   every project/task route requires a valid token. Users can only see their own data.
   Use the schema from `m_20_auth_schema_sessions` (`user`, `session`, `account`,
   `verification`, plus `refresh_token`) as the recommended auth model: Argon2id password
   hashes on the credential `account`, only SHA-256 hashes of session/refresh/verification
   tokens in the database, and rotating refresh tokens with reuse detection.
2. **Projects and tasks (CRUD)**: a user owns many projects; a project has many tasks with
   `title`, `description`, `status` (`todo`/`doing`/`done`), `due_date`, `priority`. Full
   create/read/update/delete with correct status codes (201, 204, 404, 409, 422).
3. **Persistence**: SQLAlchemy 2.0 typed models (`Mapped`, `mapped_column`), an async session
   dependency, Alembic migrations (initial schema plus at least one follow-up migration),
   Postgres in Docker for development and in-memory SQLite for tests.
4. **Pagination and filtering**: `GET /projects/{id}/tasks?status=&priority=&due_before=&q=&limit=&offset=`
   with a stable sort, a `limit` cap, and a response that includes `total`, `limit`, `offset`.
5. **Redis caching**: cache task listings (cache-aside, TTL with jitter, versioned keys that
   include the user id and the query); invalidate on every write; fall back to the database
   if Redis is down. Report cache hit/miss in a response header (e.g. `X-Cache`).
6. **Background notifications**: when a task is assigned or its due date passes, send a
   notification (write to an outbox table or log). Use `BackgroundTasks` for the quick path
   and an arq (or in-process, idempotent, retrying) worker for the overdue-task sweep.
7. **Configuration**: all settings via `pydantic-settings` (`TASKBOARD_` prefix, `SecretStr`
   for secrets, validation that rejects insecure production config); no secrets in git.
8. **Cross-cutting**: request-id middleware, CORS from settings, consistent JSON error
   bodies, a lifespan that opens/closes the DB engine and Redis, `/healthz` and `/readyz`.
9. **Observability**: structured JSON logs carrying the request id; OpenTelemetry tracing with
   `FastAPIInstrumentor` and custom spans around DB and cache calls (console or OTLP exporter
   chosen by env var).
10. **Tests**: pytest suite using `TestClient`/`AsyncClient`, `dependency_overrides` for the DB
    session, current user, and `fakeredis`; coverage of at least 80% (`pytest --cov
    --cov-fail-under=80`), including auth failures, validation errors, pagination edges,
    cache hit/invalidation, and the notification worker.
11. **Containers**: a multi-stage `Dockerfile` (uv, non-root, healthcheck, `.dockerignore`) and
    a `compose.yaml` that starts the API, Postgres, and Redis with healthchecks and
    `depends_on: condition: service_healthy`; migrations run as a separate one-off step.

### Suggested layout

```
capstone_t04/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── Dockerfile
├── .dockerignore
├── compose.yaml
├── .env.example
├── src/taskboard/
│   ├── main.py            # create_app(), lifespan, middleware, routers
│   ├── config.py          # Settings, get_settings
│   ├── db.py              # engine, async_sessionmaker, get_session
│   ├── models.py          # User, Project, Task (SQLAlchemy 2.0)
│   ├── schemas.py         # Pydantic request/response models
│   ├── security.py        # hashing, JWT create/verify, get_current_user
│   ├── cache.py           # Redis client, keys, get_or_set, invalidation
│   ├── tasks.py           # background jobs, arq WorkerSettings
│   ├── observability.py   # JSON logging, OTel setup
│   └── routers/
│       ├── auth.py        # /auth/register, /auth/token
│       ├── projects.py
│       └── tasks.py
└── tests/
    ├── conftest.py        # engine/session, client, fakeredis, auth fixtures
    ├── test_auth.py
    ├── test_projects.py
    ├── test_tasks.py
    ├── test_cache.py
    └── test_worker.py
```

Stretch: WebSocket endpoint pushing live task updates to project members; rate limiting with
Redis; Postgres full-text search on tasks; deploy the compose stack to a small VM or a
managed container service.
