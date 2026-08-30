"""Environment metadata the operator console reads on boot."""

from __future__ import annotations

from flask import Blueprint, current_app

from relayops import __version__
from relayops.config import Settings
from relayops.errors import ok

bp = Blueprint("meta", __name__)


@bp.get("/meta")
def read_meta():
    settings: Settings = current_app.config["SETTINGS"]
    return ok(
        {
            "api_version": "v1",
            "release": __version__,
            "environment_mode": settings.environment_mode,
            "can_reach_external_recipients": settings.can_reach_external_recipients,
        }
    )
