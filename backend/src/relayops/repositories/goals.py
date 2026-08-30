"""Goal persistence: conflict-safe opening, version-checked transitions, leases.

The two hardest correctness properties in the whole system live here:

- ``open_or_get`` collapses racing scanners onto one goal via
  ``INSERT ... ON CONFLICT DO NOTHING RETURNING``, appending the opened event
  only on the insert path.
- ``transition`` moves a goal forward only if the caller's ``state_version``
  still matches, and writes the new state, next tick, and one appended event in
  the same transaction. A stale version is a retryable concurrency signal.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, text

from relayops.domain.goals import Goal, GoalEvent, OpenGoalRequest

_GOAL_COLUMNS = """
    id, tenant_id, agent_type, agent_version, subject_type, subject_id,
    trigger_fingerprint, load_id, state, state_version, next_tick_at,
    terminal_outcome, lease_worker, lease_expires_at, opened_at, closed_at
"""


class ConcurrencyConflict(RuntimeError):
    """The goal advanced under us; the caller should re-read and retry."""


def _to_goal(row) -> Goal:
    return Goal(
        id=row.id,
        tenant_id=row.tenant_id,
        agent_type=row.agent_type,
        agent_version=row.agent_version,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        trigger_fingerprint=row.trigger_fingerprint,
        load_id=row.load_id,
        state=row.state,
        state_version=row.state_version,
        next_tick_at=row.next_tick_at,
        terminal_outcome=row.terminal_outcome,
        lease_worker=row.lease_worker,
        lease_expires_at=row.lease_expires_at,
        opened_at=row.opened_at,
        closed_at=row.closed_at,
    )


@dataclass(frozen=True, slots=True)
class Transition:
    to_state: str
    event_type: str
    detail: dict[str, Any]
    next_tick_at: datetime | None = None
    terminal_outcome: str | None = None
    clear_lease: bool = False


class GoalRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(self, goal_id: uuid.UUID) -> Goal | None:
        row = self._connection.execute(
            text(f"select {_GOAL_COLUMNS} from goals where id = :id"), {"id": goal_id}
        ).one_or_none()
        return _to_goal(row) if row else None

    def open_or_get(self, request: OpenGoalRequest) -> tuple[Goal, bool]:
        """Return ``(goal, created)``. Racing callers converge on one row."""
        inserted = self._connection.execute(
            text(
                f"""
                insert into goals (
                    tenant_id, agent_type, agent_version, subject_type, subject_id,
                    trigger_fingerprint, load_id, state, next_tick_at
                ) values (
                    :tenant_id, :agent_type, :agent_version, :subject_type, :subject_id,
                    :trigger, :load_id, :state, now()
                )
                on conflict (tenant_id, agent_type, subject_type, subject_id, trigger_fingerprint)
                do nothing
                returning {_GOAL_COLUMNS}
                """
            ),
            {
                "tenant_id": request.tenant_id,
                "agent_type": request.agent_type,
                "agent_version": request.agent_version,
                "subject_type": request.subject_type,
                "subject_id": request.subject_id,
                "trigger": request.trigger_fingerprint,
                "load_id": request.load_id,
                "state": request.initial_state,
            },
        ).one_or_none()

        if inserted is not None:
            goal = _to_goal(inserted)
            self._append_event(
                goal,
                sequence=1,
                event_type="opened",
                from_state=None,
                to_state=goal.state,
                detail=request.detail,
            )
            return goal, True

        # Lost the race: the row exists. Re-read by the same complete key.
        existing = self._connection.execute(
            text(
                f"""
                select {_GOAL_COLUMNS} from goals
                where tenant_id = :tenant_id and agent_type = :agent_type
                  and subject_type = :subject_type and subject_id = :subject_id
                  and trigger_fingerprint = :trigger
                """
            ),
            {
                "tenant_id": request.tenant_id,
                "agent_type": request.agent_type,
                "subject_type": request.subject_type,
                "subject_id": request.subject_id,
                "trigger": request.trigger_fingerprint,
            },
        ).one()
        return _to_goal(existing), False

    def transition(
        self, goal_id: uuid.UUID, expected_version: int, transition: Transition
    ) -> Goal:
        """Advance a goal if its version is unchanged; otherwise raise."""
        closed = transition.terminal_outcome is not None
        updated = self._connection.execute(
            text(
                f"""
                update goals set
                    state = :to_state,
                    state_version = state_version + 1,
                    next_tick_at = :next_tick_at,
                    terminal_outcome = coalesce(:terminal_outcome, terminal_outcome),
                    lease_worker = case when :clear_lease then null else lease_worker end,
                    lease_expires_at = case when :clear_lease then null else lease_expires_at end,
                    closed_at = case when :closed then now() else closed_at end,
                    updated_at = now()
                where id = :goal_id and state_version = :expected_version
                returning {_GOAL_COLUMNS}
                """
            ),
            {
                "goal_id": goal_id,
                "expected_version": expected_version,
                "to_state": transition.to_state,
                "next_tick_at": transition.next_tick_at,
                "terminal_outcome": transition.terminal_outcome,
                "clear_lease": transition.clear_lease,
                "closed": closed,
            },
        ).one_or_none()

        if updated is None:
            raise ConcurrencyConflict(
                f"goal {goal_id} was not at version {expected_version}"
            )

        goal = _to_goal(updated)
        next_sequence = self._next_sequence(goal_id)
        self._append_event(
            goal,
            sequence=next_sequence,
            event_type=transition.event_type,
            from_state=None,
            to_state=transition.to_state,
            detail=transition.detail,
        )
        return goal

    def events(self, goal_id: uuid.UUID) -> list[GoalEvent]:
        rows = self._connection.execute(
            text(
                "select sequence, event_type, from_state, to_state, detail, occurred_at "
                "from goal_events where goal_id = :id order by sequence"
            ),
            {"id": goal_id},
        ).all()
        return [
            GoalEvent(
                sequence=row.sequence,
                event_type=row.event_type,
                from_state=row.from_state,
                to_state=row.to_state,
                detail=row.detail,
                occurred_at=row.occurred_at,
            )
            for row in rows
        ]

    def save_fact_snapshot(
        self, goal: Goal, version: int, content: dict[str, Any]
    ) -> str:
        payload = json.dumps(content, sort_keys=True, default=str)
        content_hash = hashlib.sha256(payload.encode()).hexdigest()
        self._connection.execute(
            text(
                "insert into fact_snapshots (tenant_id, goal_id, version, content, content_hash) "
                "values (:t, :g, :v, cast(:content as jsonb), :hash) "
                "on conflict (goal_id, version) do nothing"
            ),
            {
                "t": goal.tenant_id,
                "g": goal.id,
                "v": version,
                "content": payload,
                "hash": content_hash,
            },
        )
        return content_hash

    def _next_sequence(self, goal_id: uuid.UUID) -> int:
        return (
            self._connection.execute(
                text("select coalesce(max(sequence), 0) + 1 from goal_events where goal_id = :id"),
                {"id": goal_id},
            ).scalar_one()
        )

    def _append_event(
        self,
        goal: Goal,
        *,
        sequence: int,
        event_type: str,
        from_state: str | None,
        to_state: str | None,
        detail: dict[str, Any],
    ) -> None:
        self._connection.execute(
            text(
                "insert into goal_events "
                "(tenant_id, goal_id, sequence, event_type, from_state, to_state, detail) "
                "values (:t, :g, :seq, :etype, :from_state, :to_state, cast(:detail as jsonb))"
            ),
            {
                "t": goal.tenant_id,
                "g": goal.id,
                "seq": sequence,
                "etype": event_type,
                "from_state": from_state,
                "to_state": to_state,
                "detail": json.dumps(detail, default=str),
            },
        )
