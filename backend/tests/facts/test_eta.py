"""Computed ETA, and the cases where refusing to compute one is the answer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from relayops.domain.freight import TrackingPoint
from relayops.facts.eta import RouteEstimate, compute_eta
from relayops.facts.tracking import Freshness

NOW = datetime(2026, 8, 30, 9, 43, tzinfo=UTC)
LOAD_ID = uuid.uuid4()


def position(age_minutes: int) -> TrackingPoint:
    return TrackingPoint(
        id=uuid.uuid4(),
        load_id=LOAD_ID,
        recorded_at=NOW - timedelta(minutes=age_minutes),
        latitude=37.2153,
        longitude=-93.2982,
        source="telematics",
    )


def route(minutes: int) -> RouteEstimate:
    return RouteEstimate(
        remaining_meters=218_900,
        remaining_duration=timedelta(minutes=minutes),
        source="route_estimate",
        traffic_assumption="historical_average",
    )


def test_predicted_arrival_is_now_plus_the_remaining_route_duration() -> None:
    fact = compute_eta(route(55), position(age_minutes=2), NOW)

    assert fact.available is True
    assert fact.predicted_arrival == datetime(2026, 8, 30, 10, 38, tzinfo=UTC)
    assert fact.reason is None


def test_the_eta_carries_the_evidence_it_was_derived_from() -> None:
    point = position(age_minutes=2)

    fact = compute_eta(route(55), point, NOW)

    assert fact.evidence_at == point.recorded_at
    assert fact.freshness is Freshness.FRESH
    assert fact.source == "route_estimate"
    assert fact.traffic_assumption == "historical_average"


def test_stale_tracking_yields_no_eta_and_says_why() -> None:
    fact = compute_eta(route(55), position(age_minutes=42), NOW)

    assert fact.available is False
    assert fact.predicted_arrival is None
    assert fact.reason == "tracking_stale"
    assert fact.freshness is Freshness.STALE


def test_an_aging_position_still_produces_an_eta_but_is_labelled_aging() -> None:
    """Between the fresh band and the maximum age we compute, and we say so."""
    fact = compute_eta(route(55), position(age_minutes=18), NOW)

    assert fact.available is True
    assert fact.freshness is Freshness.AGING


def test_a_missing_position_is_unknown_rather_than_zero() -> None:
    fact = compute_eta(route(55), None, NOW)

    assert fact.available is False
    assert fact.predicted_arrival is None
    assert fact.reason == "tracking_missing"


def test_a_missing_route_cannot_be_substituted_with_a_straight_line_guess() -> None:
    fact = compute_eta(None, position(age_minutes=2), NOW)

    assert fact.available is False
    assert fact.reason == "route_unavailable"


def test_a_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        compute_eta(route(55), position(age_minutes=2), datetime(2026, 8, 30, 9, 43))
