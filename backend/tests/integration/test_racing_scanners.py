"""Two scanners, one goal.

This is the property the whole design rests on: correctness under concurrency
comes from a database constraint, not from a worker remembering what it did.
The test therefore uses two real connections racing on a barrier rather than
mocks -- a mock cannot violate a unique index, so a mock cannot prove this.
"""

from __future__ import annotations

import pytest

from relayops.seed_freight import ATLAS
from relayops.services.race_demo import race_scanners

pytestmark = pytest.mark.integration


def test_two_racing_scanners_produce_exactly_one_goal(seeded_freight_engine) -> None:
    result = race_scanners(seeded_freight_engine, ATLAS, "LD-1048")

    assert result.goals_created == 1
    assert result.opened_events == 1
    assert len({attempt.goal_id for attempt in result.attempts}) == 1


def test_exactly_one_scanner_reports_that_it_created_the_goal(seeded_freight_engine) -> None:
    result = race_scanners(seeded_freight_engine, ATLAS, "LD-1048")

    created = [attempt for attempt in result.attempts if attempt.created]
    conflicted = [attempt for attempt in result.attempts if not attempt.created]

    assert len(created) == 1
    assert len(conflicted) == 1
    assert conflicted[0].outcome == "unique_conflict"
    assert created[0].outcome == "inserted"


def test_racing_again_on_the_same_trigger_still_yields_one_goal(seeded_freight_engine) -> None:
    """Replay safety: a redelivered scan must not open a second episode."""
    first = race_scanners(seeded_freight_engine, ATLAS, "LD-1048")
    second = race_scanners(seeded_freight_engine, ATLAS, "LD-1048", reset=False)

    assert second.goals_created == 1
    assert second.attempts[0].goal_id == first.attempts[0].goal_id
    assert all(attempt.created is False for attempt in second.attempts)


def test_the_trigger_fingerprint_names_the_appointment_episode(seeded_freight_engine) -> None:
    result = race_scanners(seeded_freight_engine, ATLAS, "LD-1048")

    # A rescheduled appointment bumps the revision and so opens a fresh episode
    # rather than colliding with the goal for the previous window.
    assert result.trigger_fingerprint.endswith(":late:v1")
    assert ":appointment:3:" in result.trigger_fingerprint
