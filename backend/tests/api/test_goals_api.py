"""The goals queue, agent catalog, and outcome analytics over HTTP."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


# --- Goals list -----------------------------------------------------------


def test_the_goals_list_shows_the_seeded_history(history_api_client, history_login_as) -> None:
    history_login_as("admin@atlas.demo")

    body = history_api_client.get("/api/v1/tenants/atlas-brokerage/goals").get_json()
    rows = body["data"]

    assert len(rows) == 44
    first = rows[0]
    for key in (
        "id",
        "reference",
        "agent_type",
        "agent_version",
        "subject_label",
        "state",
        "terminal_outcome",
        "opened_at",
        "closed_at",
    ):
        assert key in first
    # Newest first.
    opened = [row["opened_at"] for row in rows]
    assert opened == sorted(opened, reverse=True)


def test_the_goals_list_counts_every_state_unfiltered(
    history_api_client, history_login_as
) -> None:
    history_login_as("admin@atlas.demo")

    body = history_api_client.get(
        "/api/v1/tenants/atlas-brokerage/goals?state=succeeded"
    ).get_json()

    assert all(row["state"] == "succeeded" for row in body["data"])
    assert len(body["data"]) == 14
    counts = body["meta"]["counts"]
    assert counts["succeeded"] == 14
    assert counts["suppressed"] == 25
    assert counts["expired"] == 1
    assert sum(counts.values()) == 44


def test_the_goals_list_is_tenant_scoped(history_api_client, history_login_as) -> None:
    history_login_as("manager@meridian.demo")

    denied = history_api_client.get("/api/v1/tenants/atlas-brokerage/goals")
    assert denied.status_code == 404

    body = history_api_client.get("/api/v1/tenants/meridian-freight/goals").get_json()
    assert len(body["data"]) == 10
    assert {row["terminal_outcome"] for row in body["data"]} == {
        "tenant_disabled",
        "below_threshold",
    }


def test_the_goals_list_honours_the_limit(history_api_client, history_login_as) -> None:
    history_login_as("admin@atlas.demo")

    body = history_api_client.get("/api/v1/tenants/atlas-brokerage/goals?limit=5").get_json()

    assert len(body["data"]) == 5
    # The counts stay whole-tenant even when the page is truncated.
    assert sum(body["meta"]["counts"].values()) == 44


def test_an_unknown_state_filter_is_rejected(history_api_client, history_login_as) -> None:
    history_login_as("admin@atlas.demo")

    response = history_api_client.get("/api/v1/tenants/atlas-brokerage/goals?state=bogus")

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_FAILED"


# --- Agent catalog ---------------------------------------------------------


def test_the_catalog_lists_every_agent_with_live_flags(
    history_api_client, history_login_as
) -> None:
    history_login_as("admin@atlas.demo")

    body = history_api_client.get("/api/v1/tenants/atlas-brokerage/agents/catalog").get_json()
    agents = {entry["agent_type"]: entry for entry in body["data"]}

    assert set(agents) == {
        "late_pickup",
        "reactive_status_email",
        "pod_collection",
        "eta_confirmation",
        "detention_risk",
    }
    late = agents["late_pickup"]
    assert late["live"] is True
    assert late["enabled"] is True
    assert late["version"] == "1.0.0"
    assert late["trigger_kind"] == "scanner"
    assert late["config"]["late_threshold_minutes"] == 30
    assert late["counts"]["goals_7d"] == 44
    assert late["counts"]["succeeded_7d"] == 14
    assert all(agents[key]["live"] is False for key in agents if key != "late_pickup")


def test_the_catalog_reflects_the_tenants_own_config(
    history_api_client, history_login_as
) -> None:
    history_login_as("manager@meridian.demo")

    body = history_api_client.get("/api/v1/tenants/meridian-freight/agents/catalog").get_json()
    late = next(entry for entry in body["data"] if entry["agent_type"] == "late_pickup")

    assert late["enabled"] is False
    assert late["counts"]["goals_7d"] == 10
    assert late["counts"]["succeeded_7d"] == 0


# --- Outcome analytics -----------------------------------------------------


def test_outcome_analytics_counts_match_the_seeded_distribution(
    history_api_client, history_login_as
) -> None:
    history_login_as("admin@atlas.demo")

    body = history_api_client.get(
        "/api/v1/tenants/atlas-brokerage/analytics/outcomes"
    ).get_json()
    data = body["data"]
    outcomes = {entry["outcome"]: entry["count"] for entry in data["outcomes"]}

    assert outcomes == {
        "acted_successfully": 14,
        "below_threshold": 8,
        "tracking_stale": 6,
        "already_notified": 4,
        "outside_schedule": 3,
        "operator_suppressed": 2,
        "facts_incomplete": 2,
        "expired_without_action": 1,
    }
    # Sorted by count, descending.
    counts = [entry["count"] for entry in data["outcomes"]]
    assert counts == sorted(counts, reverse=True)


def test_outcome_analytics_daily_series_covers_the_window(
    history_api_client, history_login_as
) -> None:
    history_login_as("admin@atlas.demo")

    body = history_api_client.get(
        "/api/v1/tenants/atlas-brokerage/analytics/outcomes?days=7"
    ).get_json()
    data = body["data"]

    assert body["meta"]["window_days"] == 7
    # Every calendar date the 7-day window touches, oldest first.
    assert len(data["daily"]) == 8
    assert [entry["date"] for entry in data["daily"]] == sorted(
        entry["date"] for entry in data["daily"]
    )
    assert sum(entry["opened"] for entry in data["daily"]) == 44
    assert sum(entry["succeeded"] for entry in data["daily"]) == 14
    assert sum(entry["suppressed"] for entry in data["daily"]) == 25


def test_value_is_counted_from_completed_goals_only(
    history_api_client, history_login_as
) -> None:
    history_login_as("admin@atlas.demo")

    data = history_api_client.get(
        "/api/v1/tenants/atlas-brokerage/analytics/outcomes"
    ).get_json()["data"]

    # 4 minutes per avoided manual touch, from acted_successfully alone.
    assert data["value"]["operator_minutes_saved"] == 56


def test_analytics_is_tenant_scoped(history_api_client, history_login_as) -> None:
    history_login_as("manager@meridian.demo")

    denied = history_api_client.get("/api/v1/tenants/atlas-brokerage/analytics/outcomes")
    assert denied.status_code == 404

    data = history_api_client.get(
        "/api/v1/tenants/meridian-freight/analytics/outcomes"
    ).get_json()["data"]
    assert data["value"]["operator_minutes_saved"] == 0


def test_the_dashboard_reports_the_living_fleet(history_api_client, history_login_as) -> None:
    history_login_as("admin@atlas.demo")

    data = history_api_client.get("/api/v1/dashboard").get_json()["data"]

    # Open work only: terminal goals are history, not workload.
    assert data["goals"]["opened"] == 4
    assert data["goals"]["waiting"] == 1
    assert data["goals"]["needs_review"] == 1
    assert data["goals"]["failed"] == 0
    assert data["value"]["operator_minutes_saved"] == 56
    agent_rows = {row["agent_type"]: row for row in data["agents"]}
    assert agent_rows["late_pickup"]["enabled"] is True
    assert agent_rows["late_pickup"]["goals_open"] == 4
    assert agent_rows["late_pickup"]["success_rate"] == pytest.approx(14 / 40)
    assert len(data["recent_activity"]) > 0
