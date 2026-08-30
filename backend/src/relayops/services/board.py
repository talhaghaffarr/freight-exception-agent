"""The live operations board.

One query assembles each active load with its pending pickup, its remaining
route and its newest position, and the fact engine then decides what is true
about it. The board holds no policy: it reports lateness and unknowns, and the
agent decides separately whether either warrants contacting anyone.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, text

from relayops.domain.freight import Load, LoadView, Stop, TrackingPoint
from relayops.facts.eta import RouteEstimate
from relayops.facts.late_pickup import LatePickupConfig, LatePickupFacts, late_pickup_facts

# Tenant is the leading predicate on every board query. Scope is a parameter,
# never a filter applied after the fact in Python.
BOARD_SQL = """
select
    l.id                as load_id,
    l.tenant_id         as tenant_id,
    l.reference         as reference,
    l.status            as status,
    l.customer_name     as customer_name,
    l.account_manager_email as account_manager_email,
    l.account_manager_name  as account_manager_name,
    l.carrier_name      as carrier_name,
    l.driver_name       as driver_name,
    l.driver_phone      as driver_phone,
    l.latest_tracking_at as latest_tracking_at,
    l.latest_latitude   as latest_latitude,
    l.latest_longitude  as latest_longitude,
    p.id                as pickup_id,
    p.sequence          as pickup_sequence,
    p.facility_name     as pickup_facility,
    p.city              as pickup_city,
    p.state             as pickup_state,
    p.latitude          as pickup_latitude,
    p.longitude         as pickup_longitude,
    p.timezone          as pickup_timezone,
    p.appointment_revision as pickup_revision,
    p.appointment_start as pickup_appointment_start,
    p.appointment_end   as pickup_appointment_end,
    p.arrived_at        as pickup_arrived_at,
    p.departed_at       as pickup_departed_at,
    p.completed_at      as pickup_completed_at,
    d.city              as destination_city,
    d.state             as destination_state,
    d.appointment_start as delivery_appointment_start,
    lg.distance_meters  as remaining_meters,
    lg.expected_duration_seconds as remaining_seconds
from loads l
join stops p
    on p.tenant_id = l.tenant_id and p.load_id = l.id
   and p.stop_type = 'pickup' and p.sequence = 1
left join stops d
    on d.tenant_id = l.tenant_id and d.load_id = l.id and d.stop_type = 'delivery'
left join legs lg
    on lg.tenant_id = l.tenant_id and lg.load_id = l.id and lg.sequence = 1
where l.tenant_id = :tenant_id
  and l.status = 'active'
order by p.appointment_start asc nulls last, l.reference asc
limit :limit
"""


@dataclass(frozen=True, slots=True)
class BoardRow:
    """One load as the console shows it, with the facts already computed."""

    load_id: uuid.UUID
    reference: str
    customer_name: str
    carrier_name: str | None
    driver_name: str | None
    origin: str
    destination: str
    current_position_label: str | None
    pickup_appointment: datetime | None
    facts: LatePickupFacts
    view: LoadView

    @property
    def priority(self) -> int:
        """Sort weight. Unknowns rank above on-time work, not below it.

        A load we cannot see is an operational problem even though it produces
        no number, so it must not sink to the bottom of the board behind loads
        that are merely a few minutes behind.
        """
        by_class = {"late": 0, "unknown": 1, "at_risk": 2, "on_time": 3, "early": 4}
        return by_class.get(self.facts.classification, 5)


def _label(city: str | None, state: str | None) -> str:
    return ", ".join(part for part in (city, state) if part) or "Unknown"


def _row_to_view(row) -> tuple[LoadView, RouteEstimate | None]:
    load = Load(
        id=row.load_id,
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
    stop = Stop(
        id=row.pickup_id,
        load_id=row.load_id,
        sequence=row.pickup_sequence,
        stop_type="pickup",
        facility_name=row.pickup_facility,
        city=row.pickup_city,
        state=row.pickup_state,
        latitude=row.pickup_latitude,
        longitude=row.pickup_longitude,
        timezone=row.pickup_timezone,
        appointment_revision=row.pickup_revision,
        appointment_start=row.pickup_appointment_start,
        appointment_end=row.pickup_appointment_end,
        arrived_at=row.pickup_arrived_at,
        departed_at=row.pickup_departed_at,
        completed_at=row.pickup_completed_at,
    )
    point = (
        None
        if row.latest_tracking_at is None
        else TrackingPoint(
            id=row.load_id,  # the denormalised latest fix, not a stored row id
            load_id=row.load_id,
            recorded_at=row.latest_tracking_at,
            latitude=row.latest_latitude,
            longitude=row.latest_longitude,
            source="eld",
        )
    )
    route = (
        None
        if row.remaining_seconds is None
        else RouteEstimate(
            remaining_meters=int(row.remaining_meters or 0),
            remaining_duration=timedelta(seconds=row.remaining_seconds),
            source="route_estimate",
            traffic_assumption="historical_average",
        )
    )
    return LoadView(load=load, stops=(stop,), latest_tracking=point), route


def load_board(
    connection: Connection,
    tenant_id: uuid.UUID,
    *,
    now: datetime | None = None,
    config: LatePickupConfig | None = None,
    limit: int = 200,
) -> list[BoardRow]:
    """Assemble the tenant's active loads with late-pickup facts attached."""
    moment = now or datetime.now(UTC)
    policy = config or LatePickupConfig()

    rows = connection.execute(
        text(BOARD_SQL), {"tenant_id": tenant_id, "limit": limit}
    ).fetchall()

    board: list[BoardRow] = []
    for row in rows:
        view, route = _row_to_view(row)
        facts = late_pickup_facts(view, policy, moment, route=route)
        board.append(
            BoardRow(
                load_id=row.load_id,
                reference=row.reference,
                customer_name=row.customer_name,
                carrier_name=row.carrier_name,
                driver_name=row.driver_name,
                origin=_label(row.pickup_city, row.pickup_state),
                destination=_label(row.destination_city, row.destination_state),
                current_position_label=None,
                pickup_appointment=row.pickup_appointment_start,
                facts=facts,
                view=view,
            )
        )

    board.sort(key=lambda item: (item.priority, item.reference))
    return board
