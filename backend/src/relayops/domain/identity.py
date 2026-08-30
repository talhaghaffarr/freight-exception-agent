"""Tenancy and authorization entities.

Authorization is decided here and in the repositories — never by a model, never
by anything derived from message content.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

# Stable namespace so demo identifiers survive a database rebuild. Interview
# links and screenshots keep working across `docker compose down -v`.
DEMO_NAMESPACE = uuid.UUID("2f5b8a3c-9e14-5d47-b0a1-6c2d4e8f7a90")


def stable_id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, ":".join(parts))


class Role(StrEnum):
    PLATFORM_OPERATOR = "platform_operator"
    BROKERAGE_ADMIN = "brokerage_admin"
    ACCOUNT_MANAGER = "account_manager"
    REVIEWER = "reviewer"

    @property
    def can_mutate_configuration(self) -> bool:
        return self in {Role.PLATFORM_OPERATOR, Role.BROKERAGE_ADMIN}

    @property
    def can_resolve_goals(self) -> bool:
        return self in {Role.PLATFORM_OPERATOR, Role.BROKERAGE_ADMIN, Role.ACCOUNT_MANAGER}


@dataclass(frozen=True, slots=True)
class Tenant:
    id: uuid.UUID
    slug: str
    name: str
    timezone: str = "America/Chicago"
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class User:
    id: uuid.UUID
    email: str
    display_name: str
    is_platform_operator: bool = False
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class Principal:
    """An authenticated demo user plus the tenants they may touch."""

    user: User
    memberships: dict[uuid.UUID, Role] = field(default_factory=dict)

    @property
    def is_platform_operator(self) -> bool:
        return self.user.is_platform_operator

    @property
    def tenant_ids(self) -> tuple[uuid.UUID, ...]:
        return tuple(self.memberships)

    def role_in(self, tenant_id: uuid.UUID) -> Role | None:
        if role := self.memberships.get(tenant_id):
            return role
        return Role.PLATFORM_OPERATOR if self.is_platform_operator else None

    def can_read_tenant(self, tenant_id: uuid.UUID) -> bool:
        return self.role_in(tenant_id) is not None


@dataclass(frozen=True, slots=True)
class TenantContext:
    """The resolved tenant for one request, with the caller's role in it."""

    tenant: Tenant
    role: Role
    principal: Principal

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.tenant.id
