import pytest

pytestmark = pytest.mark.integration


def test_health_endpoint_is_readable_without_a_session(api_client):
    response = api_client.get("/api/v1/system/health")
    assert response.status_code == 200
    body = response.get_json()["data"]
    assert body["status"] in {"healthy", "degraded", "unhealthy", "unknown"}
    assert {"api", "database", "migrations"} <= {c["name"] for c in body["components"]}


def test_health_reports_the_database_as_healthy_against_a_migrated_schema(api_client):
    body = api_client.get("/api/v1/system/health").get_json()["data"]
    components = {component["name"]: component for component in body["components"]}
    assert components["database"]["status"] == "healthy"
    assert components["database"]["required"] is True
    assert components["migrations"]["status"] == "healthy"


def test_readiness_fails_while_a_migration_is_pending(migrated_engine, db_settings):
    from sqlalchemy import text

    from relayops.app import create_app
    from relayops.seed import seed_demo_data

    with migrated_engine.begin() as connection:
        seed_demo_data(connection)
        connection.execute(text("delete from schema_migrations"))

    app = create_app(db_settings, engine=migrated_engine)
    response = app.test_client().get("/api/v1/system/readiness")
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "NOT_READY"


def test_readiness_succeeds_on_a_current_schema(api_client):
    response = api_client.get("/api/v1/system/readiness")
    assert response.status_code == 200
    assert response.get_json()["data"]["ready"] is True


def test_liveness_does_not_fail_because_an_optional_provider_is_degraded(api_client):
    assert api_client.get("/healthz").status_code == 200


def test_health_detail_never_contains_the_database_password(api_client):
    text_body = api_client.get("/api/v1/system/health").get_data(as_text=True)
    assert "relayops:relayops@" not in text_body
