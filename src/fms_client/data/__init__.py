# data/__init__.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from .db import Base
from .mfr_record import MfrRecord
from .mfr_database import MfrDatabase, mfr_database_instance


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Context-managed Session tied to the default database instance.
    Usage:
        from data import get_session
        with get_session() as session:
            ...
    """
    session = mfr_database_instance.create_session()
    try:
        yield session
    finally:
        session.close()


__all__ = [
    "Base",
    "MfrRecord",
    "MfrDatabase",
    "mfr_database_instance",
    "get_session",
]
