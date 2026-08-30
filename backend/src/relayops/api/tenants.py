"""Tenant resources.

Every read resolves through membership. Renames are audited with the actor, the
old and new value, and the operator's stated reason.
"""

from __future__ import annotations

from flask import Blueprint, g, request

from relayops.api.deps import current_principal, db, require_login, require_role, resolve_tenant
from relayops.api.serializers import tenant_summary
from relayops.domain.identity import Role
from relayops.errors import ValidationFailed, ok
from relayops.repositories.audit import record_audit_event
from relayops.repositories.identity import list_tenants_for_principal, rename_tenant

bp = Blueprint("tenants", __name__)


@bp.get("/tenants")
@require_login
def list_tenants():
    principal = current_principal()
    tenants = list_tenants_for_principal(db(), principal)
    return ok([tenant_summary(tenant) for tenant in tenants])


@bp.get("/tenants/<tenant_ref>")
@require_login
def read_tenant(tenant_ref: str):
    context = resolve_tenant(tenant_ref)
    return ok({**tenant_summary(context.tenant), "role": str(context.role)})


@bp.patch("/tenants/<tenant_ref>")
@require_role(Role.PLATFORM_OPERATOR, Role.BROKERAGE_ADMIN)
def update_tenant(tenant_ref: str):
    context = g.tenant_context
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValidationFailed("A tenant name is required.", field="name")

    connection = db()
    updated = rename_tenant(connection, context.tenant.id, name)
    record_audit_event(
        connection,
        tenant_id=context.tenant.id,
        actor=context.principal,
        action="tenant.renamed",
        subject_type="tenant",
        subject_id=str(context.tenant.id),
        reason=str(payload.get("reason", "")).strip() or None,
        old_value={"name": context.tenant.name},
        new_value={"name": updated.name},
    )
    return ok({**tenant_summary(updated), "role": str(context.role)})
