"""Liveness evidence from inside a worker process."""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from typing import Any

from celery import shared_task


@shared_task(name="relayops.health.ping", bind=True, ignore_result=False)
def ping(self) -> dict[str, Any]:
    """Prove that a worker consumed this message and produced a result."""
    delivery_info = self.request.delivery_info or {}
    return {
        "pong": True,
        "task_id": self.request.id,
        "hostname": self.request.hostname or socket.gethostname(),
        "worker_time": datetime.now(UTC).isoformat(),
        "queue": delivery_info.get("routing_key"),
    }


@shared_task(name="relayops.health.heartbeat", ignore_result=True)
def heartbeat() -> str:
    """Record that Beat's schedule is still advancing.

    A missing key means "no evidence yet", not "Beat crashed" — the probe
    reports those differently on purpose.
    """
    import redis
    from celery import current_app

    from relayops.probes import BEAT_HEARTBEAT_KEY, BEAT_STALE_AFTER_SECONDS

    now = datetime.now(UTC).isoformat()
    client = redis.Redis.from_url(current_app.conf.broker_url, socket_connect_timeout=2)
    try:
        client.set(BEAT_HEARTBEAT_KEY, now, ex=BEAT_STALE_AFTER_SECONDS * 4)
    finally:
        client.close()
    return now
