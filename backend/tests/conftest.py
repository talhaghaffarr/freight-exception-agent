"""Shared fixtures for RelayOps backend tests."""

from __future__ import annotations

import pytest

from relayops.app import create_app
from relayops.config import Settings


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
