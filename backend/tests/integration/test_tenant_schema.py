import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


def insert_tenant(connection, slug="atlas-brokerage"):
    return connection.execute(
        text("insert into tenants (slug, name) values (:slug, :name) returning id"),
        {"slug": slug, "name": slug.replace("-", " ").title()},
    ).scalar_one()


def insert_user(connection, email="ops@atlas.example"):
    return connection.execute(
        text(
            "insert into users (email, display_name) values (:email, :name) returning id"
        ),
        {"email": email, "name": "Demo User"},
    ).scalar_one()


def insert_membership(connection, tenant_id, user_id, role):
    return connection.execute(
        text(
            "insert into tenant_memberships (tenant_id, user_id, role) "
            "values (:tenant_id, :user_id, :role) returning id"
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "role": role},
    ).scalar_one()


def insert_tenant_and_user(connection):
    return insert_tenant(connection), insert_user(connection)


def test_membership_is_unique_per_user_and_tenant(migrated_connection):
    tenant_id, user_id = insert_tenant_and_user(migrated_connection)
    insert_membership(migrated_connection, tenant_id, user_id, "reviewer")
    with pytest.raises(IntegrityError):
        insert_membership(migrated_connection, tenant_id, user_id, "account_manager")


def test_tenant_slug_is_unique(migrated_connection):
    insert_tenant(migrated_connection, "atlas-brokerage")
    with pytest.raises(IntegrityError):
        insert_tenant(migrated_connection, "atlas-brokerage")


def test_tenant_slug_must_be_kebab_case(migrated_connection):
    with pytest.raises(IntegrityError):
        insert_tenant(migrated_connection, "Atlas Brokerage")


def test_user_email_is_unique(migrated_connection):
    insert_user(migrated_connection, "ops@atlas.example")
    with pytest.raises(IntegrityError):
        insert_user(migrated_connection, "ops@atlas.example")


def test_membership_role_is_constrained(migrated_connection):
    tenant_id, user_id = insert_tenant_and_user(migrated_connection)
    with pytest.raises(IntegrityError):
        insert_membership(migrated_connection, tenant_id, user_id, "superuser")


def test_deleting_a_tenant_cascades_to_memberships(migrated_engine):
    with migrated_engine.begin() as connection:
        tenant_id, user_id = insert_tenant_and_user(connection)
        insert_membership(connection, tenant_id, user_id, "brokerage_admin")
    with migrated_engine.begin() as connection:
        connection.execute(text("delete from tenants where id = :id"), {"id": tenant_id})
    with migrated_engine.connect() as connection:
        remaining = connection.execute(
            text("select count(*) from tenant_memberships where tenant_id = :id"),
            {"id": tenant_id},
        ).scalar_one()
        user_still_there = connection.execute(
            text("select count(*) from users where id = :id"), {"id": user_id}
        ).scalar_one()
    assert remaining == 0
    assert user_still_there == 1


def test_audit_events_record_actor_and_value_change(migrated_engine):
    with migrated_engine.begin() as connection:
        tenant_id, user_id = insert_tenant_and_user(connection)
        connection.execute(
            text(
                "insert into audit_events "
                "(tenant_id, actor_user_id, actor_label, action, subject_type, subject_id, "
                " reason, old_value, new_value, request_id) "
                "values (:t, :u, :label, :action, :st, :sid, :reason, :old, :new, :rid)"
            ),
            {
                "t": tenant_id,
                "u": user_id,
                "label": "ops@atlas.example",
                "action": "tenant_agent_config.updated",
                "st": "tenant_agent_config",
                "sid": str(uuid.uuid4()),
                "reason": "raise late threshold for peak season",
                "old": '{"late_threshold_minutes": 15}',
                "new": '{"late_threshold_minutes": 30}',
                "rid": "req_abc123",
            },
        )
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "select action, old_value ->> 'late_threshold_minutes', "
                "new_value ->> 'late_threshold_minutes' from audit_events"
            )
        ).one()
    assert row == ("tenant_agent_config.updated", "15", "30")
