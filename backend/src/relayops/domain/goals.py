"""Agent goal and runtime value objects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

GOAL_STATES = frozenset(
    {
        "opened",
        "collecting_facts",
        "evaluating",
        "action_pending",
        "executing",
        "waiting",
        "needs_review",
        "succeeded",
        "suppressed",
        "failed",
        "expired",
    }
)

TERMINAL_STATES = frozenset({"succeeded", "suppressed", "failed", "expired"})


@dataclass(frozen=True, slots=True)
class Goal:
    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_type: str
    agent_version: str
    subject_type: str
    subject_id: uuid.UUID
    trigger_fingerprint: str
    load_id: uuid.UUID | None
    state: str
    state_version: int
    next_tick_at: datetime | None
    terminal_outcome: str | None
    lease_worker: str | None = None
    lease_expires_at: datetime | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES


@dataclass(frozen=True, slots=True)
class GoalEvent:
    sequence: int
    event_type: str
    from_state: str | None
    to_state: str | None
    detail: dict[str, Any]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OpenGoalRequest:
    tenant_id: uuid.UUID
    agent_type: str
    agent_version: str
    subject_type: str
    subject_id: uuid.UUID
    trigger_fingerprint: str
    load_id: uuid.UUID | None = None
    initial_state: str = "opened"
    detail: dict[str, Any] = field(default_factory=dict)
