"""Operational entry points used by containers and by developers.

`relayops migrate --check` is what the web entrypoint and readiness probe use to
refuse traffic while the schema is behind.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence

from relayops.config import Settings
from relayops.db import build_engine, migrations_path
from relayops.migrations import check_migrations, run_migrations


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="relayops", description="RelayOps operations CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    migrate = sub.add_parser("migrate", help="apply pending SQL migrations")
    migrate.add_argument(
        "--check",
        action="store_true",
        help="report pending migrations without applying them (exit 1 if behind)",
    )

    seed = sub.add_parser("seed", help="apply deterministic demo data")
    seed.add_argument("--seed", type=int, default=1048, help="deterministic seed value")

    return parser


def main(argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    settings = Settings.from_env(environ if environ is not None else os.environ)
    engine = build_engine(settings)
    directory = migrations_path(settings)

    try:
        if args.command == "migrate":
            if args.check:
                status = check_migrations(engine, directory)
                if status.mismatched:
                    print(f"checksum mismatch: {', '.join(status.mismatched)}", file=sys.stderr)
                    return 2
                if status.pending:
                    print(f"pending migrations: {', '.join(status.pending)}")
                    return 1
                print(f"schema is up to date ({len(status.applied)} applied)")
                return 0

            applied = run_migrations(engine, directory)
            print(
                f"applied {len(applied)} migration(s): {', '.join(applied)}"
                if applied
                else "applied 0 migration(s): schema already up to date"
            )
            return 0

        if args.command == "seed":
            from relayops.seed import seed_demo_data

            with engine.begin() as connection:
                summary = seed_demo_data(connection, seed=args.seed)
            print(
                f"seeded tenants={summary.tenants} users={summary.users} "
                f"memberships={summary.memberships}"
            )
            return 0
    finally:
        engine.dispose()

    return 0  # pragma: no cover - argparse guarantees a known command


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
