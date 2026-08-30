"""Stable error codes and the versioned JSON envelope.

Every API response — success or failure — is shaped as ``{data, meta, error}``.
Tenant-facing messages never carry internal exception text or cross-tenant
identifiers; the correlating ``request_id`` is how an operator ties a user
report back to the structured logs.
"""

from __future__ import annotations

import secrets
from typing import Any

from flask import g, has_request_context, jsonify
from werkzeug.exceptions import HTTPException

_HTTP_CODE_NAMES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "UNPROCESSABLE",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "UPSTREAM_ERROR",
    503: "DEPENDENCY_UNAVAILABLE",
}

_SAFE_HTTP_MESSAGES = {
    400: "The request could not be understood.",
    401: "Authentication is required.",
    403: "This account cannot access that resource.",
    404: "The requested resource does not exist.",
    405: "That method is not allowed on this resource.",
    409: "The request conflicts with the current state.",
    422: "The request failed validation.",
    429: "Too many requests. Try again shortly.",
    500: "An unexpected error occurred.",
    503: "A required dependency is unavailable.",
}


class ApiError(Exception):
    """An error that is safe to render to an API caller."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}


class NotFound(ApiError):
    def __init__(self, message: str = "The requested resource does not exist.", **details: Any):
        super().__init__("NOT_FOUND", message, 404, details or None)


class Forbidden(ApiError):
    def __init__(self, message: str = "This account cannot access that resource.", **details: Any):
        super().__init__("FORBIDDEN", message, 403, details or None)


class Unauthenticated(ApiError):
    def __init__(self, message: str = "Authentication is required.", **details: Any):
        super().__init__("UNAUTHENTICATED", message, 401, details or None)


class ValidationFailed(ApiError):
    def __init__(self, message: str = "The request failed validation.", **details: Any):
        super().__init__("VALIDATION_FAILED", message, 422, details or None)


def new_request_id() -> str:
    """Sortable-enough, collision-resistant correlation id."""
    return f"req_{secrets.token_hex(12)}"


def current_request_id() -> str:
    if has_request_context():
        request_id = getattr(g, "request_id", None)
        if request_id:
            return str(request_id)
    return new_request_id()


def envelope(
    data: Any = None,
    *,
    meta: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body_meta = {"request_id": current_request_id()}
    if meta:
        body_meta.update(meta)
    return {"data": data, "meta": body_meta, "error": error}


def ok(data: Any = None, *, meta: dict[str, Any] | None = None, status: int = 200):
    response = jsonify(envelope(data, meta=meta))
    response.status_code = status
    return response


def error_response(
    code: str,
    message: str,
    status: int,
    details: dict[str, Any] | None = None,
):
    body = envelope(
        None,
        error={"code": code, "message": message, "details": details or {}},
    )
    response = jsonify(body)
    response.status_code = status
    return response


def render_api_error(exc: ApiError):
    return error_response(exc.code, exc.message, exc.http_status, exc.details)


def render_http_exception(exc: HTTPException):
    status = exc.code or 500
    return error_response(
        _HTTP_CODE_NAMES.get(status, "HTTP_ERROR"),
        _SAFE_HTTP_MESSAGES.get(status, "The request could not be completed."),
        status,
    )


def render_unexpected_error():
    """Never echo the original exception; operators correlate by request id."""
    return error_response(
        "INTERNAL_ERROR",
        _SAFE_HTTP_MESSAGES[500],
        500,
        {"request_id": current_request_id()},
    )
