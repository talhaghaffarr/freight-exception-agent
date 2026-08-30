"""Tracking freshness classification."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

DEFAULT_MAX_TRACKING_AGE = timedelta(minutes=30)
DEFAULT_FRESH_WITHIN = timedelta(minutes=10)


class Freshness(StrEnum):
    """How much weight a position may carry in an outbound claim."""

    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"


def require_aware(moment: datetime, label: str) -> datetime:
    """Reject naive datetimes at the boundary.

    A naive timestamp here is an ambiguity we would silently resolve as UTC and
    then quote to a customer as fact, so it is a programming error, not input.
    """
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return moment


def classify_tracking_freshness(
    recorded_at: datetime,
    now: datetime,
    max_age: timedelta = DEFAULT_MAX_TRACKING_AGE,
    *,
    fresh_within: timedelta = DEFAULT_FRESH_WITHIN,
) -> Freshness:
    """Classify a position by age.

    ``fresh_within`` is deliberately separate from ``max_age``: the first is
    where we are willing to state a position, the second is where we are still
    willing to compute an ETA from it.

    A position stamped in the future is clock skew, not a perfect fix, and is
    treated as stale so it can never strengthen a claim.
    """
    require_aware(recorded_at, "recorded_at")
    require_aware(now, "now")

    age = now - recorded_at
    if age < timedelta(0):
        return Freshness.STALE
    if age <= fresh_within:
        return Freshness.FRESH
    if age <= max_age:
        return Freshness.AGING
    return Freshness.STALE
