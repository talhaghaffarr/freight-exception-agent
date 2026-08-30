import pytest

pytestmark = pytest.mark.integration


def test_account_manager_cannot_switch_to_another_tenant(api_client, login_as):
    login_as("manager@meridian.demo")
    response = api_client.get("/api/v1/tenants/atlas-brokerage")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_absent_and_unauthorized_tenants_are_indistinguishable(api_client, login_as):
    login_as("manager@meridian.demo")
    unauthorized = api_client.get("/api/v1/tenants/atlas-brokerage")
    missing = api_client.get("/api/v1/tenants/no-such-tenant")
    assert unauthorized.status_code == missing.status_code == 404
    assert unauthorized.get_json()["error"] == missing.get_json()["error"]


def test_a_member_can_read_their_own_tenant(api_client, login_as):
    login_as("manager@meridian.demo")
    body = api_client.get("/api/v1/tenants/meridian-freight").get_json()["data"]
    assert body["slug"] == "meridian-freight"
    assert body["role"] == "account_manager"


def test_tenant_is_resolvable_by_id_as_well_as_slug(api_client, login_as):
    session = login_as("admin@atlas.demo")
    tenant_id = session["tenants"][0]["id"]
    body = api_client.get(f"/api/v1/tenants/{tenant_id}").get_json()["data"]
    assert body["slug"] == "atlas-brokerage"


def test_platform_operator_may_read_any_tenant(api_client, login_as):
    login_as("operator@relayops.demo")
    for slug in ("atlas-brokerage", "meridian-freight"):
        assert api_client.get(f"/api/v1/tenants/{slug}").status_code == 200


def test_tenant_list_is_scoped_to_membership(api_client, login_as):
    login_as("reviewer@relayops.demo")
    body = api_client.get("/api/v1/tenants").get_json()["data"]
    assert [tenant["slug"] for tenant in body] == ["atlas-brokerage", "meridian-freight"]

    api_client.post("/api/v1/auth/sign-out")
    login_as("admin@atlas.demo")
    body = api_client.get("/api/v1/tenants").get_json()["data"]
    assert [tenant["slug"] for tenant in body] == ["atlas-brokerage"]


def test_a_reviewer_cannot_mutate_tenant_configuration(api_client, login_as):
    login_as("reviewer@relayops.demo")
    response = api_client.patch(
        "/api/v1/tenants/atlas-brokerage", json={"name": "Renamed By Reviewer"}
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_a_brokerage_admin_may_rename_their_own_tenant(api_client, login_as):
    login_as("admin@atlas.demo")
    response = api_client.patch(
        "/api/v1/tenants/atlas-brokerage",
        json={"name": "Atlas Brokerage LLC", "reason": "legal entity rename"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["name"] == "Atlas Brokerage LLC"
