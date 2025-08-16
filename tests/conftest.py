# tests/conftest.py
from __future__ import annotations

import secrets
import string
from typing import Iterator

import pytest
from sqlalchemy import create_engine, text

from fms_client.data.mfr_database import MfrDatabase
from fms_client.data.mfr_record import Base

import datetime as dt
from typing import Any, Dict
from sqlalchemy import String, Integer, DateTime
from fms_client.data.mfr_record import MfrRecord

PG_URL = "postgresql+psycopg2://fms_user:secure_password@localhost/mfr_database"


def _rand_schema(prefix: str = "test_") -> str:
    letters = string.ascii_lowercase + string.digits
    return prefix + "".join(secrets.choice(letters) for _ in range(8))


@pytest.fixture
def tmp_db() -> Iterator[MfrDatabase]:
    """
    Per-test isolated SCHEMA; sets search_path to that schema.
    Requires the DB user to have CREATE on the database.
    """
    schema = _rand_schema()
    admin_engine = create_engine(PG_URL, future=True)

    # create temp schema
    with admin_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}" AUTHORIZATION fms_user'))

    # bind engine to the temp schema via options
    url_with_schema = PG_URL + f"?options=-csearch_path%3D{schema}"
    db = MfrDatabase(url_with_schema)

    # create tables in the temp schema
    Base.metadata.create_all(db.engine)

    try:
        yield db
    finally:
        # drop everything in that schema
        with admin_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()
        db.engine.dispose()


@pytest.fixture(autouse=True)
def _inject_db_instance(monkeypatch: pytest.MonkeyPatch, tmp_db: MfrDatabase) -> None:
    """
    Autouse: ensure all code that imports `mfr_database_instance` gets THIS test's DB.
    Works for any test importing either `fms_client.data` or `fms_client.data.mfr_database`.
    """
    import fms_client.data as data_pkg
    monkeypatch.setattr(data_pkg, "mfr_database_instance", tmp_db, raising=True)

    import fms_client.data.mfr_database as data_mdb
    monkeypatch.setattr(data_mdb, "mfr_database_instance", tmp_db, raising=True)


def _default_for(col_name: str, col_type) -> Any:
    # Name-based overrides for required fields
    name_overrides = {
        "root_password": r"88RogueUnvar<ed",
        "ineez_user_password": r"Clutter%endor549",
        "ineez_admin_password": r"Comply?recook24",
        "admin_password": r"DandyGoog%e984",
        "wlan0_ap_password": r"965SmockWaln%t",
        "root_hash": r"$6$NYS+zaAVfEck$7YVtxIai.I3vlCaXv9Eoc5rttVlgyrVPUayn1qLH4vHBkgMIMMs616.1GoIkO2Si.FnSvnUHjsOUmSzjTYzFw/",
        "ineez_user_hash": r"$6$elHvzVPTgMrl$.8NpK2owx0sGv7M1rBSubZoHhasEz2KSXed5uXcZ07IufJfB8H/TUj3HZxO10tb/c4MtuYRzmi40wdU0ggpIc.",
        "ineez_admin_hash": r"$6$90aLIJbNhtBo$.BvD/sGKZFAdLg8as3pgYfLef9Ex09qCl7hDwL1YH6E4qbPBk02BSBR/QQt2/VHd0pYTT2kLdgtMRrGm5AW6A1",
        "admin_hash": r"$6$90aLIJbNhtBo$.BvD/sGKZFAdLg8as3pgYfLef9Ex09qCl7hDwL1YH6E4qbPBk02BSBR/QQt2/VHd0pYTT2kLdgtMRrGm5AW6A1",
        # "smart_charging": "false",
        # "plc_installed": "false",
        # "lte_installed": "false",
        # "ppp0_enabled": "false",
        # "requested": "false",
        # "allocated": "false",
    }
    if col_name in name_overrides:
        return name_overrides[col_name]

    # Generic by type
    if isinstance(col_type, String):
        return None  # let optional strings be NULL by default
    if isinstance(col_type, Integer):
        return None
    if isinstance(col_type, DateTime):
        return None

    return None

@pytest.fixture
def sample_record_data() -> Dict[str, Any]:
    """Programmatically derive a minimal valid payload for MfrRecord."""
    data: Dict[str, Any] = {}
    for col in MfrRecord.__table__.columns:
        if col.name == "id":
            continue
        # respect server/defaults where possible
        if col.default is not None or col.server_default is not None:
            # let DB / SQLAlchemy fill it
            continue
        # required vs optional
        if not col.nullable:
            data[col.name] = _default_for(col.name, col.type)
        else:
            data[col.name] = _default_for(col.name, col.type)

    # Ensure this test stays “unassigned” until request step
    data.setdefault("barcode", None)
    return data


@pytest.fixture
def fake_passwords(monkeypatch: pytest.MonkeyPatch, sample_record_data):
    """
    Global helper for tests that exercise `create_record` in the shell:
    it monkeypatches the passwords generator to return a stable payload.
    """
    class _FakePasswords:
        def generate_all(self):
            return True, dict(sample_record_data)

    import fms_client.data.passwords as pw_mod
    monkeypatch.setattr(pw_mod, "passwords_instance", _FakePasswords(), raising=True)

