from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
_MAX_REQUEST_ID_LENGTH = 64
_REQUEST_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def _generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())


def _sanitize_request_id(value: str | None) -> str:
    """Validate an incoming request ID or generate a fresh one."""
    if value is None:
        return _generate_request_id()

    if len(value) > _MAX_REQUEST_ID_LENGTH or not _REQUEST_ID_RE.match(value):
        return _generate_request_id()

    return value


async def add_request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Attach a request ID to each incoming request for log correlation."""
    request_id = _sanitize_request_id(request.headers.get(REQUEST_ID_HEADER))
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
