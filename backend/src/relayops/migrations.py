"""Handwritten SQL migrations.

RelayOps deliberately has no Alembic dependency. Migrations are numbered SQL
files applied in order, each inside one transaction, each recorded with the
SHA-256 of its bytes. Editing an already-applied file is an error rather than a
silent divergence, and the API refuses to serve traffic while a migration is
pending.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, text

# One arbitrary but stable key so concurrent boots serialise on the same lock.
MIGRATION_LOCK_KEY = 8_140_251_048

_FILENAME = re.compile(r"^(?P<number>\d{3,})_(?P<name>[a-z0-9_]+)\.sql$")

_BOOTSTRAP = """
create table if not exists schema_migrations (
    version    text        primary key,
    checksum   text        not null,
    applied_at timestamptz not null default now()
)
"""


class MigrationError(RuntimeError):
    """Base class for migration failures."""


class MigrationChecksumMismatch(MigrationError):
    """An already-applied migration file changed on disk."""


@dataclass(frozen=True, slots=True)
class MigrationFile:
    version: str
    path: Path
    checksum: str
    sql: str

    @property
    def number(self) -> int:
        return int(self.version.split("_", 1)[0])


@dataclass(frozen=True, slots=True)
class MigrationStatus:
    applied: tuple[str, ...]
    pending: list[str]
    mismatched: list[str]

    @property
    def is_current(self) -> bool:
        return not self.pending and not self.mismatched


def discover_migrations(directory: Path) -> list[MigrationFile]:
    """Return every ``NNN_name.sql`` file in numeric order."""
    if not directory.is_dir():
        raise MigrationError(f"migration directory not found: {directory}")

    files: list[MigrationFile] = []
    for path in sorted(directory.iterdir()):
        if path.suffix != ".sql" or not path.is_file():
            continue
        match = _FILENAME.match(path.name)
        if not match:
            raise MigrationError(
                f"migration filename must look like 001_name.sql, got {path.name!r}"
            )
        raw = path.read_bytes()
        files.append(
            MigrationFile(
                version=path.stem,
                path=path,
                checksum=hashlib.sha256(raw).hexdigest(),
                sql=raw.decode("utf-8"),
            )
        )

    numbers = [f.number for f in files]
    if len(set(numbers)) != len(numbers):
        raise MigrationError("duplicate migration numbers found")
    return sorted(files, key=lambda f: f.number)


def _applied_checksums(connection) -> dict[str, str]:
    connection.execute(text(_BOOTSTRAP))
    rows = connection.execute(text("select version, checksum from schema_migrations")).all()
    return dict(rows)


def check_migrations(engine: Engine, directory: Path) -> MigrationStatus:
    """Compare files on disk against what the database has applied."""
    files = discover_migrations(directory)
    with engine.begin() as connection:
        applied = _applied_checksums(connection)

    pending = [f.version for f in files if f.version not in applied]
    mismatched = [
        f.version
        for f in files
        if f.version in applied and applied[f.version] != f.checksum
    ]
    return MigrationStatus(
        applied=tuple(sorted(applied)), pending=pending, mismatched=mismatched
    )


def run_migrations(engine: Engine, directory: Path) -> list[str]:
    """Apply every pending migration; return the versions applied by this call."""
    files = discover_migrations(directory)

    with engine.begin() as connection:
        _applied_checksums(connection)

    applied_now: list[str] = []
    with engine.connect() as lock_connection:
        # Serialise concurrent boots: two web containers starting together must
        # not race to apply the same file.
        lock_connection.execute(
            text("select pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY}
        )
        lock_connection.commit()
        try:
            with engine.begin() as connection:
                applied = _applied_checksums(connection)
            for migration in files:
                recorded = applied.get(migration.version)
                if recorded is not None:
                    if recorded != migration.checksum:
                        raise MigrationChecksumMismatch(
                            f"{migration.version} changed after it was applied; "
                            "add a new migration instead of editing history"
                        )
                    continue
                with engine.begin() as connection:
                    # exec_driver_sql: raw SQL must not be scanned for bind params.
                    connection.exec_driver_sql(migration.sql)
                    connection.execute(
                        text(
                            "insert into schema_migrations (version, checksum) "
                            "values (:version, :checksum)"
                        ),
                        {"version": migration.version, "checksum": migration.checksum},
                    )
                applied_now.append(migration.version)
        finally:
            lock_connection.execute(
                text("select pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY}
            )
            lock_connection.commit()

    return applied_now
