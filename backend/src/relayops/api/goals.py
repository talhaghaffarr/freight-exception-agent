"""Goals queue and analytics resources.

The wire shapes were fixed while these were stubs (Increment 2.5); the frontend
built against them, and this implementation fills the payloads without moving
the envelope. Every number is a read against the goal tables — a zero means
nothing happened, never "not implemented".
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flask import Blueprint, request
from sqlalchemy import text

from relayops.api.deps import current_principal, db, require_login, resolve_tenant
from relayops.domain.goals import GOAL_STATES
from relayops.errors import ValidationFailed, ok
from relayops.seed_history import LIVE_AGENT_TYPES

bp = Blueprint("goals", __name__)

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200

_VALUE_MINUTES_PER_SUCCESS = 4


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.astimezone(UTC).isoformat()


def _subject_label(row) -> str | None:
    """A human-readable subject, derived from the joined stop when it exists."""
    if row.stop_city is None:
        return None
    kind = "Pickup" if row.stop_kind == "pickup" else "Delivery"
    return f"{kind} · {row.stop_city}, {row.stop_state}"


@bp.get("/tenants/<tenant_ref>/goals")
@require_login
def list_goals(tenant_ref: str):
    context = resolve_tenant(tenant_ref, principal=current_principal())

    state = (request.args.get("state") or "").strip() or None
    if state is not None and state not in GOAL_STATES:
        raise ValidationFailed("Unknown goal state.", state=state)
    agent_type = (request.args.get("agent_type") or "").strip() or None
    try:
        limit = int(request.args.get("limit") or _DEFAULT_LIMIT)
    except ValueError as exc:
        raise ValidationFailed("limit must be an integer.") from exc
    limit = max(1, min(limit, _MAX_LIMIT))

    filters = "g.tenant_id = :tenant_id"
    params: dict[str, object] = {"tenant_id": context.tenant_id, "limit": limit}
    if state is not None:
        filters += " and g.state = :state"
        params["state"] = state
    if agent_type is not None:
        filters += " and g.agent_type = :agent_type"
        params["agent_type"] = agent_type

    rows = db().execute(
        text(
            f"""
            select
                g.id, g.agent_type, g.agent_version, g.state, g.terminal_outcome,
                g.opened_at, g.closed_at,
                l.reference,
                s.stop_type as stop_kind, s.city as stop_city, s.state as stop_state
            from goals g
            left join loads l on l.tenant_id = g.tenant_id and l.id = g.load_id
            left join stops s on s.tenant_id = g.tenant_id and s.id = g.subject_id
            where {filters}
            order by g.opened_at desc, g.id
            limit :limit
            """
        ),
        params,
    ).all()

    # The chip counts describe the whole tenant, never the filtered page.
    counts = dict(
        db()
        .execute(
            text("select state, count(*) from goals where tenant_id = :tenant_id group by state"),
            {"tenant_id": context.tenant_id},
        )
        .all()
    )

    return ok(
        [
            {
                "id": str(row.id),
                "reference": row.reference,
                "agent_type": row.agent_type,
                "agent_version": row.agent_version,
                "subject_label": _subject_label(row),
                "state": row.state,
                "terminal_outcome": row.terminal_outcome,
                "opened_at": _iso(row.opened_at),
                "closed_at": _iso(row.closed_at),
            }
            for row in rows
        ],
        meta={"tenant": context.tenant.slug, "counts": counts},
    )


@bp.get("/tenants/<tenant_ref>/agents/catalog")
@require_login
def agent_catalog(tenant_ref: str):
    context = resolve_tenant(tenant_ref, principal=current_principal())

    rows = db().execute(
        text(
            """
            select
                d.agent_type, d.version, d.trigger_kind, d.display_name, d.description,
                coalesce(c.enabled, false) as enabled,
                coalesce(c.config, '{}'::jsonb) as config,
                coalesce(g.goals_7d, 0) as goals_7d,
                coalesce(g.succeeded_7d, 0) as succeeded_7d
            from agent_definitions d
            left join tenant_agent_configs c
                on c.tenant_id = :tenant_id and c.agent_type = d.agent_type
            left join (
                select agent_type,
                       count(*) as goals_7d,
                       count(*) filter (where state = 'succeeded') as succeeded_7d
                from goals
                where tenant_id = :tenant_id
                  and opened_at >= now() - interval '7 days'
                group by agent_type
            ) g on g.agent_type = d.agent_type
            order by d.agent_type
            """
        ),
        {"tenant_id": context.tenant_id},
    ).all()

    return ok(
        [
            {
                "agent_type": row.agent_type,
                "version": row.version,
                "trigger_kind": row.trigger_kind,
                "display_name": row.display_name,
                "description": row.description,
                "live": row.agent_type in LIVE_AGENT_TYPES,
                "enabled": row.enabled,
                "config": row.config,
                "counts": {"goals_7d": row.goals_7d, "succeeded_7d": row.succeeded_7d},
            }
            for row in rows
        ],
        meta={"tenant": context.tenant.slug},
    )


@bp.get("/tenants/<tenant_ref>/analytics/outcomes")
@require_login
def outcome_analytics(tenant_ref: str):
    context = resolve_tenant(tenant_ref, principal=current_principal())

    try:
        days = int(request.args.get("days") or 7)
    except ValueError as exc:
        raise ValidationFailed("days must be an integer.") from exc
    days = max(1, min(days, 30))

    connection = db()
    params = {"tenant_id": context.tenant_id, "days": days}
    window = "opened_at >= now() - make_interval(days => :days)"

    outcome_rows = connection.execute(
        text(
            f"""
            select terminal_outcome as outcome, count(*) as total
            from goals
            where tenant_id = :tenant_id and terminal_outcome is not null and {window}
            group by terminal_outcome
            order by total desc, terminal_outcome
            """
        ),
        params,
    ).all()

    daily_rows = connection.execute(
        text(
            f"""
            select
                date(opened_at at time zone 'UTC') as day,
                count(*) as opened,
                count(*) filter (where state = 'succeeded') as succeeded,
                count(*) filter (where state = 'suppressed') as suppressed
            from goals
            where tenant_id = :tenant_id and {window}
            group by day
            """
        ),
        params,
    ).all()
    by_day = {row.day: row for row in daily_rows}

    # Every calendar date the window touches gets a row, zeros included, so the
    # chart never invents continuity by skipping an empty day.
    today = datetime.now(UTC).date()
    daily = []
    for offset in range(days, -1, -1):
        day = today - timedelta(days=offset)
        row = by_day.get(day)
        daily.append(
            {
                "date": day.isoformat(),
                "opened": row.opened if row else 0,
                "succeeded": row.succeeded if row else 0,
                "suppressed": row.suppressed if row else 0,
            }
        )

    succeeded = sum(row.total for row in outcome_rows if row.outcome == "acted_successfully")

    return ok(
        {
            "outcomes": [
                {"outcome": row.outcome, "count": row.total} for row in outcome_rows
            ],
            "daily": daily,
            "value": {"operator_minutes_saved": _VALUE_MINUTES_PER_SUCCESS * succeeded},
        },
        meta={"tenant": context.tenant.slug, "window_days": days},
    )
