"""Fleet overview aggregation.

The shape is stable from the first commit: a screen that has to guess whether a
section exists cannot be trusted. Counts are real reads, so a zero here means
"nothing happened", never "not implemented".
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import Connection, text


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


def load_dashboard(
    connection: Connection, tenant_ids: list[uuid.UUID] | None
) -> DashboardSummary:
    """Aggregate for one tenant, or across every tenant when ``tenant_ids`` is None.

    Increment 1 ships the contract and the empty answer; the goal, action, and
    outcome tables that fill it in arrive with the Late Pickup slice, so the
    query degrades to zeros rather than failing while they do not exist.
    """
    if not _table_exists(connection, "goals"):
        return DashboardSummary()

    scope_clause = "" if tenant_ids is None else " where tenant_id = any(:tenant_ids)"
    params = {} if tenant_ids is None else {"tenant_ids": tenant_ids}

    goals = connection.execute(
        text(
            f"""
            select
                count(*) filter (where state not in ('succeeded', 'failed', 'expired'))
                    as opened,
                count(*) filter (where state = 'waiting') as waiting,
                count(*) filter (where state = 'needs_review') as needs_review,
                count(*) filter (where state = 'failed') as failed
            from goals{scope_clause}
            """
        ),
        params,
    ).one()

    return DashboardSummary(
        goals={
            "opened": goals.opened,
            "waiting": goals.waiting,
            "needs_review": goals.needs_review,
            "failed": goals.failed,
        }
    )
