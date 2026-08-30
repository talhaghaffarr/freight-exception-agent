"""Celery application.

Delivery is at-least-once by design. Tasks acknowledge late, a lost worker
rejects its message back onto the queue, and prefetch is one so a crashed worker
strands at most one message. Every task in this codebase must therefore be safe
to replay from any state — correctness comes from database constraints, not from
a worker remembering what it already did.
"""

from __future__ import annotations

from datetime import timedelta

from celery import Celery
from kombu import Queue

from relayops.config import Settings

# Queues are separated by failure appetite, not by agent type: a slow provider
# call must never delay a scanner, and maintenance must never delay either.
QUEUE_DEFAULT = "default"
QUEUE_SCANNERS = "scanners"
QUEUE_ACTIONS = "actions"
QUEUE_MAINTENANCE = "maintenance"

TASK_ROUTES = {
    "relayops.health.*": {"queue": QUEUE_MAINTENANCE},
    "relayops.maintenance.*": {"queue": QUEUE_MAINTENANCE},
    "relayops.scanners.*": {"queue": QUEUE_SCANNERS},
    "relayops.actions.*": {"queue": QUEUE_ACTIONS},
    "relayops.goals.*": {"queue": QUEUE_DEFAULT},
}

TASK_MODULES = ("relayops.tasks.health",)

BEAT_SCHEDULE = {
    "beat-heartbeat": {
        "task": "relayops.health.heartbeat",
        "schedule": timedelta(seconds=30),
        "options": {"queue": QUEUE_MAINTENANCE, "expires": 60},
    },
}


def build_celery_app(settings: Settings | None = None) -> Celery:
    settings = settings or Settings.from_env({})

    app = Celery("relayops", broker=settings.celery_broker_url)
    app.conf.update(
        result_backend=settings.celery_result_backend,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        # At-least-once delivery.
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_track_started=True,
        task_time_limit=300,
        task_soft_time_limit=270,
        result_expires=3600,
        broker_transport_options={"visibility_timeout": 600},
        worker_max_tasks_per_child=500,
        task_default_queue=QUEUE_DEFAULT,
        task_queues=[
            Queue(QUEUE_DEFAULT),
            Queue(QUEUE_SCANNERS),
            Queue(QUEUE_ACTIONS),
            Queue(QUEUE_MAINTENANCE),
        ],
        task_routes=TASK_ROUTES,
        beat_schedule=BEAT_SCHEDULE,
    )
    app.conf.relayops_settings = settings
    app.autodiscover_tasks(TASK_MODULES, force=True)
    for module in TASK_MODULES:
        __import__(module)
    return app


celery_app = build_celery_app()
