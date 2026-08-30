import pytest

pytestmark = pytest.mark.integration


def test_dashboard_has_stable_sections_before_agents_exist(api_client, login_as):
    login_as("admin@atlas.demo")
    body = api_client.get("/api/v1/dashboard").get_json()["data"]
    assert body == {
        "agents": [],
        "goals": {"opened": 0, "waiting": 0, "needs_review": 0, "failed": 0},
        "communications": {"email": 0, "sms": 0, "voice": 0},
        "value": {"operator_minutes_saved": 0},
        "recent_activity": [],
    }


def test_dashboard_requires_a_session(api_client):
    assert api_client.get("/api/v1/dashboard").status_code == 401


def test_dashboard_rejects_a_tenant_the_caller_cannot_see(api_client, login_as):
    login_as("manager@meridian.demo")
    response = api_client.get("/api/v1/dashboard?tenant=atlas-brokerage")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_dashboard_scopes_to_the_requested_tenant(api_client, login_as):
    login_as("reviewer@relayops.demo")
    response = api_client.get("/api/v1/dashboard?tenant=meridian-freight")
    assert response.status_code == 200
    assert response.get_json()["meta"]["scope"] == "meridian-freight"


def test_platform_operator_may_aggregate_across_tenants(api_client, login_as):
    login_as("operator@relayops.demo")
    response = api_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert response.get_json()["meta"]["scope"] == "all"


def test_a_member_without_a_tenant_argument_gets_their_own_tenant(api_client, login_as):
    login_as("admin@atlas.demo")
    meta = api_client.get("/api/v1/dashboard").get_json()["meta"]
    assert meta["scope"] == "atlas-brokerage"
