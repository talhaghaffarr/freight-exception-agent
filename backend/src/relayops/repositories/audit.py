"""Append-only audit history.

There is intentionally no update or delete function in this module. Reviewers
depend on configuration history being complete.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from flask import g, has_request_context
from sqlalchemy import Connection, text

from relayops.domain.identity import Principal


def record_audit_event(
    connection: Connection,
    *,
    tenant_id: uuid.UUID | None,
    actor: Principal | None,
    action: str,
    subject_type: str,
    subject_id: str | None = None,
    reason: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    actor_label: str | None = None,
) -> int:
    request_id = None
    if has_request_context():
        request_id = getattr(g, "request_id", None)

    return connection.execute(
        text(
            """
            insert into audit_events
                (tenant_id, actor_user_id, actor_label, action, subject_type, subject_id,
                 reason, old_value, new_value, request_id)
            values
                (:tenant_id, :actor_user_id, :actor_label, :action, :subject_type, :subject_id,
                 :reason, cast(:old_value as jsonb), cast(:new_value as jsonb), :request_id)
            returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "actor_user_id": actor.user.id if actor else None,
            "actor_label": actor_label or (actor.user.email if actor else "system"),
            "action": action,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "reason": reason,
            "old_value": json.dumps(old_value) if old_value is not None else None,
            "new_value": json.dumps(new_value) if new_value is not None else None,
            "request_id": request_id,
        },
    ).scalar_one()
