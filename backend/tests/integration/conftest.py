"""Fixtures for tests that require a real PostgreSQL server.

PostgreSQL is not optional here: the behaviours under test are unique
constraints, advisory locks, ``ON CONFLICT`` semantics, and
``FOR UPDATE SKIP LOCKED``. SQLite cannot stand in for any of them.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text

from relayops.migrations import run_migrations

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://relayops:relayops@localhost:55432/relayops_test"
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def migration_directory() -> Path:
    return MIGRATIONS_DIR


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _test_database_url()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"PostgreSQL is unavailable at {url}: {exc}")
    finally:
        engine.dispose()
    return url


@pytest.fixture
def postgres_engine(database_url: str) -> Iterator[Engine]:
    """A clean, empty ``public`` schema for one test."""
    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(text("drop schema if exists public cascade"))
        connection.execute(text("create schema public"))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def migrated_engine(postgres_engine: Engine, migration_directory: Path) -> Engine:
    run_migrations(postgres_engine, migration_directory)
    return postgres_engine


@pytest.fixture
def migrated_connection(migrated_engine: Engine):
    with migrated_engine.connect() as connection:
        yield connection
        connection.rollback()
