"""Database engine, session factory and declarative base.

Sync SQLAlchemy 2.0. Deliberately DB-agnostic: the same models run on SQLite
(local dev) and Postgres (Docker/production). pgvector-specific columns are not
introduced until Phase 4.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = settings.database_url
    connect_args: dict = {}
    if url.startswith("sqlite"):
        # FastAPI runs sync endpoints in a threadpool; allow cross-thread use.
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables if they do not exist (dev bootstrap; Alembic owns prod)."""
    from . import models  # noqa: F401 — ensure models are registered on Base

    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    with SessionLocal() as session:
        yield session
