"""Per-request database access and authorization helpers.

Authorization is fail-closed and is never derived from anything a message,
model, or external caller supplied. A caller who lacks access to a tenant gets
exactly the response a caller asking for a non-existent tenant gets, so tenant
existence cannot be probed.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import current_app, g, session
from sqlalchemy import Connection, Engine

from relayops.domain.identity import Principal, Role, TenantContext
from relayops.errors import Forbidden, NotFound, Unauthenticated
from relayops.repositories.identity import (
    get_tenant_by_reference,
    load_principal,
)

SESSION_USER_KEY = "user_id"


def get_engine() -> Engine:
    engine = current_app.extensions.get("relayops_engine")
    if engine is None:
        factory = current_app.extensions.get("relayops_engine_factory")
        if factory is None:  # pragma: no cover - misconfiguration guard
            raise RuntimeError("database engine is not configured on this application")
        engine = factory()
        current_app.extensions["relayops_engine"] = engine
    return engine


def db() -> Connection:
    """One connection per request, closed by the app teardown."""
    connection = getattr(g, "db_connection", None)
    if connection is None:
        connection = get_engine().connect()
        g.db_connection = connection
    return connection


def close_db(exception: BaseException | None = None) -> None:
    connection = g.pop("db_connection", None)
    if connection is None:
        return
    if exception is None:
        connection.commit()
    else:
        connection.rollback()
    connection.close()


def current_principal_or_none() -> Principal | None:
    cached = getattr(g, "principal", None)
    if cached is not None:
        return cached
    raw_user_id = session.get(SESSION_USER_KEY)
    if not raw_user_id:
        return None
    try:
        user_id = uuid.UUID(str(raw_user_id))
    except ValueError:
        return None
    principal = load_principal(db(), user_id)
    if principal is not None:
        g.principal = principal
    return principal


def current_principal() -> Principal:
    principal = current_principal_or_none()
    if principal is None:
        raise Unauthenticated()
    return principal


def resolve_tenant(reference: str, *, principal: Principal | None = None) -> TenantContext:
    """Resolve a tenant reference the caller is allowed to see, or 404."""
    principal = principal or current_principal()
    tenant = get_tenant_by_reference(db(), reference)
    if tenant is None or not tenant.is_active:
        raise NotFound()

    role = principal.role_in(tenant.id)
    if role is None:
        # Deliberately the same error as a missing tenant: an account manager
        # must not be able to learn that another brokerage exists.
        raise NotFound()
    return TenantContext(tenant=tenant, role=role, principal=principal)


def require_login(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        current_principal()
        return view(*args, **kwargs)

    return wrapper


def require_role(*roles: Role) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Require one of ``roles`` in the tenant named by the ``tenant_ref`` view arg."""
    allowed = set(roles)

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any):
            principal = current_principal()
            reference = kwargs.get("tenant_ref")
            if reference is None:
                if not (principal.is_platform_operator and Role.PLATFORM_OPERATOR in allowed):
                    raise Forbidden()
                return view(*args, **kwargs)
            context = resolve_tenant(reference, principal=principal)
            if context.role not in allowed:
                raise Forbidden()
            g.tenant_context = context
            return view(*args, **kwargs)

        return wrapper

    return decorator


def require_platform_operator(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        if not current_principal().is_platform_operator:
            raise Forbidden()
        return view(*args, **kwargs)

    return wrapper
