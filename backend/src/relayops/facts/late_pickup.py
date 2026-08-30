"""Late-pickup facts.

This module answers "is this pickup going to be late, and how do we know" and
nothing else. Whether that warrants contacting anyone is policy, and policy
lives with the agent.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from relayops.domain.freight import LoadView
from relayops.facts.eta import EtaFact, RouteEstimate, compute_eta
from relayops.facts.tracking import (
    DEFAULT_FRESH_WITHIN,
    DEFAULT_MAX_TRACKING_AGE,
    Freshness,
    require_aware,
)

Classification = Literal["scheduled", "early", "on_time", "at_risk", "late", "unknown"]


@dataclass(frozen=True, slots=True)
class LatePickupConfig:
    """The tenant-tunable thresholds the facts depend on.

    Only values that change what is *true* live here. Enablement, schedules and
    recipients are policy and belong to the agent configuration.
    """

    late_threshold_minutes: int = 30
    early_threshold_minutes: int = 15
    #: Beyond this much slack a pickup has not started rather than being early.
    planning_horizon_minutes: int = 240
    max_tracking_age: timedelta = DEFAULT_MAX_TRACKING_AGE
    fresh_within: timedelta = DEFAULT_FRESH_WITHIN


@dataclass(frozen=True, slots=True)
class LatePickupFacts:
    """Everything the operator and the template are allowed to rely on."""

    load_reference: str
    stop_id: uuid.UUID | None
    appointment_start: datetime | None
    appointment_revision: int | None
    eta: EtaFact
    minutes_late: int | None
    classification: Classification
    tracking_freshness: Freshness | None
    latest_position: tuple[float, float] | None
    evidence_at: datetime | None
    threshold_minutes: int
    reason: str | None

    @property
    def is_late(self) -> bool:
        return self.classification == "late"


def _unknown(
    view: LoadView,
    config: LatePickupConfig,
    reason: str,
    *,
    stop_id: uuid.UUID | None,
    appointment_start: datetime | None,
    appointment_revision: int | None,
    eta: EtaFact,
) -> LatePickupFacts:
    point = view.latest_tracking
    return LatePickupFacts(
        load_reference=view.load.reference,
        stop_id=stop_id,
        appointment_start=appointment_start,
        appointment_revision=appointment_revision,
        eta=eta,
        minutes_late=None,
        classification="unknown",
        tracking_freshness=eta.freshness,
        latest_position=None if point is None else (point.latitude, point.longitude),
        evidence_at=None if point is None else point.recorded_at,
        threshold_minutes=config.late_threshold_minutes,
        reason=reason,
    )


def late_pickup_facts(
    view: LoadView,
    config: LatePickupConfig,
    now: datetime,
    *,
    route: RouteEstimate | None = None,
) -> LatePickupFacts:
    """Derive lateness for the first incomplete pickup on a load.

    Every path returns a fact object. An unknown answer is a first-class result
    carrying the reason it is unknown, because "we could not tell" is
    operationally different from "it is on time" and the two must never
    collapse into the same silence.
    """
    require_aware(now, "now")

    eta = compute_eta(
        route,
        view.latest_tracking,
        now,
        max_tracking_age=config.max_tracking_age,
        fresh_within=config.fresh_within,
    )

    stop = view.first_incomplete_pickup()
    if stop is None:
        return _unknown(
            view,
            config,
            "pickup_complete",
            stop_id=None,
            appointment_start=None,
            appointment_revision=None,
            eta=eta,
        )

    if stop.appointment_start is None:
        return _unknown(
            view,
            config,
            "appointment_missing",
            stop_id=stop.id,
            appointment_start=None,
            appointment_revision=stop.appointment_revision,
            eta=eta,
        )

    if not eta.available:
        return _unknown(
            view,
            config,
            eta.reason or "facts_incomplete",
            stop_id=stop.id,
            appointment_start=stop.appointment_start,
            appointment_revision=stop.appointment_revision,
            eta=eta,
        )

    assert eta.predicted_arrival is not None  # narrowed by eta.available
    delta_minutes = round((eta.predicted_arrival - stop.appointment_start).total_seconds() / 60)

    if delta_minutes >= config.late_threshold_minutes:
        classification: Classification = "late"
    elif delta_minutes > 0:
        classification = "at_risk"
    elif delta_minutes <= -config.planning_horizon_minutes:
        # Far more slack than a working day's dispatch: not early, not started.
        classification = "scheduled"
    elif delta_minutes <= -config.early_threshold_minutes:
        classification = "early"
    else:
        classification = "on_time"

    point = view.latest_tracking
    return LatePickupFacts(
        load_reference=view.load.reference,
        stop_id=stop.id,
        appointment_start=stop.appointment_start,
        appointment_revision=stop.appointment_revision,
        eta=eta,
        minutes_late=delta_minutes,
        classification=classification,
        tracking_freshness=eta.freshness,
        latest_position=None if point is None else (point.latitude, point.longitude),
        evidence_at=None if point is None else point.recorded_at,
        threshold_minutes=config.late_threshold_minutes,
        reason=None,
    )
