# Background Tasks
"""
Some work does not need to finish before the client gets an answer: sending a welcome email,
writing an audit row, warming a cache. FastAPI's `BackgroundTasks` runs a function AFTER the
response has been sent, in the same process.

    @app.post("/signup", status_code=202)
    def signup(user: NewUser, background_tasks: BackgroundTasks):
        background_tasks.add_task(send_welcome, user.email)   # (callable, *args, **kwargs)
        return {"status": "accepted"}

How it works
- `add_task` only registers the call. Starlette runs it once the response body is sent.
- `def` tasks run in the threadpool; `async def` tasks run on the event loop (never block it).
- Tasks added to the injected `BackgroundTasks` are shared with dependencies, so a dependency
  can schedule work too.
- An exception in a task happens AFTER the 2xx was sent: the client never sees it. Catch and
  log inside the task.
- In tests, `TestClient` waits for background tasks before `client.post()` returns.

Run live:  uv run fastapi dev t04_fastapi_backend/m_11_background_tasks.py

Common mistakes
- Treating BackgroundTasks as a durable queue. If the process restarts, queued work is lost.
- Doing CPU-heavy work in a task: it still competes with request handling in this process.
- Relying on request-scoped objects (DB session, `Request`) inside the task; they may be
  closed by then. Pass plain values (ids, emails) and open your own resources.
- Letting an exception escape and getting only a stack trace in the server log.

Production notes
- Use BackgroundTasks for small, fast, best-effort work (< a few seconds, OK to lose).
- Move to a real queue (arq, Celery, see m_16) when you need retries, durability, scheduling,
  rate limiting, a separate worker fleet, or visibility into job status.
- Return 202 Accepted for "work started", and give clients a way to check status later.
"""

import logging
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

logger = logging.getLogger("m_11")
app = FastAPI(title="Background tasks")

# Stand-ins for "the outside world" so the demo is observable and offline.
OUTBOX: list[dict[str, str]] = []
AUDIT: list[str] = []
FAILURES: list[str] = []


class NewUser(BaseModel):
    email: str


# Example: the tasks themselves are ordinary functions
def send_welcome(email: str) -> None:
    if "@" not in email:
        raise ValueError(f"bad address: {email!r}")
    OUTBOX.append({"to": email, "subject": "Welcome!"})


def safe_send_welcome(email: str) -> None:
    """Wrap the task: nobody is listening after the response, so handle errors here."""
    try:
        send_welcome(email)
    except Exception as exc:  # last line of defence for background work
        logger.warning("welcome email failed: %s", exc)  # use logger.exception for a traceback
        FAILURES.append(f"{email}: {exc}")


# Example: a dependency can add tasks to the SAME BackgroundTasks instance
def audit_request(background_tasks: BackgroundTasks) -> None:
    background_tasks.add_task(AUDIT.append, "signup requested")


@app.post("/signup", status_code=202)
def signup(
    user: NewUser,
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(audit_request)],
) -> dict[str, str]:
    background_tasks.add_task(safe_send_welcome, user.email)
    return {"status": "accepted", "email": user.email}


# Example: async tasks run on the event loop, so only await non-blocking things
async def async_ping(url: str) -> None:
    AUDIT.append(f"pinged {url}")  # imagine `await httpx_client.post(url)`


@app.post("/webhook", status_code=202)
async def webhook(background_tasks: BackgroundTasks) -> dict[str, str]:
    background_tasks.add_task(async_ping, "https://hooks.example.com")
    return {"status": "queued"}


if __name__ == "__main__":
    client = TestClient(app)

    r = client.post("/signup", json={"email": "ada@example.com"})
    print(r.status_code, r.json())
    print("outbox:", OUTBOX)  # the task already ran: TestClient waits for it
    print("audit:", AUDIT)

    # A failing task does NOT change the response; it is recorded by our own handler.
    r = client.post("/signup", json={"email": "not-an-email"})
    print(r.status_code, r.json())
    print("failures:", FAILURES)

    print(client.post("/webhook").json(), AUDIT[-1])
