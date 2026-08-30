"""Computed arrival time, or an explicit refusal to compute one."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from relayops.domain.freight import TrackingPoint
from relayops.facts.tracking import (
    DEFAULT_FRESH_WITHIN,
    DEFAULT_MAX_TRACKING_AGE,
    Freshness,
    classify_tracking_freshness,
    require_aware,
)


@dataclass(frozen=True, slots=True)
class RouteEstimate:
    """Remaining distance and duration from a routing source.

    ``traffic_assumption`` travels with the estimate because an operator reading
    a predicted arrival is entitled to know whether traffic was modelled.
    """

    remaining_meters: int
    remaining_duration: timedelta
    source: str
    traffic_assumption: str


@dataclass(frozen=True, slots=True)
class EtaFact:
    """A predicted arrival, or the reason there is none.

    ``predicted_arrival`` and ``reason`` are mutually exclusive: exactly one of
    them is set, so a template can never render an empty ETA as if it were a
    real one.
    """

    predicted_arrival: datetime | None
    freshness: Freshness | None
    evidence_at: datetime | None
    source: str | None
    traffic_assumption: str | None
    remaining_meters: int | None
    reason: str | None

    @property
    def available(self) -> bool:
        return self.predicted_arrival is not None


def _unavailable(reason: str, freshness: Freshness | None, evidence_at: datetime | None) -> EtaFact:
    return EtaFact(
        predicted_arrival=None,
        freshness=freshness,
        evidence_at=evidence_at,
        source=None,
        traffic_assumption=None,
        remaining_meters=None,
        reason=reason,
    )


def compute_eta(
    route: RouteEstimate | None,
    position: TrackingPoint | None,
    now: datetime,
    *,
    max_tracking_age: timedelta = DEFAULT_MAX_TRACKING_AGE,
    fresh_within: timedelta = DEFAULT_FRESH_WITHIN,
) -> EtaFact:
    """Predict arrival as ``now`` plus the remaining route duration.

    The prediction is anchored to ``now`` rather than to the position timestamp:
    the route duration describes travel still ahead of the truck, and adding it
    to an older fix would quietly claim progress we have not observed.

    Returns an unavailable fact when the position is missing or older than
    ``max_tracking_age``, when there is no route to measure, per the honesty
    rule that unknown is a valid answer.
    """
    require_aware(now, "now")

    if position is None:
        return _unavailable("tracking_missing", None, None)

    freshness = classify_tracking_freshness(
        position.recorded_at, now, max_tracking_age, fresh_within=fresh_within
    )
    if freshness is Freshness.STALE:
        return _unavailable("tracking_stale", freshness, position.recorded_at)

    if route is None:
        return _unavailable("route_unavailable", freshness, position.recorded_at)

    return EtaFact(
        predicted_arrival=now + route.remaining_duration,
        freshness=freshness,
        evidence_at=position.recorded_at,
        source=route.source,
        traffic_assumption=route.traffic_assumption,
        remaining_meters=route.remaining_meters,
        reason=None,
    )
