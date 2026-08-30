"""Health and readiness.

Health is public because it carries no tenant data. Readiness is the signal a
load balancer uses: it fails while a required component cannot prove itself,
including while a migration is pending.
"""

from __future__ import annotations

from flask import Blueprint, current_app

from relayops.api.deps import get_engine
from relayops.config import Settings
from relayops.errors import error_response, ok
from relayops.health import HealthProbe, collect_health
from relayops.probes import (
    ApiProbe,
    BeatProbe,
    DatabaseProbe,
    MigrationsProbe,
    SmtpProbe,
    ValkeyProbe,
    WorkerProbe,
)

bp = Blueprint("system_health", __name__)


def build_probes() -> list[HealthProbe]:
    settings: Settings = current_app.config["SETTINGS"]
    engine = get_engine()
    probes: list[HealthProbe] = [
        ApiProbe(),
        DatabaseProbe(engine),
        MigrationsProbe(engine, settings),
    ]
    if settings.web_only:
        # No worker fleet is deployed here; probing for one would report
        # honest infrastructure as an outage.
        return probes
    probes += [
        ValkeyProbe(settings.celery_broker_url),
        BeatProbe(settings.celery_broker_url),
        SmtpProbe(settings.smtp_host, settings.smtp_port),
    ]

    celery_app = current_app.extensions.get("relayops_celery")
    if celery_app is not None:
        probes.append(WorkerProbe(celery_app))
    return probes


@bp.get("/system/health")
def read_health():
    report = collect_health(build_probes())
    return ok(report.as_dict())


@bp.get("/system/readiness")
def read_readiness():
    report = collect_health(build_probes())
    if not report.ready:
        unready = [
            component.name
            for component in report.components
            if component.required and component.status in {"unhealthy", "unknown"}
        ]
        return error_response(
            "NOT_READY",
            "A required component is not ready to serve traffic.",
            503,
            {"components": unready, "status": report.status},
        )
    return ok({"ready": True, "status": report.status})
