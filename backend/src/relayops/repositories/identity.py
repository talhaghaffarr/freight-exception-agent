"""Tenant, user, and membership persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import Connection, text

from relayops.domain.identity import Principal, Role, Tenant, User


def upsert_tenant(connection: Connection, tenant: Tenant) -> uuid.UUID:
    return connection.execute(
        text(
            """
            insert into tenants (id, slug, name, timezone, is_active)
            values (:id, :slug, :name, :timezone, :is_active)
            on conflict (id) do update
               set slug = excluded.slug,
                   name = excluded.name,
                   timezone = excluded.timezone,
                   is_active = excluded.is_active,
                   updated_at = now()
            returning id
            """
        ),
        {
            "id": tenant.id,
            "slug": tenant.slug,
            "name": tenant.name,
            "timezone": tenant.timezone,
            "is_active": tenant.is_active,
        },
    ).scalar_one()


def upsert_user(connection: Connection, user: User) -> uuid.UUID:
    return connection.execute(
        text(
            """
            insert into users (id, email, display_name, is_platform_operator, is_active)
            values (:id, :email, :display_name, :is_platform_operator, :is_active)
            on conflict (id) do update
               set email = excluded.email,
                   display_name = excluded.display_name,
                   is_platform_operator = excluded.is_platform_operator,
                   is_active = excluded.is_active,
                   updated_at = now()
            returning id
            """
        ),
        {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "is_platform_operator": user.is_platform_operator,
            "is_active": user.is_active,
        },
    ).scalar_one()


def upsert_membership(
    connection: Connection, tenant_id: uuid.UUID, user_id: uuid.UUID, role: Role
) -> None:
    connection.execute(
        text(
            """
            insert into tenant_memberships (tenant_id, user_id, role)
            values (:tenant_id, :user_id, :role)
            on conflict (tenant_id, user_id) do update set role = excluded.role
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "role": str(role)},
    )


def _to_tenant(row) -> Tenant:
    return Tenant(
        id=row.id, slug=row.slug, name=row.name, timezone=row.timezone, is_active=row.is_active
    )


def get_user_by_email(connection: Connection, email: str) -> User | None:
    row = connection.execute(
        text(
            "select id, email, display_name, is_platform_operator, is_active "
            "from users where lower(email) = lower(:email)"
        ),
        {"email": email},
    ).one_or_none()
    if row is None:
        return None
    return User(
        id=row.id,
        email=row.email,
        display_name=row.display_name,
        is_platform_operator=row.is_platform_operator,
        is_active=row.is_active,
    )


def load_principal(connection: Connection, user_id: uuid.UUID) -> Principal | None:
    """Load an active user together with every membership they hold."""
    row = connection.execute(
        text(
            "select id, email, display_name, is_platform_operator, is_active "
            "from users where id = :id and is_active"
        ),
        {"id": user_id},
    ).one_or_none()
    if row is None:
        return None

    memberships = {
        membership.tenant_id: Role(membership.role)
        for membership in connection.execute(
            text(
                "select m.tenant_id, m.role from tenant_memberships m "
                "join tenants t on t.id = m.tenant_id "
                "where m.user_id = :user_id and t.is_active"
            ),
            {"user_id": user_id},
        )
    }
    return Principal(
        user=User(
            id=row.id,
            email=row.email,
            display_name=row.display_name,
            is_platform_operator=row.is_platform_operator,
            is_active=row.is_active,
        ),
        memberships=memberships,
    )


def get_tenant(connection: Connection, tenant_id: uuid.UUID) -> Tenant | None:
    row = connection.execute(
        text(
            "select id, slug, name, timezone, is_active from tenants where id = :id"
        ),
        {"id": tenant_id},
    ).one_or_none()
    return _to_tenant(row) if row else None


def get_tenant_by_reference(connection: Connection, reference: str) -> Tenant | None:
    """Resolve a tenant by slug or id without revealing which form matched."""
    try:
        tenant_id: uuid.UUID | None = uuid.UUID(str(reference))
    except (ValueError, AttributeError, TypeError):
        tenant_id = None

    if tenant_id is not None:
        return get_tenant(connection, tenant_id)

    row = connection.execute(
        text("select id, slug, name, timezone, is_active from tenants where slug = :slug"),
        {"slug": reference},
    ).one_or_none()
    return _to_tenant(row) if row else None


def list_tenants_for_principal(connection: Connection, principal: Principal) -> list[Tenant]:
    """Platform operators see every tenant; everyone else sees only their own."""
    if principal.is_platform_operator:
        rows = connection.execute(
            text(
                "select id, slug, name, timezone, is_active from tenants "
                "where is_active order by name"
            )
        ).all()
    else:
        if not principal.memberships:
            return []
        rows = connection.execute(
            text(
                "select id, slug, name, timezone, is_active from tenants "
                "where is_active and id = any(:ids) order by name"
            ),
            {"ids": list(principal.memberships)},
        ).all()
    return [_to_tenant(row) for row in rows]


def rename_tenant(connection: Connection, tenant_id: uuid.UUID, name: str) -> Tenant:
    row = connection.execute(
        text(
            "update tenants set name = :name, updated_at = now() where id = :id "
            "returning id, slug, name, timezone, is_active"
        ),
        {"id": tenant_id, "name": name},
    ).one()
    return _to_tenant(row)
