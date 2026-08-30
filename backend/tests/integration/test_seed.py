import pytest
from sqlalchemy import text

from relayops.seed import DEMO_USERS, seed_demo_data

pytestmark = pytest.mark.integration


def test_seed_is_repeatable_and_idempotent(migrated_connection):
    first = seed_demo_data(migrated_connection, seed=1048)
    second = seed_demo_data(migrated_connection, seed=1048)
    assert first.tenants == 2
    assert second == first


def test_seed_creates_the_documented_demo_identities(migrated_connection):
    seed_demo_data(migrated_connection, seed=1048)
    slugs = (
        migrated_connection.execute(text("select slug from tenants order by slug"))
        .scalars()
        .all()
    )
    emails = (
        migrated_connection.execute(text("select email from users order by email"))
        .scalars()
        .all()
    )
    assert slugs == ["atlas-brokerage", "meridian-freight"]
    assert emails == sorted(user.email for user in DEMO_USERS)


def test_seed_ids_are_stable_across_a_rebuilt_database(postgres_engine, migration_directory):
    from relayops.migrations import run_migrations

    def ids() -> list[str]:
        run_migrations(postgres_engine, migration_directory)
        with postgres_engine.begin() as connection:
            seed_demo_data(connection)
        with postgres_engine.connect() as connection:
            return [
                str(value)
                for value in connection.execute(
                    text("select id from tenants order by slug")
                ).scalars()
            ]

    before = ids()
    with postgres_engine.begin() as connection:
        connection.exec_driver_sql("drop schema public cascade; create schema public;")
    after = ids()
    assert before == after


def test_seed_does_not_truncate_tenant_owned_rows(migrated_connection):
    seed_demo_data(migrated_connection)
    migrated_connection.execute(
        text("insert into tenants (slug, name) values ('operator-added', 'Operator Added')")
    )
    seed_demo_data(migrated_connection)
    survived = migrated_connection.execute(
        text("select count(*) from tenants where slug = 'operator-added'")
    ).scalar_one()
    assert survived == 1


def test_seed_repairs_a_drifted_demo_row(migrated_connection):
    seed_demo_data(migrated_connection)
    migrated_connection.execute(
        text("update tenants set name = 'Renamed By Hand' where slug = 'atlas-brokerage'")
    )
    seed_demo_data(migrated_connection)
    name = migrated_connection.execute(
        text("select name from tenants where slug = 'atlas-brokerage'")
    ).scalar_one()
    assert name == "Atlas Brokerage"


def test_platform_operator_has_no_tenant_membership(migrated_connection):
    seed_demo_data(migrated_connection)
    rows = migrated_connection.execute(
        text(
            "select count(*) from tenant_memberships m "
            "join users u on u.id = m.user_id where u.is_platform_operator"
        )
    ).scalar_one()
    assert rows == 0
