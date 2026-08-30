"""Shared fixtures for RelayOps backend tests.

Tests that touch persistence run against a real PostgreSQL server. SQLite is not
an accepted substitute: the behaviours under test are unique constraints,
advisory locks, ``ON CONFLICT`` semantics, and ``FOR UPDATE SKIP LOCKED``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text

from relayops.app import create_app
from relayops.config import Settings
from relayops.migrations import run_migrations
from relayops.seed import seed_demo_data

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://relayops:relayops@localhost:55432/relayops_test"
DEFAULT_TEST_BROKER_URL = "redis://localhost:56379/0"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@pytest.fixture
def settings() -> Settings:
    return Settings.from_env(
        {
            "SECRET_KEY": "test-only-signing-key",
            "TESTING": "true",
            "CORS_ORIGINS": "http://localhost:5173",
        }
    )


@pytest.fixture
def app(settings: Settings):
    application = create_app(settings)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


# --- PostgreSQL-backed fixtures -----------------------------------------


@pytest.fixture(scope="session")
def migration_directory() -> Path:
    return MIGRATIONS_DIR


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
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
        connection.exec_driver_sql("drop schema if exists public cascade; create schema public;")
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


@pytest.fixture
def seeded_engine(migrated_engine: Engine) -> Engine:
    with migrated_engine.begin() as connection:
        seed_demo_data(connection)
    return migrated_engine


@pytest.fixture
def seeded_freight_engine(seeded_engine: Engine) -> Engine:
    """Identity seed plus the synthetic freight board."""
    from relayops.seed_freight import seed_freight

    with seeded_engine.begin() as connection:
        seed_freight(connection)
    return seeded_engine


@pytest.fixture
def seeded_freight_connection(seeded_freight_engine: Engine):
    with seeded_freight_engine.connect() as connection:
        yield connection
        connection.rollback()


@pytest.fixture
def seeded_history_engine(seeded_freight_engine: Engine) -> Engine:
    """Freight board plus the seeded agent history (goals, events, outcomes)."""
    from relayops.seed_history import seed_history

    with seeded_freight_engine.begin() as connection:
        seed_history(connection)
    return seeded_freight_engine


@pytest.fixture(scope="session")
def broker_url() -> str:
    return os.environ.get("TEST_BROKER_URL", DEFAULT_TEST_BROKER_URL)


@pytest.fixture
def db_settings(database_url: str, broker_url: str) -> Settings:
    return Settings.from_env(
        {
            "SECRET_KEY": "test-only-signing-key",
            "TESTING": "true",
            "DATABASE_URL": database_url,
            "CELERY_BROKER_URL": broker_url,
            "CELERY_RESULT_BACKEND": broker_url.rsplit("/", 1)[0] + "/1",
        }
    )


@pytest.fixture
def freight_api_app(seeded_freight_engine: Engine, db_settings: Settings):
    application = create_app(db_settings, engine=seeded_freight_engine)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def freight_api_client(freight_api_app):
    return freight_api_app.test_client()


@pytest.fixture
def history_api_app(seeded_history_engine: Engine, db_settings: Settings):
    application = create_app(db_settings, engine=seeded_history_engine)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def history_api_client(history_api_app):
    return history_api_app.test_client()


@pytest.fixture
def history_login_as(history_api_client):
    def _login(email: str):
        response = history_api_client.post("/api/v1/auth/demo-session", json={"email": email})
        assert response.status_code == 200, response.get_data(as_text=True)
        return response.get_json()["data"]

    return _login


@pytest.fixture
def api_app(seeded_engine: Engine, db_settings: Settings):
    application = create_app(db_settings, engine=seeded_engine)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def api_client(api_app):
    return api_app.test_client()


@pytest.fixture
def login_as(api_client):
    def _login(email: str):
        response = api_client.post("/api/v1/auth/demo-session", json={"email": email})
        assert response.status_code == 200, response.get_data(as_text=True)
        return response.get_json()["data"]

    return _login


@pytest.fixture
def freight_login_as(freight_api_client):
    def _login(email: str):
        response = freight_api_client.post("/api/v1/auth/demo-session", json={"email": email})
        assert response.status_code == 200, response.get_data(as_text=True)
        return response.get_json()["data"]

    return _login
