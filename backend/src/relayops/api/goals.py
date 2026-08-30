"""Goals queue and analytics resources.

CONTRACT (Increment 2.5 -- fill the console): implemented by the goals-history
workstream. The routes below define the wire shape the frontend builds against;
the implementation replaces the empty payloads without changing the shape.
"""

from __future__ import annotations

from flask import Blueprint

from relayops.api.deps import current_principal, require_login, resolve_tenant
from relayops.errors import ok

bp = Blueprint("goals", __name__)


@bp.get("/tenants/<tenant_ref>/goals")
@require_login
def list_goals(tenant_ref: str):
    context = resolve_tenant(tenant_ref, principal=current_principal())
    return ok([], meta={"tenant": context.tenant.slug, "counts": {}})


@bp.get("/tenants/<tenant_ref>/agents/catalog")
@require_login
def agent_catalog(tenant_ref: str):
    context = resolve_tenant(tenant_ref, principal=current_principal())
    return ok([], meta={"tenant": context.tenant.slug})


@bp.get("/tenants/<tenant_ref>/analytics/outcomes")
@require_login
def outcome_analytics(tenant_ref: str):
    context = resolve_tenant(tenant_ref, principal=current_principal())
    return ok(
        {"outcomes": [], "daily": [], "value": {"operator_minutes_saved": 0}},
        meta={"tenant": context.tenant.slug, "window_days": 7},
    )
