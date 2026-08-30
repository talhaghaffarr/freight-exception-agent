"""A real worker, a real broker, and a real result backend.

Asserting that a mock was called would prove nothing about acknowledgement,
serialisation, or routing, which is the whole point of this test.
"""

from __future__ import annotations

import os

import pytest
from celery.contrib.testing.worker import start_worker

from relayops.celery_app import build_celery_app
from relayops.config import Settings

pytestmark = pytest.mark.integration

DEFAULT_TEST_BROKER_URL = "redis://localhost:56379/0"


@pytest.fixture(scope="module")
def broker_url() -> str:
    url = os.environ.get("TEST_BROKER_URL", DEFAULT_TEST_BROKER_URL)
    try:
        import redis

        redis.Redis.from_url(url).ping()
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"Valkey is unavailable at {url}: {exc}")
    return url


@pytest.fixture(scope="module")
def celery_app(broker_url: str):
    settings = Settings.from_env(
        {
            "CELERY_BROKER_URL": broker_url,
            "CELERY_RESULT_BACKEND": broker_url.rsplit("/", 1)[0] + "/1",
            "TESTING": "true",
        }
    )
    app = build_celery_app(settings)
    app.conf.update(broker_connection_retry_on_startup=True)
    return app


@pytest.fixture(scope="module")
def celery_worker(celery_app):
    with start_worker(celery_app, perform_ping_check=False, shutdown_timeout=30) as worker:
        yield worker


def test_ping_round_trips_through_a_real_worker(celery_app, celery_worker):
    async_result = celery_app.send_task("relayops.health.ping")
    payload = async_result.get(timeout=30)

    assert payload["task_id"] == async_result.id
    assert payload["pong"] is True
    assert payload["worker_time"].endswith("+00:00")
    assert payload["hostname"]


def test_tasks_acknowledge_late_so_a_crash_redelivers(celery_app):
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_only_json_is_accepted_on_the_wire(celery_app):
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]


def test_health_tasks_are_routed_to_the_maintenance_queue(celery_app):
    route = celery_app.amqp.router.route({}, "relayops.health.ping")
    assert route["queue"].name == "maintenance"


def test_heartbeat_makes_beat_observable_to_the_health_probe(celery_app, celery_worker):
    from relayops.probes import BeatProbe

    celery_app.send_task("relayops.health.heartbeat").get(timeout=30)

    component = BeatProbe(celery_app.conf.broker_url).check()
    assert component.status == "healthy"
    assert component.metadata["age_seconds"] < 5


def test_beat_probe_reports_unknown_before_any_heartbeat(celery_app):
    import redis

    from relayops.probes import BEAT_HEARTBEAT_KEY, BeatProbe

    client = redis.Redis.from_url(celery_app.conf.broker_url)
    client.delete(BEAT_HEARTBEAT_KEY)
    client.close()

    component = BeatProbe(celery_app.conf.broker_url).check()
    assert component.status == "unknown"
    assert component.detail == "no heartbeat recorded yet"


def test_beat_schedule_includes_the_heartbeat(celery_app):
    assert "beat-heartbeat" in celery_app.conf.beat_schedule
