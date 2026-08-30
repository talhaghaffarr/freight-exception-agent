"""Serving the built console from the API process.

A single container is the cheapest shape to host, so Flask serves the compiled
SPA when a build is present. The rule that matters: API routes must never be
shadowed by the SPA fallback, or a mistyped endpoint would return HTML with a
200 instead of a JSON 404.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relayops.app import create_app
from relayops.config import Settings


@pytest.fixture
def console_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>RelayOps</title>")
    (dist / "assets" / "app.js").write_text("console.log('relayops')")
    return dist


@pytest.fixture
def console_client(console_dist: Path):
    settings = Settings.from_env({"SECRET_KEY": "test-only-signing-key", "TESTING": "true"})
    app = create_app(settings, console_dist=str(console_dist))
    app.config.update(TESTING=True)
    return app.test_client()


def test_the_root_serves_the_console(console_client) -> None:
    response = console_client.get("/")
    assert response.status_code == 200
    assert b"RelayOps" in response.data


def test_built_assets_are_served(console_client) -> None:
    assert console_client.get("/assets/app.js").status_code == 200


def test_a_client_route_falls_back_to_the_console(console_client) -> None:
    """Deep links are the SPA's to resolve, not the server's."""
    response = console_client.get("/live")
    assert response.status_code == 200
    assert b"RelayOps" in response.data


def test_an_unknown_api_route_is_json_not_html(console_client) -> None:
    response = console_client.get("/api/v1/no-such-resource")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_the_liveness_probe_is_not_shadowed(console_client) -> None:
    assert console_client.get("/healthz").get_json()["data"]["status"] == "alive"


def test_without_a_build_the_api_still_runs(client) -> None:
    """No console build present: the API must not fail to start."""
    assert client.get("/healthz").status_code == 200
