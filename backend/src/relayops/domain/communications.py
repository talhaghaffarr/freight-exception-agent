"""Action and delivery value objects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ActionState = Literal[
    "pending", "executing", "succeeded", "delivery_unknown", "retry_scheduled", "failed"
]


@dataclass(frozen=True, slots=True)
class Action:
    id: uuid.UUID
    tenant_id: uuid.UUID
    goal_id: uuid.UUID
    action_kind: str
    recipient: str
    recipient_fingerprint: str
    action_fingerprint: str
    idempotency_key: str
    state: ActionState
    subject: str | None = None
    body_preview: str | None = None
    template_key: str | None = None
    template_version: str | None = None


@dataclass(frozen=True, slots=True)
class ActionAttempt:
    attempt: int
    provider: str
    provider_message_id: str | None
    result_class: str
    detail: dict[str, Any]
    attempted_at: datetime


@dataclass(frozen=True, slots=True)
class ActionRequest:
    action_kind: str
    recipient: str
    recipient_fingerprint: str
    action_fingerprint: str
    subject: str
    body_html: str
    body_text: str
    template_key: str
    template_version: str
    headers: dict[str, str] = field(default_factory=dict)
