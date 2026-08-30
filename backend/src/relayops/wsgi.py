"""WSGI entrypoint.

Configuration comes entirely from the environment, which is how every container
is configured. Migrations are applied on boot so a fresh deployment reaches a
usable schema without a separate release step; ``run_migrations`` is idempotent
and records what it has already applied.
"""

from __future__ import annotations

import os

from relayops.app import create_app
from relayops.logging import get_logger

log = get_logger("relayops.wsgi")

application = create_app()


def _bootstrap() -> None:
    """Apply migrations, and seed the demo when explicitly asked to."""
    from pathlib import Path

    from relayops.api.deps import get_engine
    from relayops.migrations import run_migrations

    with application.app_context():
        engine = get_engine()
        applied = run_migrations(engine, Path(os.environ.get("MIGRATIONS_DIR", "migrations")))
        log.info("migrations_applied", count=len(applied))

        if os.environ.get("SEED_ON_BOOT", "").lower() in {"1", "true", "yes"}:
            from relayops.seed import seed_demo_data
            from relayops.seed_freight import seed_freight

            with engine.begin() as connection:
                seed_demo_data(connection)
                freight = seed_freight(connection)
            log.info("demo_seeded", loads=freight.loads)


if os.environ.get("MIGRATE_ON_BOOT", "true").lower() in {"1", "true", "yes"}:
    _bootstrap()
