"""Concrete health probes for each platform component.

Probes answer with evidence — latency, freshness, counts — not with a boolean.
A probe never raises into the caller: ``collect_health`` contains failures and
reports them as ``unhealthy`` without leaking connection strings.
"""

from __future__ import annotations

import socket
import time
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from relayops.config import Settings
from relayops.db import migrations_path
from relayops.health import ComponentHealth
from relayops.migrations import check_migrations

# A Beat heartbeat older than this means the schedule has stopped advancing.
BEAT_HEARTBEAT_KEY = "relayops:beat:heartbeat"
BEAT_STALE_AFTER_SECONDS = 120
WORKER_PING_TIMEOUT_SECONDS = 1.0


class ApiProbe:
    name = "api"
    required = True

    def check(self) -> ComponentHealth:
        return ComponentHealth(name=self.name, status="healthy", required=True)


class DatabaseProbe:
    name = "database"
    required = True

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check(self) -> ComponentHealth:
        started = time.perf_counter()
        with self._engine.connect() as connection:
            connection.execute(text("select 1"))
            in_use = self._engine.pool.checkedout()
        latency_ms = (time.perf_counter() - started) * 1000
        return ComponentHealth(
            name=self.name,
            status="healthy" if latency_ms < 500 else "degraded",
            required=True,
            detail=None if latency_ms < 500 else "database round trip is slow",
            latency_ms=latency_ms,
            metadata={"pool_checked_out": in_use},
        )


class MigrationsProbe:
    """Readiness must fail while the schema is behind the code."""

    name = "migrations"
    required = True

    def __init__(self, engine: Engine, settings: Settings) -> None:
        self._engine = engine
        self._settings = settings

    def check(self) -> ComponentHealth:
        status = check_migrations(self._engine, migrations_path(self._settings))
        if status.mismatched:
            return ComponentHealth(
                name=self.name,
                status="unhealthy",
                required=True,
                detail=f"{len(status.mismatched)} applied migration(s) changed on disk",
                metadata={"mismatched": status.mismatched},
            )
        if status.pending:
            return ComponentHealth(
                name=self.name,
                status="unhealthy",
                required=True,
                detail=f"{len(status.pending)} migration(s) pending",
                metadata={"pending": status.pending},
            )
        return ComponentHealth(
            name=self.name,
            status="healthy",
            required=True,
            metadata={"applied": len(status.applied)},
        )


class ValkeyProbe:
    name = "valkey"
    required = True

    def __init__(self, broker_url: str) -> None:
        self._broker_url = broker_url

    def check(self) -> ComponentHealth:
        import redis

        started = time.perf_counter()
        client = redis.Redis.from_url(self._broker_url, socket_connect_timeout=1)
        try:
            client.ping()
        finally:
            client.close()
        return ComponentHealth(
            name=self.name,
            status="healthy",
            required=True,
            latency_ms=(time.perf_counter() - started) * 1000,
        )


class WorkerProbe:
    """Ask the broker which workers answer, rather than assuming any do."""

    name = "worker"
    required = False

    def __init__(self, celery_app) -> None:
        self._celery_app = celery_app

    def check(self) -> ComponentHealth:
        replies = self._celery_app.control.ping(timeout=WORKER_PING_TIMEOUT_SECONDS) or []
        if not replies:
            return ComponentHealth(
                name=self.name,
                status="unknown",
                detail="no worker answered within 1s",
                metadata={"workers": 0},
            )
        hostnames = sorted(name for reply in replies for name in reply)
        return ComponentHealth(
            name=self.name,
            status="healthy",
            metadata={"workers": len(hostnames), "hostnames": hostnames},
        )


class BeatProbe:
    """Beat writes a heartbeat key; a missing or stale key is not a crash."""

    name = "beat"
    required = False

    def __init__(self, broker_url: str) -> None:
        self._broker_url = broker_url

    def check(self) -> ComponentHealth:
        import redis

        client = redis.Redis.from_url(self._broker_url, socket_connect_timeout=1)
        try:
            raw = client.get(BEAT_HEARTBEAT_KEY)
        finally:
            client.close()

        if raw is None:
            return ComponentHealth(
                name=self.name, status="unknown", detail="no heartbeat recorded yet"
            )
        beat_at = datetime.fromisoformat(raw.decode())
        age_seconds = (datetime.now(UTC) - beat_at).total_seconds()
        stale = age_seconds > BEAT_STALE_AFTER_SECONDS
        return ComponentHealth(
            name=self.name,
            status="degraded" if stale else "healthy",
            detail=f"last heartbeat {int(age_seconds)}s ago" if stale else None,
            metadata={"last_heartbeat": beat_at.isoformat(), "age_seconds": int(age_seconds)},
        )


class SmtpProbe:
    """Mailpit in sandbox mode. Optional: email failure must not fail readiness."""

    name = "email"
    required = False

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    def check(self) -> ComponentHealth:
        started = time.perf_counter()
        try:
            with socket.create_connection((self._host, self._port), timeout=1):
                pass
        except OSError:
            return ComponentHealth(
                name=self.name,
                status="unhealthy",
                detail=f"cannot reach the SMTP sink on port {self._port}",
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        return ComponentHealth(
            name=self.name,
            status="healthy",
            latency_ms=(time.perf_counter() - started) * 1000,
            metadata={"host": self._host, "port": self._port},
        )
