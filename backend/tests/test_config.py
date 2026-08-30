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
