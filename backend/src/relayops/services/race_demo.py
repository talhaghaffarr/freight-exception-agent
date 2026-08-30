"""Two scanners racing for one goal, on purpose and in the open.

The console can run this on demand so an operator sees the idempotency
guarantee happen rather than reading a claim about it. Nothing here is
simulated: two threads take two real connections, meet at a barrier, and both
issue the same INSERT. PostgreSQL rejects one of them on
``goals_idempotency_key`` and the loser re-reads the winner's row.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from relayops.domain.goals import OpenGoalRequest
from relayops.repositories.goals import GoalRepository

AGENT_TYPE = "late_pickup"
AGENT_VERSION = "1.0.0"


def trigger_fingerprint(stop_id: uuid.UUID, appointment_revision: int) -> str:
    """Name one trigger episode.

    The appointment revision is part of the key so that rescheduling a pickup
    legitimately opens a new goal, while a redelivered scan of the *same*
    window collapses onto the existing one.
    """
    return f"pickup:{stop_id}:appointment:{appointment_revision}:late:v1"


@dataclass(frozen=True, slots=True)
class ScannerAttempt:
    worker: str
    created: bool
    goal_id: uuid.UUID
    outcome: str
    started_at: datetime
    finished_at: datetime

    @property
    def duration_ms(self) -> float:
        return (self.finished_at - self.started_at).total_seconds() * 1000


@dataclass(frozen=True, slots=True)
class RaceResult:
    reference: str
    trigger_fingerprint: str
    attempts: tuple[ScannerAttempt, ...]
    goals_created: int
    opened_events: int

    @property
    def duplicates_prevented(self) -> int:
        return sum(1 for attempt in self.attempts if not attempt.created)


def _resolve_pickup(engine: Engine, tenant_id: uuid.UUID, reference: str):
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                select p.id as stop_id, p.appointment_revision as revision, l.id as load_id
                from loads l
                join stops p on p.tenant_id = l.tenant_id and p.load_id = l.id
                 and p.stop_type = 'pickup' and p.sequence = 1
                where l.tenant_id = :tenant_id and l.reference = :reference
                """
            ),
            {"tenant_id": tenant_id, "reference": reference},
        ).one_or_none()
    if row is None:
        raise LookupError(f"no pickup stop for {reference} in this tenant")
    return row


def race_scanners(
    engine: Engine,
    tenant_id: uuid.UUID,
    reference: str,
    *,
    workers: int = 2,
    reset: bool = True,
) -> RaceResult:
    """Run ``workers`` scanners concurrently against one trigger.

    ``reset`` clears the goal for this trigger first so the demonstration is
    repeatable. It is a demo affordance and nothing else: the constraint that
    decides the outcome is the same one the scanner relies on in normal
    operation.
    """
    pickup = _resolve_pickup(engine, tenant_id, reference)
    fingerprint = trigger_fingerprint(pickup.stop_id, pickup.revision)

    if reset:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    delete from goals
                    where tenant_id = :tenant_id and agent_type = :agent_type
                      and subject_type = 'stop' and subject_id = :subject_id
                      and trigger_fingerprint = :trigger
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "agent_type": AGENT_TYPE,
                    "subject_id": pickup.stop_id,
                    "trigger": fingerprint,
                },
            )

    request = OpenGoalRequest(
        tenant_id=tenant_id,
        agent_type=AGENT_TYPE,
        agent_version=AGENT_VERSION,
        subject_type="stop",
        subject_id=pickup.stop_id,
        trigger_fingerprint=fingerprint,
        load_id=pickup.load_id,
        detail={"reference": reference, "source": "racing-scanner-demo"},
    )

    # The barrier is what makes this a race rather than a sequence: no thread
    # may issue its INSERT until every thread has arrived.
    barrier = threading.Barrier(workers)
    attempts: list[ScannerAttempt] = []
    lock = threading.Lock()

    def run(index: int) -> None:
        worker = f"scanner-{chr(ord('A') + index)}"
        barrier.wait()
        started = datetime.now(UTC)
        with engine.begin() as connection:
            goal, created = GoalRepository(connection).open_or_get(request)
        finished = datetime.now(UTC)
        attempt = ScannerAttempt(
            worker=worker,
            created=created,
            goal_id=goal.id,
            outcome="inserted" if created else "unique_conflict",
            started_at=started,
            finished_at=finished,
        )
        with lock:
            attempts.append(attempt)

    threads = [threading.Thread(target=run, args=(index,)) for index in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with engine.connect() as connection:
        goals_created = connection.execute(
            text(
                """
                select count(*) from goals
                where tenant_id = :tenant_id and agent_type = :agent_type
                  and subject_id = :subject_id and trigger_fingerprint = :trigger
                """
            ),
            {
                "tenant_id": tenant_id,
                "agent_type": AGENT_TYPE,
                "subject_id": pickup.stop_id,
                "trigger": fingerprint,
            },
        ).scalar_one()
        opened_events = connection.execute(
            text(
                """
                select count(*) from goal_events e
                join goals g on g.id = e.goal_id
                where g.tenant_id = :tenant_id and g.subject_id = :subject_id
                  and g.trigger_fingerprint = :trigger and e.event_type = 'opened'
                """
            ),
            {
                "tenant_id": tenant_id,
                "subject_id": pickup.stop_id,
                "trigger": fingerprint,
            },
        ).scalar_one()

    attempts.sort(key=lambda item: item.worker)
    return RaceResult(
        reference=reference,
        trigger_fingerprint=fingerprint,
        attempts=tuple(attempts),
        goals_created=goals_created,
        opened_events=opened_events,
    )
