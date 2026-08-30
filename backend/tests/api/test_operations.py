"""The operations resources, exercised end to end over HTTP."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_the_board_reports_computed_lateness(freight_api_client, freight_login_as) -> None:
    freight_login_as("admin@atlas.demo")

    body = freight_api_client.get("/api/v1/tenants/atlas-brokerage/loads").get_json()
    rows = {row["reference"]: row for row in body["data"]}

    assert rows["LD-1048"]["facts"]["classification"] == "late"
    assert rows["LD-1048"]["facts"]["minutes_late"] == 38
    assert body["meta"]["summary"]["late_pickup"] >= 1


def test_an_unavailable_eta_is_null_with_a_reason_never_a_placeholder(
    freight_api_client, freight_login_as
) -> None:
    freight_login_as("admin@atlas.demo")

    body = freight_api_client.get("/api/v1/tenants/atlas-brokerage/loads").get_json()
    rows = {row["reference"]: row for row in body["data"]}

    dark = rows["LD-1051"]["facts"]
    assert dark["eta"]["predicted_arrival"] is None
    assert dark["eta"]["reason"] == "tracking_stale"
    assert dark["minutes_late"] is None


def test_a_manager_cannot_read_another_tenants_board(
    freight_api_client, freight_login_as
) -> None:
    freight_login_as("manager@meridian.demo")

    response = freight_api_client.get("/api/v1/tenants/atlas-brokerage/loads")

    assert response.status_code == 404


def test_the_same_reference_in_two_tenants_returns_different_loads(
    freight_api_client, freight_login_as
) -> None:
    freight_login_as("operator@relayops.demo")

    atlas = freight_api_client.get(
        "/api/v1/tenants/atlas-brokerage/loads/LD-1048"
    ).get_json()["data"]
    meridian = freight_api_client.get(
        "/api/v1/tenants/meridian-freight/loads/LD-1048"
    ).get_json()["data"]

    assert atlas["customer_name"] == "ACME Retail"
    assert meridian["customer_name"] == "Sonora Distribution"
    assert atlas["load_id"] != meridian["load_id"]


def test_the_race_endpoint_reports_one_goal_and_one_prevented_duplicate(
    freight_api_client, freight_login_as
) -> None:
    freight_login_as("admin@atlas.demo")

    response = freight_api_client.post(
        "/api/v1/tenants/atlas-brokerage/demo/race", json={"reference": "LD-1048"}
    )
    data = response.get_json()["data"]

    assert response.status_code == 200
    assert data["goals_created"] == 1
    assert data["duplicates_prevented"] == 1
    assert data["constraint"] == "goals_idempotency_key"
    assert sorted(a["outcome"] for a in data["attempts"]) == ["inserted", "unique_conflict"]


def test_the_race_goal_is_readable_as_a_trace(freight_api_client, freight_login_as) -> None:
    freight_login_as("admin@atlas.demo")
    race = freight_api_client.post(
        "/api/v1/tenants/atlas-brokerage/demo/race", json={"reference": "LD-1048"}
    ).get_json()["data"]

    goal_id = race["attempts"][0]["goal_id"]
    trace = freight_api_client.get(
        f"/api/v1/tenants/atlas-brokerage/goals/{goal_id}/trace"
    ).get_json()["data"]

    assert trace["goal"]["agent_type"] == "late_pickup"
    assert [event["event_type"] for event in trace["events"]] == ["opened"]


def test_resetting_the_demo_restores_the_intended_lateness(
    freight_api_client, freight_login_as
) -> None:
    """The board is re-anchored to now, so the flagship figure is exact again."""
    freight_login_as("admin@atlas.demo")
    freight_api_client.post(
        "/api/v1/tenants/atlas-brokerage/demo/race", json={"reference": "LD-1048"}
    )

    reset = freight_api_client.post("/api/v1/tenants/atlas-brokerage/demo/reset")
    assert reset.status_code == 200
    assert reset.get_json()["data"]["goals_cleared"] >= 1

    body = freight_api_client.get("/api/v1/tenants/atlas-brokerage/loads").get_json()
    rows = {row["reference"]: row for row in body["data"]}
    assert rows["LD-1048"]["facts"]["minutes_late"] == 38


def test_reset_is_scoped_to_the_callers_tenant(freight_api_client, freight_login_as) -> None:
    freight_login_as("manager@meridian.demo")

    assert freight_api_client.post("/api/v1/tenants/atlas-brokerage/demo/reset").status_code == 404
