"""Engine and connection management.

A single lazily-created engine per process. Repositories receive an explicit
connection or session; nothing reaches for a thread-local behind the caller's
back.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from relayops.config import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def migrations_path(settings: Settings) -> Path:
    directory = Path(settings.migrations_dir)
    return directory if directory.is_absolute() else BACKEND_ROOT / directory


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        connect_args={"application_name": "relayops"},
    )


@lru_cache(maxsize=4)
def _cached_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        connect_args={"application_name": "relayops"},
    )


def get_engine(settings: Settings) -> Engine:
    return _cached_engine(settings.database_url)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def transaction(engine: Engine) -> Iterator[Connection]:
    """Run a unit of work in one transaction, committing on clean exit."""
    with engine.begin() as connection:
        yield connection
