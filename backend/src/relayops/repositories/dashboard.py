"""Fleet overview aggregation.

The shape is stable from the first commit: a screen that has to guess whether a
section exists cannot be trusted. Counts are real reads, so a zero here means
"nothing happened", never "not implemented".
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, text

#: The value convention shared with the analytics endpoint: one avoided manual
#: touch per successfully acted goal, four minutes each.
MINUTES_SAVED_PER_SUCCESS = 4

_RECENT_ACTIVITY_LIMIT = 8


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    agents: list[dict[str, Any]] = field(default_factory=list)
    goals: dict[str, int] = field(
        default_factory=lambda: {"opened": 0, "waiting": 0, "needs_review": 0, "failed": 0}
    )
    communications: dict[str, int] = field(
        default_factory=lambda: {"email": 0, "sms": 0, "voice": 0}
    )
    value: dict[str, int] = field(default_factory=lambda: {"operator_minutes_saved": 0})
    recent_activity: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _table_exists(connection: Connection, name: str) -> bool:
    return bool(
        connection.execute(
            text("select to_regclass(:name) is not null"), {"name": f"public.{name}"}
        ).scalar()
    )


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.astimezone(UTC).isoformat()


def _activity_summary(row: Any) -> str:
    """Operator language, not enum values: the overview renders this verbatim."""
    name = row.display_name or row.agent_type.replace("_", " ").title()
    event = row.event_type.replace("_", " ").capitalize()
    state = f" → {row.to_state.replace('_', ' ')}" if row.to_state else ""
    reference = f" · {row.reference}" if row.reference else ""
    return f"{name} · {event}{state}{reference}"


def load_dashboard(
    connection: Connection, tenant_ids: list[uuid.UUID] | None
) -> DashboardSummary:
    """Aggregate for one tenant, or across every tenant when ``tenant_ids`` is None.

    The query degrades to zeros rather than failing while the goal tables do
    not exist, which keeps the contract stable on a half-migrated database.
    """
    if not _table_exists(connection, "goals"):
        return DashboardSummary()

    scope_clause = "" if tenant_ids is None else " where tenant_id = any(:tenant_ids)"
    params: dict[str, Any] = {} if tenant_ids is None else {"tenant_ids": tenant_ids}

    goals = connection.execute(
        text(
            f"""
            select
                count(*) filter (
                    where state not in ('succeeded', 'failed', 'expired', 'suppressed')
                ) as opened,
                count(*) filter (where state = 'waiting') as waiting,
                count(*) filter (where state = 'needs_review') as needs_review,
                count(*) filter (where state = 'failed') as failed,
                count(*) filter (where terminal_outcome = 'acted_successfully') as succeeded
            from goals{scope_clause}
            """
        ),
        params,
    ).one()

    agent_scope = "" if tenant_ids is None else " where c.tenant_id = any(:tenant_ids)"
    agents = connection.execute(
        text(
            f"""
            select
                c.agent_type,
                c.enabled,
                t.slug as tenant_slug,
                coalesce(d.version, '—') as version,
                coalesce(g.goals_open, 0) as goals_open,
                g.success_rate
            from tenant_agent_configs c
            join tenants t on t.id = c.tenant_id
            left join lateral (
                select version from agent_definitions d
                where d.agent_type = c.agent_type
                order by d.version desc limit 1
            ) d on true
            left join lateral (
                select
                    count(*) filter (
                        where state not in ('succeeded', 'failed', 'expired', 'suppressed')
                    ) as goals_open,
                    case when count(*) filter (where terminal_outcome is not null) = 0
                        then null
                        else count(*) filter (where terminal_outcome = 'acted_successfully')
                            / count(*) filter (where terminal_outcome is not null)::float
                    end as success_rate
                from goals g
                where g.tenant_id = c.tenant_id and g.agent_type = c.agent_type
            ) g on true
            {agent_scope}
            order by t.slug, c.agent_type
            """
        ),
        params,
    ).all()

    event_scope = "" if tenant_ids is None else " where e.tenant_id = any(:tenant_ids)"
    activity = connection.execute(
        text(
            f"""
            select
                e.id, e.event_type, e.to_state, e.occurred_at, e.goal_id,
                g.agent_type, l.reference, d.display_name
            from goal_events e
            join goals g on g.id = e.goal_id
            left join loads l on l.tenant_id = g.tenant_id and l.id = g.load_id
            left join lateral (
                select display_name from agent_definitions d
                where d.agent_type = g.agent_type
                order by d.version desc limit 1
            ) d on true
            {event_scope}
            order by e.occurred_at desc, e.id desc
            limit :activity_limit
            """
        ),
        {**params, "activity_limit": _RECENT_ACTIVITY_LIMIT},
    ).all()

    return DashboardSummary(
        agents=[
            {
                "agent_type": row.agent_type,
                "version": row.version,
                "tenant_slug": row.tenant_slug,
                "enabled": row.enabled,
                "goals_open": row.goals_open,
                "success_rate": row.success_rate,
            }
            for row in agents
        ],
        goals={
            "opened": goals.opened,
            "waiting": goals.waiting,
            "needs_review": goals.needs_review,
            "failed": goals.failed,
        },
        value={"operator_minutes_saved": MINUTES_SAVED_PER_SUCCESS * goals.succeeded},
        recent_activity=[
            {
                "id": str(row.id),
                "occurred_at": _iso(row.occurred_at),
                "summary": _activity_summary(row),
                "goal_id": str(row.goal_id),
            }
            for row in activity
        ],
    )
