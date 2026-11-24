"""Exercise 11: Background Tasks.

Tasks
1. send_welcome: append a message to OUTBOX (and reject bad addresses).
2. safe_send_welcome: a background-safe wrapper that records errors instead of raising.
3. write_audit: append an audit line to AUDIT.
4. register: the route handler. Respond 202 immediately and schedule BOTH background jobs.

Run: uv run pytest t04_fastapi_backend -k background_tasks
"""

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

OUTBOX: list[dict[str, str]] = []
AUDIT: list[str] = []
FAILURES: list[str] = []

app = FastAPI()


class Registration(BaseModel):
    email: str


def send_welcome(email: str) -> None:
    """Append {"to": email, "subject": "Welcome"} to OUTBOX.

    Raise ValueError if "@" is not in the address (and append nothing).
    """
    raise NotImplementedError


def safe_send_welcome(email: str) -> None:
    """Call send_welcome(email). If it raises, never propagate: append
    f"{email}: {exc}" to FAILURES instead.
    """
    raise NotImplementedError


def write_audit(email: str) -> None:
    """Append f"registered:{email}" to AUDIT."""
    raise NotImplementedError


@app.post("/register", status_code=202)
def register(payload: Registration, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Schedule write_audit then safe_send_welcome (use add_task) and return
    {"status": "accepted"}. Do not call them directly.
    """
    raise NotImplementedError
