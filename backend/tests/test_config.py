import pytest

from relayops.config import Settings


def test_settings_default_to_sandbox():
    settings = Settings.from_env({})
    assert settings.environment_mode == "sandbox"
    assert settings.allow_live_sends is False


def test_settings_reject_live_mode_without_explicit_acknowledgement():
    with pytest.raises(ValueError, match="ALLOW_LIVE_SENDS"):
        Settings.from_env({"ENVIRONMENT_MODE": "live"})


def test_settings_allow_live_mode_when_acknowledged():
    settings = Settings.from_env({"ENVIRONMENT_MODE": "live", "ALLOW_LIVE_SENDS": "true"})
    assert settings.environment_mode == "live"
    assert settings.allow_live_sends is True


def test_settings_reject_unknown_environment_mode():
    with pytest.raises(ValueError):
        Settings.from_env({"ENVIRONMENT_MODE": "yolo"})


def test_settings_read_overrides_and_split_cors_origins():
    settings = Settings.from_env(
        {
            "DATABASE_URL": "postgresql+psycopg://u:p@db:5432/x",
            "CORS_ORIGINS": "http://localhost:5173, http://127.0.0.1:5173",
        }
    )
    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/x"
    assert settings.cors_origins == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_secret_key_is_not_exposed_by_repr():
    settings = Settings.from_env({"SECRET_KEY": "hunter2"})
    assert "hunter2" not in repr(settings)
    assert settings.secret_key.get_secret_value() == "hunter2"


class TestDatabaseUrlNormalisation:
    """Managed providers hand out generic Postgres URLs; the app must not
    require operators to know which SQLAlchemy driver suffix we compiled in."""

    def test_a_generic_postgresql_url_is_coerced_to_the_psycopg_driver(self):
        settings = Settings.from_env(
            {
                "SECRET_KEY": "x",
                "DATABASE_URL": "postgresql://u:p@ep-x.aws.neon.tech/db?sslmode=require",
            }
        )
        assert settings.database_url == (
            "postgresql+psycopg://u:p@ep-x.aws.neon.tech/db?sslmode=require"
        )

    def test_a_heroku_style_postgres_url_is_coerced_too(self):
        settings = Settings.from_env(
            {"SECRET_KEY": "x", "DATABASE_URL": "postgres://u:p@host/db"}
        )
        assert settings.database_url == "postgresql+psycopg://u:p@host/db"

    def test_an_explicit_driver_is_left_alone(self):
        url = "postgresql+psycopg://u:p@host/db"
        settings = Settings.from_env({"SECRET_KEY": "x", "DATABASE_URL": url})
        assert settings.database_url == url
