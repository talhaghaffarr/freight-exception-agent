"""Load persistence and view assembly.

Every method takes an explicit ``tenant_id``. There is no method that resolves a
load without one, because the whole point of the safety model is that a load
lookup can only happen inside an already-authorised tenant.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Connection, text

from relayops.domain.freight import Load, LoadView, Stop, TrackingPoint

_LOAD_COLUMNS = """
    id, tenant_id, reference, status, customer_name, account_manager_email,
    account_manager_name, carrier_name, driver_name, driver_phone,
    latest_tracking_at, latest_latitude, latest_longitude
"""


def _to_load(row) -> Load:
    return Load(
        id=row.id,
        tenant_id=row.tenant_id,
        reference=row.reference,
        status=row.status,
        customer_name=row.customer_name,
        account_manager_email=row.account_manager_email,
        account_manager_name=row.account_manager_name,
        carrier_name=row.carrier_name,
        driver_name=row.driver_name,
        driver_phone=row.driver_phone,
        latest_tracking_at=row.latest_tracking_at,
        latest_latitude=row.latest_latitude,
        latest_longitude=row.latest_longitude,
    )


def _to_stop(row) -> Stop:
    return Stop(
        id=row.id,
        load_id=row.load_id,
        sequence=row.sequence,
        stop_type=row.stop_type,
        facility_name=row.facility_name,
        city=row.city,
        state=row.state,
        latitude=row.latitude,
        longitude=row.longitude,
        timezone=row.timezone,
        appointment_revision=row.appointment_revision,
        appointment_start=row.appointment_start,
        appointment_end=row.appointment_end,
        arrived_at=row.arrived_at,
        departed_at=row.departed_at,
        completed_at=row.completed_at,
    )


class LoadRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(self, tenant_id: uuid.UUID, load_id: uuid.UUID) -> Load | None:
        row = self._connection.execute(
            text(f"select {_LOAD_COLUMNS} from loads where tenant_id = :t and id = :id"),
            {"t": tenant_id, "id": load_id},
        ).one_or_none()
        return _to_load(row) if row else None

    def get_by_reference(self, tenant_id: uuid.UUID, reference: str) -> Load | None:
        row = self._connection.execute(
            text(
                f"select {_LOAD_COLUMNS} from loads "
                "where tenant_id = :t and reference = :reference"
            ),
            {"t": tenant_id, "reference": reference},
        ).one_or_none()
        return _to_load(row) if row else None

    def stops_for(self, tenant_id: uuid.UUID, load_id: uuid.UUID) -> list[Stop]:
        rows = self._connection.execute(
            text(
                "select id, load_id, sequence, stop_type, facility_name, city, state, "
                "latitude, longitude, timezone, appointment_revision, appointment_start, "
                "appointment_end, arrived_at, departed_at, completed_at "
                "from stops where tenant_id = :t and load_id = :l order by sequence"
            ),
            {"t": tenant_id, "l": load_id},
        ).all()
        return [_to_stop(row) for row in rows]

    def latest_tracking(self, tenant_id: uuid.UUID, load_id: uuid.UUID) -> TrackingPoint | None:
        row = self._connection.execute(
            text(
                "select id, load_id, recorded_at, latitude, longitude, source "
                "from tracking_points where tenant_id = :t and load_id = :l "
                "order by recorded_at desc limit 1"
            ),
            {"t": tenant_id, "l": load_id},
        ).one_or_none()
        if row is None:
            return None
        return TrackingPoint(
            id=row.id,
            load_id=row.load_id,
            recorded_at=row.recorded_at,
            latitude=row.latitude,
            longitude=row.longitude,
            source=row.source,
        )

    def view(self, tenant_id: uuid.UUID, load_id: uuid.UUID) -> LoadView | None:
        load = self.get(tenant_id, load_id)
        if load is None:
            return None
        return LoadView(
            load=load,
            stops=tuple(self.stops_for(tenant_id, load_id)),
            latest_tracking=self.latest_tracking(tenant_id, load_id),
        )

    def list_active(self, tenant_id: uuid.UUID, limit: int = 100) -> list[Load]:
        rows = self._connection.execute(
            text(
                f"select {_LOAD_COLUMNS} from loads "
                "where tenant_id = :t and status = 'active' order by reference limit :limit"
            ),
            {"t": tenant_id, "limit": limit},
        ).all()
        return [_to_load(row) for row in rows]
