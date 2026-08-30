import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from relayops.migrations import (
    MigrationChecksumMismatch,
    check_migrations,
    run_migrations,
)

pytestmark = pytest.mark.integration


def test_migrations_apply_once(postgres_engine, migration_directory):
    first = run_migrations(postgres_engine, migration_directory)
    second = run_migrations(postgres_engine, migration_directory)
    assert first[0] == "001_foundation"
    assert second == []


def test_applied_migrations_are_recorded_with_a_checksum(postgres_engine, migration_directory):
    run_migrations(postgres_engine, migration_directory)
    with postgres_engine.connect() as connection:
        rows = connection.execute(
            text("select version, checksum from schema_migrations order by version")
        ).all()
    assert rows[0][0] == "001_foundation"
    assert len(rows[0][1]) == 64


def test_check_migrations_reports_pending_before_and_none_after(
    postgres_engine, migration_directory
):
    before = check_migrations(postgres_engine, migration_directory)
    assert before.pending
    assert before.is_current is False

    run_migrations(postgres_engine, migration_directory)

    after = check_migrations(postgres_engine, migration_directory)
    assert after.pending == []
    assert after.is_current is True


def test_editing_an_applied_migration_is_rejected(postgres_engine, migration_directory):
    run_migrations(postgres_engine, migration_directory)
    with postgres_engine.begin() as connection:
        connection.execute(
            text("update schema_migrations set checksum = :c where version = :v"),
            {"c": "0" * 64, "v": "001_foundation"},
        )

    with pytest.raises(MigrationChecksumMismatch, match="001_foundation"):
        run_migrations(postgres_engine, migration_directory)


def test_a_failing_migration_leaves_no_partial_schema(postgres_engine, tmp_path):
    (tmp_path / "001_ok.sql").write_text("create table alpha (id int primary key);")
    (tmp_path / "002_bad.sql").write_text(
        "create table beta (id int primary key);\nselect * from table_that_is_not_there;"
    )

    with pytest.raises(ProgrammingError):
        run_migrations(postgres_engine, tmp_path)

    with postgres_engine.connect() as connection:
        applied = connection.execute(text("select version from schema_migrations")).scalars().all()
        beta_exists = connection.execute(
            text("select to_regclass('public.beta') is not null")
        ).scalar()
    assert applied == ["001_ok"]
    assert beta_exists is False
