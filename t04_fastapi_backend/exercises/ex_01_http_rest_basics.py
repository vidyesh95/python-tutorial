"""Exercise 01: HTTP and REST basics.

Tasks
1. status_class: map a numeric status code to its family name.
2. method_properties: say whether an HTTP method is safe and idempotent.
3. build_url: build a REST URL like "/books/42?limit=5" from parts.
4. parse_bearer: pull the token out of an `Authorization: Bearer <token>` header.
5. fetch_json: call an API with an httpx.Client; return JSON or raise ApiError.

Run: uv run pytest t04_fastapi_backend -k ex_01
"""

from urllib.parse import urlencode  # noqa: F401  (handy for build_url)

import httpx


class ApiError(Exception):
    """Raised by fetch_json on a 4xx/5xx response. (Already written for you.)"""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


def status_class(code: int) -> str:
    """Return 'informational' (1xx), 'success' (2xx), 'redirect' (3xx),
    'client_error' (4xx) or 'server_error' (5xx). Raise ValueError otherwise.

    >>> status_class(201)
    'success'
    """
    raise NotImplementedError


def method_properties(method: str) -> dict[str, bool]:
    """Return {"safe": ..., "idempotent": ...} for a method (case-insensitive).

    GET/HEAD/OPTIONS: safe and idempotent. PUT/DELETE: idempotent, not safe.
    POST/PATCH: neither. Raise ValueError for unknown methods.
    """
    raise NotImplementedError


def build_url(resource: str, item_id: int | None = None, **query: object) -> str:
    """Build '/<resource>[/<item_id>][?<query>]'. Skip query params whose value is None.

    >>> build_url("books", 42, limit=5)
    '/books/42?limit=5'
    >>> build_url("books", q=None)
    '/books'
    """
    raise NotImplementedError


def parse_bearer(header: str | None) -> str | None:
    """Return the token from 'Bearer <token>' (scheme is case-insensitive).

    Return None if the header is missing, uses another scheme, or has no token.
    """
    raise NotImplementedError


def fetch_json(client: httpx.Client, path: str) -> object:
    """GET `path` and return the decoded JSON body.

    On status >= 400 raise ApiError(status_code, detail) where detail is the JSON
    body's "detail" field if present, else the response text.
    """
    raise NotImplementedError
