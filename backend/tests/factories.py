"""Row builders for integration tests.

These write raw SQL on purpose: the point of most of these tests is what
PostgreSQL rejects, so going through a repository would test the repository
instead of the constraint.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

NOW = datetime(2026, 8, 30, 14, 43, tzinfo=UTC)


def insert_tenant(connection, slug: str = "atlas-brokerage", name: str | None = None):
    return connection.execute(
        text("insert into tenants (slug, name) values (:slug, :name) returning id"),
        {"slug": slug, "name": name or slug.replace("-", " ").title()},
    ).scalar_one()


def insert_two_tenants(connection):
    return insert_tenant(connection, "atlas-brokerage"), insert_tenant(
        connection, "meridian-freight"
    )


def insert_load(
    connection,
    tenant_id,
    reference: str = "LD-1048",
    *,
    status: str = "active",
    account_manager_email: str = "dana@atlas.demo",
    latest_tracking_at: datetime | None = None,
    latest_latitude: float | None = None,
    latest_longitude: float | None = None,
):
    return connection.execute(
        text(
            """
            insert into loads (
                tenant_id, reference, status, customer_name,
                account_manager_email, account_manager_name, carrier_name,
                driver_name, driver_phone,
                latest_tracking_at, latest_latitude, latest_longitude
            ) values (
                :tenant_id, :reference, :status, 'Northwind Foods',
                :am_email, 'Dana Okafor', 'Bluebird Carriers',
                'R. Alvarez', '+15125550142',
                :tracking_at, :lat, :lon
            ) returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "reference": reference,
            "status": status,
            "am_email": account_manager_email,
            "tracking_at": latest_tracking_at,
            "lat": latest_latitude,
            "lon": latest_longitude,
        },
    ).scalar_one()


def insert_stop(
    connection,
    tenant_id,
    load_id,
    *,
    sequence: int = 1,
    stop_type: str = "pickup",
    appointment_start: datetime | None = None,
    appointment_end: datetime | None = None,
    arrived_at: datetime | None = None,
    departed_at: datetime | None = None,
    completed_at: datetime | None = None,
    latitude: float = 32.7767,
    longitude: float = -96.797,
    timezone: str = "America/Chicago",
):
    appointment_start = appointment_start or (NOW + timedelta(minutes=17))
    return connection.execute(
        text(
            """
            insert into stops (
                tenant_id, load_id, sequence, stop_type, facility_name,
                city, state, latitude, longitude, timezone,
                appointment_start, appointment_end,
                arrived_at, departed_at, completed_at
            ) values (
                :tenant_id, :load_id, :sequence, :stop_type, 'Dallas Cold Storage',
                'Dallas', 'TX', :latitude, :longitude, :timezone,
                :appointment_start, :appointment_end,
                :arrived_at, :departed_at, :completed_at
            ) returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "load_id": load_id,
            "sequence": sequence,
            "stop_type": stop_type,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "appointment_start": appointment_start,
            "appointment_end": appointment_end or appointment_start + timedelta(hours=2),
            "arrived_at": arrived_at,
            "departed_at": departed_at,
            "completed_at": completed_at,
        },
    ).scalar_one()


def insert_tracking_point(
    connection,
    tenant_id,
    load_id,
    *,
    recorded_at: datetime | None = None,
    latitude: float = 32.9,
    longitude: float = -96.9,
    source: str = "eld",
    source_event_id: str | None = None,
):
    return connection.execute(
        text(
            """
            insert into tracking_points (
                tenant_id, load_id, recorded_at, latitude, longitude, source, source_event_id
            ) values (
                :tenant_id, :load_id, :recorded_at, :latitude, :longitude, :source, :source_event_id
            ) returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "load_id": load_id,
            "recorded_at": recorded_at or NOW - timedelta(minutes=3),
            "latitude": latitude,
            "longitude": longitude,
            "source": source,
            "source_event_id": source_event_id or str(uuid.uuid4()),
        },
    ).scalar_one()


def insert_goal(
    connection,
    tenant_id,
    *,
    subject_id,
    load_id=None,
    trigger: str = "pickup:1:appointment:1:late:v1",
    agent_type: str = "late_pickup_alert",
    agent_version: str = "1.0.0",
    subject_type: str = "stop",
    state: str = "opened",
    terminal_outcome: str | None = None,
):
    return connection.execute(
        text(
            """
            insert into goals (
                tenant_id, agent_type, agent_version, subject_type, subject_id,
                trigger_fingerprint, load_id, state, terminal_outcome
            ) values (
                :tenant_id, :agent_type, :agent_version, :subject_type, :subject_id,
                :trigger, :load_id, :state, :terminal_outcome
            ) returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "agent_type": agent_type,
            "agent_version": agent_version,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "trigger": trigger,
            "load_id": load_id,
            "state": state,
            "terminal_outcome": terminal_outcome,
        },
    ).scalar_one()


def insert_action(
    connection,
    tenant_id,
    goal_id,
    *,
    action_kind: str = "email",
    recipient: str = "dana@atlas.demo",
    recipient_fingerprint: str = "email:dana@atlas.demo",
    action_fingerprint: str = "late-pickup-alert:v1",
    state: str = "pending",
):
    return connection.execute(
        text(
            """
            insert into actions (
                tenant_id, goal_id, action_kind, recipient, recipient_fingerprint,
                action_fingerprint, template_key, template_version, idempotency_key, state
            ) values (
                :tenant_id, :goal_id, :action_kind, :recipient, :recipient_fingerprint,
                :action_fingerprint, 'late_pickup', '1.0.0', :idempotency_key, :state
            ) returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "goal_id": goal_id,
            "action_kind": action_kind,
            "recipient": recipient,
            "recipient_fingerprint": recipient_fingerprint,
            "action_fingerprint": action_fingerprint,
            "idempotency_key": f"{goal_id}:{action_kind}:{action_fingerprint}",
            "state": state,
        },
    ).scalar_one()
