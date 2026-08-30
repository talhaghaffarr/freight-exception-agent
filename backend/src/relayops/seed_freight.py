"""Deterministic freight demo data.

Every row is derived from a stable id and a fixed offset from the seed moment,
so the console always looks live without the data ever being random: the same
seed run twice produces the same board, and a demo recorded today reproduces
tomorrow.

The set is chosen to exercise the honesty rules rather than to look tidy. It
contains loads whose ETA cannot be computed, a pickup that is merely at risk
rather than late, and the same load reference in two tenants so cross-tenant
scoping is visible instead of asserted.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, text

from relayops.domain.identity import stable_id

ATLAS = stable_id("tenant", "atlas-brokerage")
MERIDIAN = stable_id("tenant", "meridian-freight")

# Coordinates are city centroids; this is synthetic freight, not a GPS replay.
CITIES: dict[str, tuple[float, float]] = {
    "Chicago, IL": (41.8781, -87.6298),
    "Dallas, TX": (32.7767, -96.7970),
    "Detroit, MI": (42.3314, -83.0458),
    "Nashville, TN": (36.1627, -86.7816),
    "Columbus, OH": (39.9612, -82.9988),
    "Memphis, TN": (35.1495, -90.0490),
    "Atlanta, GA": (33.7490, -84.3880),
    "Orlando, FL": (28.5383, -81.3792),
    "Louisville, KY": (38.2527, -85.7585),
    "Charlotte, NC": (35.2271, -80.8431),
    "Savannah, GA": (32.0809, -81.0912),
    "Birmingham, AL": (33.5186, -86.8104),
    "Kansas City, MO": (39.0997, -94.5786),
    "Denver, CO": (39.7392, -104.9903),
    "Phoenix, AZ": (33.4484, -112.0740),
    "Indianapolis, IN": (39.7684, -86.1581),
    "St. Louis, MO": (38.6270, -90.1994),
    "Oklahoma City, OK": (35.4676, -97.5164),
    "Little Rock, AR": (34.7465, -92.2896),
    "Springfield, MO": (37.2153, -93.2982),
    "Omaha, NE": (41.2565, -95.9345),
    "Tulsa, OK": (36.1540, -95.9928),
    "Cincinnati, OH": (39.1031, -84.5120),
    "Richmond, VA": (37.5407, -77.4360),
    "Jacksonville, FL": (30.3322, -81.6557),
    "Houston, TX": (29.7604, -95.3698),
}


@dataclass(frozen=True, slots=True)
class LoadSpec:
    """One synthetic load, described by offsets from the seed moment."""

    reference: str
    origin: str
    destination: str
    customer: str
    carrier: str
    driver: str
    driver_phone: str
    #: Minutes from "now" until the pickup appointment. Negative means past.
    appointment_in: int
    #: Age of the newest tracking point, or ``None`` for a load with no signal.
    tracking_age: int | None
    #: Remaining drive time to the pickup, the input to the computed ETA.
    remaining_minutes: int
    #: Where the truck currently is, for the map and the position label.
    position: str
    status: str = "active"
    pickup_complete: bool = False
    arrived_at_dock: int | None = None
    tenant_id: uuid.UUID = ATLAS
    account_manager: str = "Dana Reyes"
    account_manager_email: str = "dana.reyes@atlasbrokerage.demo"


# The signature loads. Each one exists to make a specific behaviour visible.
SIGNATURE_LOADS: tuple[LoadSpec, ...] = (
    # Late beyond the threshold: ETA 38 minutes past a 17-minute-away appointment.
    LoadSpec(
        reference="LD-1048",
        origin="Chicago, IL",
        destination="Dallas, TX",
        customer="ACME Retail",
        carrier="BlueLine Logistics",
        driver="R. Okafor",
        driver_phone="+15555550142",
        appointment_in=17,
        tracking_age=2,
        remaining_minutes=55,
        position="Springfield, MO",
    ),
    # No signal at all: the ETA must be unknown, never estimated.
    LoadSpec(
        reference="LD-1051",
        origin="Detroit, MI",
        destination="Nashville, TN",
        customer="Northwind Foods",
        carrier="NorthStar Carriers",
        driver="J. Alvarez",
        driver_phone="+15555550188",
        appointment_in=47,
        tracking_age=42,
        remaining_minutes=40,
        position="Indianapolis, IN",
    ),
    # Late, but by less than LD-1048: proves the threshold is a real comparison.
    LoadSpec(
        reference="LD-1062",
        origin="Columbus, OH",
        destination="Memphis, TN",
        customer="Vertex Industrial",
        carrier="Arrow Freight",
        driver="M. Chen",
        driver_phone="+15555550120",
        appointment_in=92,
        tracking_age=5,
        remaining_minutes=114,
        position="Cincinnati, OH",
    ),
    # Pickup already done: nothing to alert on.
    LoadSpec(
        reference="LD-1068",
        origin="Atlanta, GA",
        destination="Orlando, FL",
        customer="Sunbelt Grocers",
        carrier="Rapid Transit Co",
        driver="T. Boone",
        driver_phone="+15555550166",
        appointment_in=-180,
        tracking_age=8,
        remaining_minutes=95,
        position="Jacksonville, FL",
        pickup_complete=True,
    ),
    # Tracking just past the maximum age: the honest-unknown boundary case.
    LoadSpec(
        reference="LD-1071",
        origin="Louisville, KY",
        destination="Charlotte, NC",
        customer="Piedmont Supply",
        carrier="Delta Line",
        driver="K. Novak",
        driver_phone="+15555550109",
        appointment_in=35,
        tracking_age=31,
        remaining_minutes=48,
        position="Cincinnati, OH",
    ),
    # At the dock and not departed: the detention shape, seeded for later.
    LoadSpec(
        reference="LD-1083",
        origin="Savannah, GA",
        destination="Birmingham, AL",
        customer="Harbor Materials",
        carrier="Coastal Freight",
        driver="P. Ibrahim",
        driver_phone="+15555550154",
        appointment_in=-92,
        tracking_age=3,
        remaining_minutes=0,
        position="Savannah, GA",
        pickup_complete=True,
        arrived_at_dock=92,
    ),
    # At risk but under the threshold: must NOT produce an alert.
    LoadSpec(
        reference="LD-1090",
        origin="Kansas City, MO",
        destination="Denver, CO",
        customer="Front Range Retail",
        carrier="BlueLine Logistics",
        driver="S. Whitfield",
        driver_phone="+15555550171",
        appointment_in=40,
        tracking_age=4,
        remaining_minutes=48,
        position="Omaha, NE",
    ),
    # Same reference as the Atlas flagship, in another tenant. Scoping is
    # demonstrated by this row existing, not by a claim in a README.
    LoadSpec(
        reference="LD-1048",
        origin="Phoenix, AZ",
        destination="Houston, TX",
        customer="Sonora Distribution",
        carrier="Cactus Line",
        driver="D. Marsh",
        driver_phone="+15555550133",
        appointment_in=25,
        tracking_age=6,
        remaining_minutes=70,
        position="Tulsa, OK",
        tenant_id=MERIDIAN,
        account_manager="Alex Kim",
        account_manager_email="alex.kim@meridianfreight.demo",
    ),
)

_FILLER_ROUTES: tuple[tuple[str, str, str, str], ...] = (
    ("Indianapolis, IN", "Nashville, TN", "Great Lakes Parts", "Arrow Freight"),
    ("St. Louis, MO", "Oklahoma City, OK", "Gateway Foods", "NorthStar Carriers"),
    ("Denver, CO", "Kansas City, MO", "Rocky Mountain Co-op", "Summit Haulers"),
    ("Memphis, TN", "Little Rock, AR", "Delta Provisions", "Rapid Transit Co"),
    ("Cincinnati, OH", "Richmond, VA", "Ohio Valley Supply", "Coastal Freight"),
    ("Omaha, NE", "Chicago, IL", "Prairie Agri", "BlueLine Logistics"),
    ("Tulsa, OK", "Dallas, TX", "Red River Materials", "Cactus Line"),
    ("Jacksonville, FL", "Atlanta, GA", "First Coast Retail", "Delta Line"),
    ("Houston, TX", "Phoenix, AZ", "Gulf Chemical", "Summit Haulers"),
    ("Charlotte, NC", "Savannah, GA", "Carolina Textiles", "Arrow Freight"),
)


def _filler_loads(count: int) -> tuple[LoadSpec, ...]:
    """On-track loads so the board has realistic volume around the exceptions.

    Offsets are derived from the index rather than drawn at random: the board
    looks varied and is still byte-identical between runs.
    """
    specs = []
    for index in range(count):
        origin, destination, customer, carrier = _FILLER_ROUTES[index % len(_FILLER_ROUTES)]
        specs.append(
            LoadSpec(
                reference=f"LD-2{index + 100:03d}",
                origin=origin,
                destination=destination,
                customer=customer,
                carrier=carrier,
                driver=f"Driver {index + 1:02d}",
                driver_phone=f"+1555555{2000 + index:04d}",
                appointment_in=90 + index * 37,
                tracking_age=1 + index % 9,
                remaining_minutes=25 + index % 40,
                position=list(CITIES)[index % len(CITIES)],
            )
        )
    return tuple(specs)


ALL_LOADS: tuple[LoadSpec, ...] = SIGNATURE_LOADS + _filler_loads(41)


def _haversine_meters(a: tuple[float, float], b: tuple[float, float]) -> int:
    """Great-circle distance, used only to give the route a plausible length."""
    from math import asin, cos, radians, sin, sqrt

    lat1, lon1 = radians(a[0]), radians(a[1])
    lat2, lon2 = radians(b[0]), radians(b[1])
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return int(2 * 6_371_000 * asin(sqrt(h)))


@dataclass(frozen=True, slots=True)
class FreightSeedSummary:
    loads: int
    stops: int
    tracking_points: int


def seed_freight(connection: Connection, now: datetime | None = None) -> FreightSeedSummary:
    """Upsert the demo freight set.

    Like the identity seed this is an upsert keyed on (tenant, reference), so
    re-running it repairs the demo rows in place and never truncates a table an
    operator may have added to.
    """
    moment = (now or datetime.now(UTC)).replace(microsecond=0)
    loads = stops = points = 0

    for spec in ALL_LOADS:
        load_id = stable_id("load", f"{spec.tenant_id}:{spec.reference}")
        origin = CITIES[spec.origin]
        destination = CITIES[spec.destination]
        position = CITIES[spec.position]
        tracked_at = (
            None if spec.tracking_age is None else moment - timedelta(minutes=spec.tracking_age)
        )

        connection.execute(
            text(
                """
                insert into loads (
                    id, tenant_id, reference, status, customer_name,
                    account_manager_email, account_manager_name, carrier_name,
                    driver_name, driver_phone,
                    latest_tracking_at, latest_latitude, latest_longitude
                ) values (
                    :id, :tenant, :reference, :status, :customer,
                    :am_email, :am_name, :carrier, :driver, :phone,
                    :tracked_at, :lat, :lon
                )
                on conflict (tenant_id, reference) do update set
                    status = excluded.status,
                    customer_name = excluded.customer_name,
                    account_manager_email = excluded.account_manager_email,
                    account_manager_name = excluded.account_manager_name,
                    carrier_name = excluded.carrier_name,
                    driver_name = excluded.driver_name,
                    driver_phone = excluded.driver_phone,
                    latest_tracking_at = excluded.latest_tracking_at,
                    latest_latitude = excluded.latest_latitude,
                    latest_longitude = excluded.latest_longitude,
                    updated_at = now()
                """
            ),
            {
                "id": load_id,
                "tenant": spec.tenant_id,
                "reference": spec.reference,
                "status": spec.status,
                "customer": spec.customer,
                "am_email": spec.account_manager_email,
                "am_name": spec.account_manager,
                "carrier": spec.carrier,
                "driver": spec.driver,
                "phone": spec.driver_phone,
                "tracked_at": tracked_at,
                "lat": None if tracked_at is None else position[0],
                "lon": None if tracked_at is None else position[1],
            },
        )
        loads += 1

        appointment = moment + timedelta(minutes=spec.appointment_in)
        for sequence, (stop_type, label, coords, appt) in enumerate(
            (
                ("pickup", spec.origin, origin, appointment),
                ("delivery", spec.destination, destination, appointment + timedelta(hours=14)),
            ),
            start=1,
        ):
            city, state = label.split(", ")
            completed = (
                moment - timedelta(minutes=spec.arrived_at_dock or 20)
                if stop_type == "pickup" and spec.pickup_complete
                else None
            )
            arrived = (
                moment - timedelta(minutes=spec.arrived_at_dock)
                if stop_type == "pickup" and spec.arrived_at_dock is not None
                else completed
            )
            suffix = "Distribution Center" if stop_type == "pickup" else "Receiving"
            facility = f"{spec.customer} {suffix}"
            connection.execute(
                text(
                    """
                    insert into stops (
                        id, tenant_id, load_id, sequence, stop_type, facility_name,
                        city, state, latitude, longitude, timezone,
                        appointment_revision, appointment_start, appointment_end,
                        arrived_at, departed_at, completed_at
                    ) values (
                        :id, :tenant, :load, :sequence, :stop_type, :facility,
                        :city, :state, :lat, :lon, :tz,
                        :revision, :appt_start, :appt_end,
                        :arrived, :departed, :completed
                    )
                    on conflict (load_id, sequence) do update set
                        appointment_start = excluded.appointment_start,
                        appointment_end = excluded.appointment_end,
                        arrived_at = excluded.arrived_at,
                        departed_at = excluded.departed_at,
                        completed_at = excluded.completed_at,
                        updated_at = now()
                    """
                ),
                {
                    "id": stable_id("stop", f"{load_id}:{sequence}"),
                    "tenant": spec.tenant_id,
                    "load": load_id,
                    "sequence": sequence,
                    "stop_type": stop_type,
                    "facility": facility,
                    "city": city,
                    "state": state,
                    "lat": coords[0],
                    "lon": coords[1],
                    "tz": "America/Chicago",
                    "revision": 3 if spec.reference == "LD-1048" else 1,
                    "appt_start": appt,
                    "appt_end": appt + timedelta(hours=1),
                    "arrived": arrived,
                    "departed": None,
                    "completed": completed,
                },
            )
            stops += 1

        # The leg carries the remaining route the ETA is computed from.
        connection.execute(
            text(
                """
                insert into legs (
                    id, tenant_id, load_id, sequence, origin_stop_id,
                    destination_stop_id, distance_meters, expected_duration_seconds
                ) values (
                    :id, :tenant, :load, 1, :origin_stop, :destination_stop,
                    :distance, :duration
                )
                on conflict (load_id, sequence) do update set
                    distance_meters = excluded.distance_meters,
                    expected_duration_seconds = excluded.expected_duration_seconds
                """
            ),
            {
                "id": stable_id("leg", f"{load_id}:1"),
                "tenant": spec.tenant_id,
                "load": load_id,
                "origin_stop": stable_id("stop", f"{load_id}:1"),
                "destination_stop": stable_id("stop", f"{load_id}:2"),
                "distance": _haversine_meters(position, origin),
                "duration": spec.remaining_minutes * 60,
            },
        )

        if tracked_at is not None:
            connection.execute(
                text(
                    """
                    insert into tracking_points (
                        id, tenant_id, load_id, recorded_at, latitude, longitude,
                        source, source_event_id
                    ) values (
                        :id, :tenant, :load, :recorded_at, :lat, :lon, 'eld', :event_id
                    )
                    on conflict (source, source_event_id) do update set
                        recorded_at = excluded.recorded_at,
                        latitude = excluded.latitude,
                        longitude = excluded.longitude
                    """
                ),
                {
                    "id": stable_id("tracking", f"{load_id}:latest"),
                    "tenant": spec.tenant_id,
                    "load": load_id,
                    "recorded_at": tracked_at,
                    "lat": position[0],
                    "lon": position[1],
                    "event_id": f"seed:{load_id}:latest",
                },
            )
            points += 1

    return FreightSeedSummary(loads=loads, stops=stops, tracking_points=points)
