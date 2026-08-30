"""Freight value objects.

These are read models assembled for decisions and serialisation. They are
immutable and timezone-aware; a naive datetime is a bug, not an input.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

LoadStatus = Literal["active", "delivered", "cancelled", "draft"]
StopType = Literal["pickup", "delivery"]


@dataclass(frozen=True, slots=True)
class TrackingPoint:
    id: uuid.UUID
    load_id: uuid.UUID
    recorded_at: datetime
    latitude: float
    longitude: float
    source: str


@dataclass(frozen=True, slots=True)
class Stop:
    id: uuid.UUID
    load_id: uuid.UUID
    sequence: int
    stop_type: StopType
    facility_name: str | None
    city: str | None
    state: str | None
    latitude: float | None
    longitude: float | None
    timezone: str
    appointment_revision: int
    appointment_start: datetime | None
    appointment_end: datetime | None
    arrived_at: datetime | None
    departed_at: datetime | None
    completed_at: datetime | None

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None


@dataclass(frozen=True, slots=True)
class Load:
    id: uuid.UUID
    tenant_id: uuid.UUID
    reference: str
    status: LoadStatus
    customer_name: str
    account_manager_email: str
    account_manager_name: str | None
    carrier_name: str | None
    driver_name: str | None
    driver_phone: str | None
    latest_tracking_at: datetime | None
    latest_latitude: float | None
    latest_longitude: float | None


@dataclass(frozen=True, slots=True)
class LoadView:
    """A load with the stops and latest tracking a decision needs."""

    load: Load
    stops: tuple[Stop, ...]
    latest_tracking: TrackingPoint | None

    def stop(self, stop_id: uuid.UUID) -> Stop | None:
        for stop in self.stops:
            if stop.id == stop_id:
                return stop
        return None

    def first_incomplete_pickup(self) -> Stop | None:
        for stop in sorted(self.stops, key=lambda s: s.sequence):
            if stop.stop_type == "pickup" and not stop.is_complete:
                return stop
        return None
