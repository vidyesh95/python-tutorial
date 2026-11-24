"""Reference solution for Exercise 01: HTTP and REST basics."""

from urllib.parse import urlencode

import httpx


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


def status_class(code: int) -> str:
    names = {
        1: "informational",
        2: "success",
        3: "redirect",
        4: "client_error",
        5: "server_error",
    }
    try:
        return names[code // 100]
    except KeyError:
        raise ValueError(f"invalid status code: {code}") from None


def method_properties(method: str) -> dict[str, bool]:
    table = {
        "GET": (True, True),
        "HEAD": (True, True),
        "OPTIONS": (True, True),
        "PUT": (False, True),
        "DELETE": (False, True),
        "POST": (False, False),
        "PATCH": (False, False),
    }
    try:
        safe, idempotent = table[method.upper()]
    except KeyError:
        raise ValueError(f"unknown method: {method}") from None
    return {"safe": safe, "idempotent": idempotent}


def build_url(resource: str, item_id: int | None = None, **query: object) -> str:
    url = f"/{resource}"
    if item_id is not None:
        url += f"/{item_id}"
    params = {k: v for k, v in query.items() if v is not None}
    if params:
        url += "?" + urlencode(params)
    return url


def parse_bearer(header: str | None) -> str | None:
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def fetch_json(client: httpx.Client, path: str) -> object:
    response = client.get(path)
    if response.status_code >= 400:
        try:
            detail = response.json()["detail"]
        except ValueError, KeyError, TypeError:
            detail = response.text
        raise ApiError(response.status_code, str(detail))
    return response.json()
