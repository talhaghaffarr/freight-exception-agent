"""Tracking freshness is a boundary decision, so the boundaries are the tests.

An operator acting on a stale position is worse than an operator told the
position is unknown, so the classification has to be explicit rather than a
truthiness check somewhere in a template.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from relayops.facts.tracking import Freshness, classify_tracking_freshness

NOW = datetime(2026, 8, 30, 9, 43, tzinfo=UTC)
MAX_AGE = timedelta(minutes=30)


@pytest.mark.parametrize(
    ("age_minutes", "expected"),
    [
        (0, "fresh"),
        (4, "fresh"),
        (10, "fresh"),
        (11, "aging"),
        (15, "aging"),
        (30, "aging"),
        (31, "stale"),
    ],
)
def test_tracking_freshness_has_explicit_boundaries(age_minutes: int, expected: str) -> None:
    recorded_at = NOW - timedelta(minutes=age_minutes)

    assert classify_tracking_freshness(recorded_at, NOW, MAX_AGE).value == expected


def test_the_aging_band_is_configurable_independently_of_the_maximum_age() -> None:
    recorded_at = NOW - timedelta(minutes=4)

    freshness = classify_tracking_freshness(
        recorded_at, NOW, MAX_AGE, fresh_within=timedelta(minutes=2)
    )

    assert freshness is Freshness.AGING


def test_a_naive_timestamp_is_rejected_rather_than_assumed_to_be_utc() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        classify_tracking_freshness(datetime(2026, 8, 30, 9, 40), NOW, MAX_AGE)


def test_a_position_recorded_in_the_future_is_not_treated_as_fresh() -> None:
    """Clock skew on a telematics feed must not read as a perfect fix."""
    recorded_at = NOW + timedelta(minutes=5)

    assert classify_tracking_freshness(recorded_at, NOW, MAX_AGE) is Freshness.STALE
