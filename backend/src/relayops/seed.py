"""Deterministic demo data.

Seeding is an upsert of a known set of rows, never a truncate. Running it twice
produces the same summary, and running it against a hand-edited demo row repairs
that row without touching anything an operator added.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Connection, text

from relayops.domain.identity import Role, Tenant, User, stable_id
from relayops.repositories.identity import upsert_membership, upsert_tenant, upsert_user


@dataclass(frozen=True, slots=True)
class SeedSummary:
    tenants: int
    users: int
    memberships: int


@dataclass(frozen=True, slots=True)
class DemoUser:
    email: str
    display_name: str
    is_platform_operator: bool
    memberships: tuple[tuple[str, Role], ...]

    @property
    def id(self) -> uuid.UUID:
        return stable_id("user", self.email)


DEMO_TENANTS: tuple[Tenant, ...] = (
    Tenant(
        id=stable_id("tenant", "atlas-brokerage"),
        slug="atlas-brokerage",
        name="Atlas Brokerage",
        timezone="America/Chicago",
    ),
    Tenant(
        id=stable_id("tenant", "meridian-freight"),
        slug="meridian-freight",
        name="Meridian Freight",
        timezone="America/Los_Angeles",
    ),
)

DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser(
        email="operator@relayops.demo",
        display_name="Platform Operator",
        is_platform_operator=True,
        memberships=(),
    ),
    DemoUser(
        email="admin@atlas.demo",
        display_name="Dana Okafor",
        is_platform_operator=False,
        memberships=(("atlas-brokerage", Role.BROKERAGE_ADMIN),),
    ),
    DemoUser(
        email="manager@meridian.demo",
        display_name="Sam Whitfield",
        is_platform_operator=False,
        memberships=(("meridian-freight", Role.ACCOUNT_MANAGER),),
    ),
    DemoUser(
        email="reviewer@relayops.demo",
        display_name="Read-only Reviewer",
        is_platform_operator=False,
        memberships=(
            ("atlas-brokerage", Role.REVIEWER),
            ("meridian-freight", Role.REVIEWER),
        ),
    ),
)


def seed_demo_data(connection: Connection, seed: int = 1048) -> SeedSummary:
    """Upsert the documented demo tenants, users, and memberships."""
    tenant_ids: dict[str, uuid.UUID] = {}
    for tenant in DEMO_TENANTS:
        tenant_ids[tenant.slug] = upsert_tenant(connection, tenant)

    for demo_user in DEMO_USERS:
        user_id = upsert_user(
            connection,
            User(
                id=demo_user.id,
                email=demo_user.email,
                display_name=demo_user.display_name,
                is_platform_operator=demo_user.is_platform_operator,
            ),
        )
        for tenant_slug, role in demo_user.memberships:
            upsert_membership(connection, tenant_ids[tenant_slug], user_id, role)

    # Count the demo rows that are actually present rather than what we intended
    # to write: the summary is evidence, not an assertion.
    demo_tenant_ids = list(tenant_ids.values())
    demo_user_ids = [user.id for user in DEMO_USERS]
    return SeedSummary(
        tenants=connection.execute(
            text("select count(*) from tenants where id = any(:ids)"),
            {"ids": demo_tenant_ids},
        ).scalar_one(),
        users=connection.execute(
            text("select count(*) from users where id = any(:ids)"), {"ids": demo_user_ids}
        ).scalar_one(),
        memberships=connection.execute(
            text(
                "select count(*) from tenant_memberships "
                "where user_id = any(:users) and tenant_id = any(:tenants)"
            ),
            {"users": demo_user_ids, "tenants": demo_tenant_ids},
        ).scalar_one(),
    )
