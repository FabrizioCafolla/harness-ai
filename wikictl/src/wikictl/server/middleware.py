"""ASGI middleware for request logging and correlation IDs."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that adds correlation IDs and logs request lifecycle."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        log = structlog.get_logger("wikictl.server")
        log.info("request_started", method=request.method, path=request.url.path)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000)

        response.headers["X-Request-ID"] = request_id
        log.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        structlog.contextvars.clear_contextvars()
        return response
