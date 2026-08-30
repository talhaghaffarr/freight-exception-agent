from relayops.health import HealthProbe, StaticProbe, collect_health


def test_optional_provider_failure_degrades_but_does_not_fail_readiness():
    report = collect_health(
        [
            StaticProbe("database", "healthy", required=True),
            StaticProbe("voice", "unhealthy", required=False),
        ]
    )
    assert report.status == "degraded"
    assert report.ready is True


def test_all_healthy_components_report_healthy_and_ready():
    report = collect_health(
        [StaticProbe("database", "healthy", required=True), StaticProbe("valkey", "healthy")]
    )
    assert report.status == "healthy"
    assert report.ready is True


def test_required_component_failure_fails_readiness():
    report = collect_health(
        [
            StaticProbe("database", "unhealthy", required=True, detail="connection refused"),
            StaticProbe("voice", "healthy", required=False),
        ]
    )
    assert report.status == "unhealthy"
    assert report.ready is False


def test_unknown_required_component_is_not_ready_but_is_not_reported_as_failing():
    report = collect_health([StaticProbe("worker", "unknown", required=True)])
    assert report.status == "unknown"
    assert report.ready is False


def test_a_paused_agent_is_not_the_same_as_an_unhealthy_runtime():
    report = collect_health(
        [StaticProbe("worker", "healthy", required=True), StaticProbe("agents", "degraded")]
    )
    assert report.status == "degraded"
    assert report.ready is True
    assert report.component("agents").status == "degraded"


def test_probe_failures_are_contained_and_reported_as_unhealthy():
    class ExplodingProbe:
        name = "database"
        required = True

        def check(self):
            raise RuntimeError("password=hunter2 in dsn")

    report = collect_health([ExplodingProbe()])
    component = report.component("database")
    assert component.status == "unhealthy"
    assert "hunter2" not in (component.detail or "")
    assert report.ready is False


def test_each_component_records_latency_and_a_check_timestamp():
    report = collect_health([StaticProbe("database", "healthy", required=True)])
    component = report.component("database")
    assert component.latency_ms >= 0
    assert component.checked_at.tzinfo is not None


def test_static_probe_satisfies_the_probe_protocol():
    assert isinstance(StaticProbe("x", "healthy"), HealthProbe)
