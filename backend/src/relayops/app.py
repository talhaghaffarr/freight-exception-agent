"""Flask application factory.

The factory wires configuration, correlation ids, the JSON envelope, and the
versioned blueprint tree. Database and Celery initialisation stay behind
explicit extension functions so unit tests can build an app without contacting
PostgreSQL or Valkey.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, g, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import Engine
from werkzeug.exceptions import HTTPException, NotFound

from relayops.config import Settings
from relayops.errors import (
    ApiError,
    new_request_id,
    ok,
    render_api_error,
    render_http_exception,
    render_unexpected_error,
)
from relayops.logging import configure_logging, get_logger

API_PREFIX = "/api/v1"


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    console_dist: str | None = None,
    **overrides: Any,
) -> Flask:
    # No settings means "read the environment": that is how every container
    # is configured.
    settings = settings or Settings.from_env(os.environ)

    configure_logging(service="web", json_output=not settings.testing)
    log = get_logger("relayops.api")

    app = Flask(__name__)
    app.config.update(
        SETTINGS=settings,
        SECRET_KEY=settings.secret_key.get_secret_value(),
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.environment_mode == "live",
        TESTING=settings.testing,
    )
    app.config.update(overrides)

    CORS(
        app,
        resources={rf"{API_PREFIX}/*": {"origins": list(settings.cors_origins)}},
        supports_credentials=True,
    )

    _register_database(app, settings, engine)
    _register_celery(app, settings)
    _register_request_lifecycle(app, log)
    _register_error_handlers(app, log)
    _register_blueprints(app)
    _register_console(app, console_dist)

    return app


def _resolve_console_dist(explicit: str | None) -> Path | None:
    """Locate a compiled console, if one was shipped alongside the API.

    Deployments build the SPA into the image and serve it from this process,
    which keeps the hosted demo to a single container. Development runs the
    Vite dev server instead and this returns ``None``.
    """
    candidates = [explicit, os.environ.get("CONSOLE_DIST")]
    for candidate in candidates:
        if candidate:
            path = Path(candidate)
            return path if (path / "index.html").is_file() else None

    bundled = Path(__file__).resolve().parents[2] / "console"
    if (bundled / "index.html").is_file():
        return bundled
    return None


def _register_console(app: Flask, explicit: str | None) -> None:
    dist = _resolve_console_dist(explicit)
    if dist is None:
        return

    index = (dist / "index.html").read_text()

    @app.get("/")
    def _console_root():
        return Response(index, mimetype="text/html")

    # Registered last and excluding the API prefix, so an unknown endpoint under
    # /api still resolves to the JSON 404 handler rather than to the SPA shell.
    @app.get("/<path:resource>")
    def _console_asset(resource: str):
        if resource.startswith("api/") or resource == "healthz":
            raise NotFound()
        candidate = (dist / resource).resolve()
        if candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return send_from_directory(dist, resource)
        # Any other path is a client-side route; the SPA resolves it.
        return Response(index, mimetype="text/html")


def _register_database(app: Flask, settings: Settings, engine: Engine | None) -> None:
    """Attach the engine.

    When no engine is injected the factory is stored instead and resolved on
    first use, so a unit test can build an application without PostgreSQL
    running anywhere.
    """
    from relayops.api.deps import close_db
    from relayops.db import get_engine

    if engine is not None:
        app.extensions["relayops_engine"] = engine
    else:
        app.extensions["relayops_engine_factory"] = lambda: get_engine(settings)

    app.teardown_appcontext(close_db)


def _register_celery(app: Flask, settings: Settings) -> None:
    """Attach a Celery client so the API can inspect workers and enqueue work."""
    from relayops.celery_app import build_celery_app

    app.extensions["relayops_celery"] = build_celery_app(settings)


def _register_request_lifecycle(app: Flask, log) -> None:
    @app.before_request
    def _start_request() -> None:
        g.request_id = request.headers.get("X-Request-ID-Echo") or new_request_id()
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _finish_request(response: Response) -> Response:
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        started_at = getattr(g, "request_started_at", None)
        if started_at is not None:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            response.headers["X-Response-Time-Ms"] = str(duration_ms)
            log.info(
                "http_request",
                request_id=request_id,
                method=request.method,
                path=request.path,
                status=response.status_code,
                duration_ms=duration_ms,
            )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


def _register_error_handlers(app: Flask, log) -> None:
    @app.errorhandler(ApiError)
    def _handle_api_error(exc: ApiError):
        log.info(
            "api_error",
            request_id=getattr(g, "request_id", None),
            code=exc.code,
            status=exc.http_status,
        )
        return render_api_error(exc)

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):
        return render_http_exception(exc)

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):
        log.error(
            "unhandled_exception",
            request_id=getattr(g, "request_id", None),
            exception_type=type(exc).__name__,
            exc_info=True,
        )
        return render_unexpected_error()


def _register_blueprints(app: Flask) -> None:
    from relayops.api.auth import bp as auth_bp
    from relayops.api.dashboard import bp as dashboard_bp
    from relayops.api.health import bp as health_bp
    from relayops.api.meta import bp as meta_bp
    from relayops.api.goals import bp as goals_bp
    from relayops.api.operations import bp as operations_bp
    from relayops.api.tenants import bp as tenants_bp

    for blueprint in (meta_bp, auth_bp, tenants_bp, health_bp, dashboard_bp, operations_bp, goals_bp):
        app.register_blueprint(blueprint, url_prefix=API_PREFIX)

    @app.get("/healthz")
    def _liveness():
        return ok({"status": "alive"})
