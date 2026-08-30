"""Validated runtime settings.

Settings are read once from the process environment and never mutated. The
safe-send switch lives here because it is the single control that decides
whether the platform is capable of contacting a real person.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

EnvironmentMode = Literal["sandbox", "allowlist", "live"]

_TRUE_VALUES = frozenset({"1", "true", "t", "yes", "y", "on"})
_FALSE_VALUES = frozenset({"", "0", "false", "f", "no", "n", "off"})


def _as_bool(raw: str | bool | None, *, field: str) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ValueError(f"{field} must be a boolean-like value, got {raw!r}")


def _normalise_database_url(url: str) -> str:
    """Coerce a generic Postgres URL onto the psycopg driver this app ships.

    Managed providers hand out ``postgresql://`` (Heroku-era tooling emits
    ``postgres://``); SQLAlchemy would resolve both to the psycopg2 driver,
    which is deliberately not installed. An explicit ``+driver`` is respected.
    """
    url = url.strip()
    if url.startswith("postgresql+") :
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


def _as_tuple(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


class Settings(BaseModel):
    """Immutable process configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    database_url: str = "postgresql+psycopg://relayops:relayops@postgres:5432/relayops"
    celery_broker_url: str = "redis://valkey:6379/0"
    celery_result_backend: str = "redis://valkey:6379/1"
    secret_key: SecretStr = SecretStr("local-demo-only-not-a-secret")
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)

    environment_mode: EnvironmentMode = "sandbox"
    allow_live_sends: bool = False
    allowlist_recipients: tuple[str, ...] = ()

    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    mailpit_ui_url: str = "http://localhost:8025"

    openai_api_key: SecretStr | None = None
    sendgrid_api_key: SecretStr | None = None
    osrm_base_url: str | None = None

    testing: bool = False
    #: A deployment with no worker fleet: only api/database/migrations probes
    #: register, so absent background services read as "not deployed", never
    #: as failures the header nags about.
    web_only: bool = False
    migrations_dir: str = Field(default="migrations")

    @model_validator(mode="after")
    def protect_live_mode(self) -> Settings:
        if self.environment_mode == "live" and not self.allow_live_sends:
            raise ValueError("ALLOW_LIVE_SENDS=true is required for live mode")
        if self.environment_mode == "allowlist" and not self.allowlist_recipients:
            raise ValueError("ALLOWLIST_RECIPIENTS must list at least one recipient")
        return self

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> Settings:
        """Build settings from an environment mapping, applying documented defaults."""

        def optional_secret(key: str) -> SecretStr | None:
            value = environ.get(key, "").strip()
            return SecretStr(value) if value else None

        provided: dict[str, object] = {
            "environment_mode": environ.get("ENVIRONMENT_MODE", "sandbox").strip() or "sandbox",
            "allow_live_sends": _as_bool(
                environ.get("ALLOW_LIVE_SENDS"), field="ALLOW_LIVE_SENDS"
            ),
            "allowlist_recipients": _as_tuple(environ.get("ALLOWLIST_RECIPIENTS")),
            "testing": _as_bool(environ.get("TESTING"), field="TESTING"),
            "web_only": _as_bool(environ.get("WEB_ONLY"), field="WEB_ONLY"),
            "openai_api_key": optional_secret("OPENAI_API_KEY"),
            "sendgrid_api_key": optional_secret("SENDGRID_API_KEY"),
            "osrm_base_url": environ.get("OSRM_BASE_URL", "").strip() or None,
        }

        if raw_db := environ.get("DATABASE_URL"):
            provided["database_url"] = _normalise_database_url(raw_db)

        for field, key in (
            ("celery_broker_url", "CELERY_BROKER_URL"),
            ("celery_result_backend", "CELERY_RESULT_BACKEND"),
            ("smtp_host", "SMTP_HOST"),
            ("mailpit_ui_url", "MAILPIT_UI_URL"),
            ("migrations_dir", "MIGRATIONS_DIR"),
        ):
            value = environ.get(key)
            if value:
                provided[field] = value

        if secret := environ.get("SECRET_KEY"):
            provided["secret_key"] = SecretStr(secret)
        if origins := environ.get("CORS_ORIGINS"):
            provided["cors_origins"] = _as_tuple(origins)
        if port := environ.get("SMTP_PORT"):
            provided["smtp_port"] = int(port)

        return cls(**provided)

    @property
    def can_reach_external_recipients(self) -> bool:
        """True only when configuration permits contacting a non-local address."""
        return self.environment_mode != "sandbox"
