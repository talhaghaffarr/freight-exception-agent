"""Fleet overview."""

from __future__ import annotations

from flask import Blueprint, request

from relayops.api.deps import current_principal, db, require_login, resolve_tenant
from relayops.errors import ok
from relayops.repositories.dashboard import load_dashboard

bp = Blueprint("dashboard", __name__)

ALL_TENANTS = "all"


@bp.get("/dashboard")
@require_login
def read_dashboard():
    principal = current_principal()
    requested = (request.args.get("tenant") or "").strip()

    if requested in {"", ALL_TENANTS}:
        if principal.is_platform_operator:
            summary = load_dashboard(db(), None)
            return ok(summary.as_dict(), meta={"scope": ALL_TENANTS})
        # A member with no explicit choice gets their own tenant, never a
        # cross-tenant aggregate.
        tenant_ids = list(principal.memberships)
        scope = ALL_TENANTS if len(tenant_ids) != 1 else None
        if scope is None:
            from relayops.repositories.identity import get_tenant

            tenant = get_tenant(db(), tenant_ids[0])
            summary = load_dashboard(db(), tenant_ids)
            return ok(summary.as_dict(), meta={"scope": tenant.slug if tenant else ALL_TENANTS})
        summary = load_dashboard(db(), tenant_ids)
        return ok(summary.as_dict(), meta={"scope": ALL_TENANTS})

    context = resolve_tenant(requested, principal=principal)
    summary = load_dashboard(db(), [context.tenant_id])
    return ok(summary.as_dict(), meta={"scope": context.tenant.slug})
