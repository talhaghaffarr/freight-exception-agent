"""Demo sessions.

This is deliberately a demo-only identity mechanism: a signed, HTTP-only cookie
issued to one of the seeded users. It is disabled outright in ``live`` mode, and
``docs/deployment.md`` documents the OIDC integration that replaces it in
production.
"""

from __future__ import annotations

from flask import Blueprint, current_app, request, session

from relayops.api.deps import SESSION_USER_KEY, current_principal, db
from relayops.api.serializers import session_payload
from relayops.config import Settings
from relayops.errors import ApiError, Unauthenticated, ValidationFailed, ok
from relayops.repositories.identity import get_user_by_email, list_tenants_for_principal

bp = Blueprint("auth", __name__)


def _settings() -> Settings:
    return current_app.config["SETTINGS"]


@bp.post("/auth/demo-session")
def open_demo_session():
    settings = _settings()
    if settings.environment_mode == "live":
        raise ApiError(
            "DEMO_AUTH_DISABLED",
            "Demo sessions are disabled outside sandbox and allowlist modes.",
            403,
        )

    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip()
    if not email:
        raise ValidationFailed("An email address is required.", field="email")

    user = get_user_by_email(db(), email)
    if user is None or not user.is_active:
        # Same response for unknown and inactive: do not confirm which demo
        # addresses exist.
        raise Unauthenticated("That demo account is not available.")

    session.clear()
    session[SESSION_USER_KEY] = str(user.id)
    session.permanent = False

    principal = current_principal()
    tenants = list_tenants_for_principal(db(), principal)
    return ok(session_payload(principal, tenants, settings.environment_mode))


@bp.get("/auth/me")
def read_me():
    principal = current_principal()
    tenants = list_tenants_for_principal(db(), principal)
    return ok(session_payload(principal, tenants, _settings().environment_mode))


@bp.post("/auth/sign-out")
def sign_out():
    session.clear()
    return ok({"signed_out": True})
