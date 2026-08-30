"""Live operations resources: the board, one load's decision, and the race demo.

Every response is tenant-scoped through :func:`resolve_tenant`, so a caller who
is not a member of the tenant gets the same 404 a caller naming a non-existent
tenant gets.
"""

from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, request

from relayops.api.deps import current_principal, db, get_engine, require_login, resolve_tenant
from relayops.errors import NotFound, ok
from relayops.facts.late_pickup import LatePickupFacts
from relayops.repositories.goals import GoalRepository
from relayops.services.board import BoardRow, load_board
from relayops.services.race_demo import race_scanners

bp = Blueprint("operations", __name__)


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.astimezone(UTC).isoformat()


def _facts_json(facts: LatePickupFacts) -> dict:
    """Serialise facts without ever emitting a placeholder for an unknown.

    ``eta`` is null when it could not be computed and ``reason`` says why, so a
    client cannot accidentally render an empty string as a real arrival time.
    """
    return {
        "classification": facts.classification,
        "minutes_late": facts.minutes_late,
        "threshold_minutes": facts.threshold_minutes,
        "reason": facts.reason,
        "appointment_start": _iso(facts.appointment_start),
        "appointment_revision": facts.appointment_revision,
        "tracking_freshness": (
            None if facts.tracking_freshness is None else facts.tracking_freshness.value
        ),
        "evidence_at": _iso(facts.evidence_at),
        "position": (
            None
            if facts.latest_position is None
            else {"latitude": facts.latest_position[0], "longitude": facts.latest_position[1]}
        ),
        "eta": {
            "available": facts.eta.available,
            "predicted_arrival": _iso(facts.eta.predicted_arrival),
            "reason": facts.eta.reason,
            "source": facts.eta.source,
            "traffic_assumption": facts.eta.traffic_assumption,
            "remaining_meters": facts.eta.remaining_meters,
        },
    }


def _row_json(row: BoardRow) -> dict:
    return {
        "load_id": str(row.load_id),
        "reference": row.reference,
        "customer_name": row.customer_name,
        "carrier_name": row.carrier_name,
        "driver_name": row.driver_name,
        "origin": row.origin,
        "destination": row.destination,
        "pickup_appointment": _iso(row.pickup_appointment),
        "facts": _facts_json(row.facts),
    }


def _summary(board: list[BoardRow]) -> dict:
    """The counters on the board header.

    ``needs_action`` deliberately includes unknowns: a load we cannot see needs
    a human as much as one we can see is late.
    """
    counts = {"late": 0, "at_risk": 0, "unknown": 0, "on_time": 0, "early": 0}
    for row in board:
        counts[row.facts.classification] = counts.get(row.facts.classification, 0) + 1
    return {
        "active_loads": len(board),
        "needs_action": counts["late"] + counts["unknown"],
        "late_pickup": counts["late"],
        "at_risk": counts["at_risk"],
        "no_signal": counts["unknown"],
        "on_track": counts["on_time"] + counts["early"],
    }


@bp.get("/tenants/<tenant_ref>/loads")
@require_login
def list_loads(tenant_ref: str):
    context = resolve_tenant(tenant_ref, principal=current_principal())
    board = load_board(db(), context.tenant_id)
    return ok(
        [_row_json(row) for row in board],
        meta={
            "tenant": context.tenant.slug,
            "summary": _summary(board),
            "generated_at": _iso(datetime.now(UTC)),
        },
    )


@bp.get("/tenants/<tenant_ref>/loads/<reference>")
@require_login
def read_load(tenant_ref: str, reference: str):
    context = resolve_tenant(tenant_ref, principal=current_principal())
    board = load_board(db(), context.tenant_id)
    match = next((row for row in board if row.reference == reference), None)
    if match is None:
        raise NotFound()

    stop = match.view.first_incomplete_pickup()
    goals = GoalRepository(db()).for_subject(context.tenant_id, stop.id) if stop else []

    return ok(
        {
            **_row_json(match),
            "account_manager": {
                "name": match.view.load.account_manager_name,
                "email": match.view.load.account_manager_email,
            },
            "pickup_facility": None if stop is None else stop.facility_name,
            "goals": [
                {
                    "id": str(goal.id),
                    "state": goal.state,
                    "agent_type": goal.agent_type,
                    "agent_version": goal.agent_version,
                    "trigger_fingerprint": goal.trigger_fingerprint,
                    "terminal_outcome": goal.terminal_outcome,
                    "opened_at": _iso(goal.opened_at),
                }
                for goal in goals
            ],
        },
        meta={"tenant": context.tenant.slug},
    )


@bp.post("/tenants/<tenant_ref>/demo/race")
@require_login
def run_race(tenant_ref: str):
    """Race two scanners for one trigger and report what the database did."""
    context = resolve_tenant(tenant_ref, principal=current_principal())
    payload = request.get_json(silent=True) or {}
    reference = str(payload.get("reference") or "LD-1048")
    workers = min(max(int(payload.get("workers") or 2), 2), 4)

    try:
        result = race_scanners(get_engine(), context.tenant_id, reference, workers=workers)
    except LookupError as exc:
        raise NotFound() from exc

    return ok(
        {
            "reference": result.reference,
            "trigger_fingerprint": result.trigger_fingerprint,
            "goals_created": result.goals_created,
            "opened_events": result.opened_events,
            "duplicates_prevented": result.duplicates_prevented,
            "constraint": "goals_idempotency_key",
            "attempts": [
                {
                    "worker": attempt.worker,
                    "created": attempt.created,
                    "outcome": attempt.outcome,
                    "goal_id": str(attempt.goal_id),
                    "duration_ms": round(attempt.duration_ms, 2),
                }
                for attempt in result.attempts
            ],
        },
        meta={"tenant": context.tenant.slug},
    )


@bp.get("/tenants/<tenant_ref>/goals/<goal_id>/trace")
@require_login
def read_trace(tenant_ref: str, goal_id: str):
    import uuid as _uuid

    context = resolve_tenant(tenant_ref, principal=current_principal())
    try:
        parsed = _uuid.UUID(goal_id)
    except ValueError as exc:
        raise NotFound() from exc

    repository = GoalRepository(db())
    goal = repository.get(parsed)
    # Scope is checked against the resolved tenant, never against the path.
    if goal is None or goal.tenant_id != context.tenant_id:
        raise NotFound()

    return ok(
        {
            "goal": {
                "id": str(goal.id),
                "state": goal.state,
                "agent_type": goal.agent_type,
                "agent_version": goal.agent_version,
                "trigger_fingerprint": goal.trigger_fingerprint,
                "terminal_outcome": goal.terminal_outcome,
                "opened_at": _iso(goal.opened_at),
            },
            "events": [
                {
                    "sequence": event.sequence,
                    "event_type": event.event_type,
                    "from_state": event.from_state,
                    "to_state": event.to_state,
                    "detail": event.detail,
                    "occurred_at": _iso(event.occurred_at),
                }
                for event in repository.events(goal.id)
            ],
        },
        meta={"tenant": context.tenant.slug},
    )
