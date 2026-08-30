"""Wire representations. Keep serialisation out of route bodies."""

from __future__ import annotations

from typing import Any

from relayops.domain.identity import Principal, Tenant


def tenant_summary(tenant: Tenant) -> dict[str, Any]:
    return {
        "id": str(tenant.id),
        "slug": tenant.slug,
        "name": tenant.name,
        "timezone": tenant.timezone,
    }


def user_summary(principal: Principal) -> dict[str, Any]:
    return {
        "id": str(principal.user.id),
        "email": principal.user.email,
        "display_name": principal.user.display_name,
        "is_platform_operator": principal.is_platform_operator,
    }


def session_payload(
    principal: Principal, tenants: list[Tenant], environment_mode: str
) -> dict[str, Any]:
    by_id = {tenant.id: tenant for tenant in tenants}
    roles = {
        by_id[tenant_id].slug: str(role)
        for tenant_id, role in principal.memberships.items()
        if tenant_id in by_id
    }
    return {
        "user": user_summary(principal),
        "tenants": [tenant_summary(tenant) for tenant in tenants],
        "roles": roles,
        "environment_mode": environment_mode,
    }
