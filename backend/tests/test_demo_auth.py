import pytest

pytestmark = pytest.mark.integration


def test_unauthenticated_requests_are_rejected(api_client):
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHENTICATED"


def test_demo_session_returns_the_principal_and_visible_tenants(api_client, login_as):
    data = login_as("admin@atlas.demo")
    assert data["user"]["email"] == "admin@atlas.demo"
    assert data["user"]["is_platform_operator"] is False
    assert [tenant["slug"] for tenant in data["tenants"]] == ["atlas-brokerage"]
    assert data["roles"] == {"atlas-brokerage": "brokerage_admin"}

    me = api_client.get("/api/v1/auth/me").get_json()["data"]
    assert me["user"]["email"] == "admin@atlas.demo"


def test_platform_operator_sees_every_tenant(login_as):
    data = login_as("operator@relayops.demo")
    assert data["user"]["is_platform_operator"] is True
    assert [tenant["slug"] for tenant in data["tenants"]] == [
        "atlas-brokerage",
        "meridian-freight",
    ]


def test_unknown_email_cannot_open_a_session(api_client):
    response = api_client.post(
        "/api/v1/auth/demo-session", json={"email": "stranger@example.com"}
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHENTICATED"


def test_session_cookie_is_http_only_and_same_site(api_client):
    response = api_client.post(
        "/api/v1/auth/demo-session", json={"email": "reviewer@relayops.demo"}
    )
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_sign_out_clears_the_session(api_client, login_as):
    login_as("reviewer@relayops.demo")
    assert api_client.post("/api/v1/auth/sign-out").status_code == 200
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_a_tampered_session_is_refused(api_client, login_as):
    login_as("reviewer@relayops.demo")
    api_client.set_cookie("session", "forged-value", domain="localhost")
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_demo_sessions_are_unavailable_in_live_mode(seeded_engine, database_url):
    from relayops.app import create_app
    from relayops.config import Settings

    live_settings = Settings.from_env(
        {
            "SECRET_KEY": "test-only-signing-key",
            "TESTING": "true",
            "DATABASE_URL": database_url,
            "ENVIRONMENT_MODE": "live",
            "ALLOW_LIVE_SENDS": "true",
        }
    )
    app = create_app(live_settings, engine=seeded_engine)
    response = app.test_client().post(
        "/api/v1/auth/demo-session", json={"email": "operator@relayops.demo"}
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "DEMO_AUTH_DISABLED"
