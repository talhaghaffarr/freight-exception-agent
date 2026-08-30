"""The seeded agent history: deterministic, re-runnable, and honest.

The history is what makes the Goals, Agents, and Analytics screens show a
living system. These tests pin the outcome distribution the PRD taxonomy
names, and prove the seed is an upsert rather than an append.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from relayops.seed_freight import ATLAS, MERIDIAN
from relayops.seed_history import (
    AGENT_DEFINITIONS,
    ATLAS_TERMINAL_OUTCOMES,
    seed_history,
)

pytestmark = pytest.mark.integration


def _counts(connection) -> tuple[int, int, int]:
    return (
        connection.execute(text("select count(*) from goals")).scalar_one(),
        connection.execute(text("select count(*) from goal_events")).scalar_one(),
        connection.execute(text("select count(*) from outcomes")).scalar_one(),
    )


def test_seed_history_is_idempotent(seeded_freight_engine) -> None:
    with seeded_freight_engine.begin() as connection:
        first = seed_history(connection)
        after_first = _counts(connection)
        second = seed_history(connection)
        after_second = _counts(connection)

    assert first == second
    assert after_first == after_second


def test_the_atlas_outcome_distribution_matches_the_taxonomy(seeded_freight_engine) -> None:
    with seeded_freight_engine.begin() as connection:
        seed_history(connection)
        rows = connection.execute(
            text(
                "select terminal_outcome, count(*) from goals "
                "where tenant_id = :tenant and terminal_outcome is not null "
                "group by terminal_outcome"
            ),
            {"tenant": ATLAS},
        ).all()

    assert dict(rows) == dict(ATLAS_TERMINAL_OUTCOMES)


def test_meridian_history_is_mostly_tenant_disabled(seeded_freight_engine) -> None:
    with seeded_freight_engine.begin() as connection:
        seed_history(connection)
        rows = dict(
            connection.execute(
                text(
                    "select terminal_outcome, count(*) from goals "
                    "where tenant_id = :tenant group by terminal_outcome"
                ),
                {"tenant": MERIDIAN},
            ).all()
        )

    assert rows == {"tenant_disabled": 7, "below_threshold": 3}


def test_four_atlas_goals_are_still_open_with_a_next_tick(seeded_freight_engine) -> None:
    with seeded_freight_engine.begin() as connection:
        seed_history(connection)
        rows = connection.execute(
            text(
                "select state, next_tick_at from goals "
                "where tenant_id = :tenant and terminal_outcome is null"
            ),
            {"tenant": ATLAS},
        ).all()

    assert sorted(row.state for row in rows) == [
        "action_pending",
        "evaluating",
        "needs_review",
        "waiting",
    ]
    assert all(row.next_tick_at is not None for row in rows)


def test_every_terminal_goal_records_its_outcome_event_and_row(seeded_freight_engine) -> None:
    with seeded_freight_engine.begin() as connection:
        seed_history(connection)

        # The last event of every closed goal is the recorded outcome.
        unfinished = connection.execute(
            text(
                """
                select count(*) from goals g
                where g.terminal_outcome is not null
                  and not exists (
                    select 1 from goal_events e
                    where e.goal_id = g.id and e.event_type = 'outcome_recorded'
                      and e.detail ->> 'outcome' = g.terminal_outcome
                  )
                """
            )
        ).scalar_one()
        assert unfinished == 0

        # And the outcomes table carries one countable row per closed goal.
        missing = connection.execute(
            text(
                """
                select count(*) from goals g
                where g.terminal_outcome is not null
                  and not exists (
                    select 1 from outcomes o
                    where o.goal_id = g.id and o.reason = g.terminal_outcome
                  )
                """
            )
        ).scalar_one()
        assert missing == 0


def test_every_goal_starts_with_an_opened_event(seeded_freight_engine) -> None:
    with seeded_freight_engine.begin() as connection:
        seed_history(connection)
        broken = connection.execute(
            text(
                """
                select count(*) from goals g
                where not exists (
                    select 1 from goal_events e
                    where e.goal_id = g.id and e.sequence = 1 and e.event_type = 'opened'
                )
                """
            )
        ).scalar_one()

    assert broken == 0


def test_the_agent_catalog_is_seeded_with_tenant_configs(seeded_freight_engine) -> None:
    with seeded_freight_engine.begin() as connection:
        seed_history(connection)
        definitions = connection.execute(
            text("select agent_type from agent_definitions order by agent_type")
        ).scalars().all()
        atlas_late = connection.execute(
            text(
                "select enabled, config from tenant_agent_configs "
                "where tenant_id = :tenant and agent_type = 'late_pickup'"
            ),
            {"tenant": ATLAS},
        ).one()
        meridian_late = connection.execute(
            text(
                "select enabled from tenant_agent_configs "
                "where tenant_id = :tenant and agent_type = 'late_pickup'"
            ),
            {"tenant": MERIDIAN},
        ).one()

    assert definitions == sorted(spec.agent_type for spec in AGENT_DEFINITIONS)
    assert atlas_late.enabled is True
    assert atlas_late.config["late_threshold_minutes"] == 30
    assert meridian_late.enabled is False


def test_reset_demo_reanchors_the_history_too(seeded_freight_engine) -> None:
    """After a reset the overview still shows a living system, never zeros."""
    from relayops.services.race_demo import reset_demo

    with seeded_freight_engine.begin() as connection:
        seed_history(connection)

    result = reset_demo(seeded_freight_engine, ATLAS)

    assert result["goals_cleared"] >= 44
    with seeded_freight_engine.connect() as connection:
        remaining = connection.execute(
            text("select count(*) from goals where tenant_id = :tenant"),
            {"tenant": ATLAS},
        ).scalar_one()
    assert remaining == 44
