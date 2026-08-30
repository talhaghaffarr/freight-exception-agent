"""Late-pickup facts: the deterministic input to the agent's policy.

These functions decide nothing about whether to notify anyone. They establish
what is true, including "we do not know", and the agent decides separately.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from relayops.domain.freight import Load, LoadView, Stop, TrackingPoint
from relayops.facts.eta import RouteEstimate
from relayops.facts.late_pickup import LatePickupConfig, late_pickup_facts

NOW = datetime(2026, 8, 30, 9, 43, tzinfo=UTC)
TENANT = uuid.uuid4()
CONFIG = LatePickupConfig()


def build_view(
    *,
    appointment: datetime | None = datetime(2026, 8, 30, 10, 0, tzinfo=UTC),
    tracking_age: int | None = 2,
    completed: bool = False,
) -> LoadView:
    load_id = uuid.uuid4()
    load = Load(
        id=load_id,
        tenant_id=TENANT,
        reference="LD-1048",
        status="active",
        customer_name="ACME Retail",
        account_manager_email="am@atlas.example",
        account_manager_name="Dana Reyes",
        carrier_name="BlueLine Logistics",
        driver_name="R. Okafor",
        driver_phone="+15555550142",
        latest_tracking_at=None,
        latest_latitude=None,
        latest_longitude=None,
    )
    stop = Stop(
        id=uuid.uuid4(),
        load_id=load_id,
        sequence=1,
        stop_type="pickup",
        facility_name="ACME Distribution Center",
        city="Chicago",
        state="IL",
        latitude=41.8781,
        longitude=-87.6298,
        timezone="America/Chicago",
        appointment_revision=3,
        appointment_start=appointment,
        appointment_end=None if appointment is None else appointment + timedelta(hours=1),
        arrived_at=None,
        departed_at=None,
        completed_at=NOW - timedelta(minutes=5) if completed else None,
    )
    point = (
        None
        if tracking_age is None
        else TrackingPoint(
            id=uuid.uuid4(),
            load_id=load_id,
            recorded_at=NOW - timedelta(minutes=tracking_age),
            latitude=37.2153,
            longitude=-93.2982,
            source="telematics",
        )
    )
    return LoadView(load=load, stops=(stop,), latest_tracking=point)


def route(minutes: int) -> RouteEstimate:
    return RouteEstimate(
        remaining_meters=218_900,
        remaining_duration=timedelta(minutes=minutes),
        source="route_estimate",
        traffic_assumption="historical_average",
    )


def test_an_eta_past_the_appointment_by_more_than_the_threshold_is_late() -> None:
    facts = late_pickup_facts(build_view(), CONFIG, NOW, route=route(55))

    assert facts.minutes_late == 38
    assert facts.classification == "late"
    assert facts.appointment_revision == 3
    assert facts.load_reference == "LD-1048"


def test_lateness_below_the_threshold_is_at_risk_not_late() -> None:
    facts = late_pickup_facts(build_view(), CONFIG, NOW, route=route(25))

    assert facts.minutes_late == 8
    assert facts.classification == "at_risk"


def test_a_pickup_beyond_the_planning_horizon_is_scheduled_not_early() -> None:
    """A load due in nine hours is not "early"; it has not started yet.

    Without this band the board reads as if most of the fleet were running
    ahead of schedule, which buries the handful of loads that need a human.
    """
    view = build_view(appointment=NOW + timedelta(hours=9))

    facts = late_pickup_facts(view, CONFIG, NOW, route=route(55))

    assert facts.classification == "scheduled"
    assert facts.minutes_late == -485


def test_arriving_before_the_appointment_is_not_late() -> None:
    facts = late_pickup_facts(build_view(), CONFIG, NOW, route=route(10))

    assert facts.minutes_late == -7
    assert facts.classification == "on_time"


def test_stale_tracking_produces_unknown_rather_than_an_invented_lateness() -> None:
    facts = late_pickup_facts(build_view(tracking_age=42), CONFIG, NOW, route=route(55))

    assert facts.classification == "unknown"
    assert facts.minutes_late is None
    assert facts.reason == "tracking_stale"
    assert facts.eta.available is False


def test_a_missing_appointment_cannot_be_late_against_nothing() -> None:
    facts = late_pickup_facts(build_view(appointment=None), CONFIG, NOW, route=route(55))

    assert facts.classification == "unknown"
    assert facts.minutes_late is None
    assert facts.reason == "appointment_missing"


def test_a_completed_pickup_has_no_pending_pickup_to_judge() -> None:
    facts = late_pickup_facts(build_view(completed=True), CONFIG, NOW, route=route(55))

    assert facts.classification == "unknown"
    assert facts.reason == "pickup_complete"
    assert facts.stop_id is None


def test_facts_expose_the_position_and_evidence_time_backing_the_claim() -> None:
    view = build_view()

    facts = late_pickup_facts(view, CONFIG, NOW, route=route(55))

    assert facts.latest_position == (37.2153, -93.2982)
    assert facts.evidence_at == view.latest_tracking.recorded_at
    assert facts.threshold_minutes == CONFIG.late_threshold_minutes
