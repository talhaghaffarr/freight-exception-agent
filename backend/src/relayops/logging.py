"""Structured logging configuration.

Log records carry the correlation fields the operations console needs to tie a
message back to a request, task, tenant, goal, and outcome. Secrets and raw
contact details are redacted before a record is emitted.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(password|secret|token|api[_-]?key)=\S+"), r"\1=[redacted]"),
    (re.compile(r"://([^:/@\s]+):([^@\s]+)@"), r"://\1:[redacted]@"),
)

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "secret_key",
        "token",
        "api_key",
        "authorization",
        "openai_api_key",
        "sendgrid_api_key",
        "twilio_auth_token",
    }
)


def redact(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key, value in list(event_dict.items()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[redacted]"
        elif isinstance(value, str):
            for pattern, replacement in _REDACTIONS:
                value = pattern.sub(replacement, value)
            event_dict[key] = value
    return event_dict


def configure_logging(*, service: str, json_output: bool = True, level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service)


def get_logger(name: str = "relayops"):
    return structlog.get_logger(name)
