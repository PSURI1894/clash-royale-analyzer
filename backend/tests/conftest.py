from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cr_helper import models  # noqa: F401 — register models on Base
from cr_helper.db import Base


@pytest.fixture()
def session() -> Session:
    """An isolated in-memory SQLite session (shared connection via StaticPool)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    with testing_session() as s:
        yield s
    Base.metadata.drop_all(engine)
