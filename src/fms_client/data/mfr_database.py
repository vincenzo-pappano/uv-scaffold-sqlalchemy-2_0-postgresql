# src/fms_client/data/mfr_database.py
from __future__ import annotations

from fms_client.utils.logger import logger_base

from typing import Dict, Optional, Tuple, List

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select, and_, or_

from .mfr_record import MfrRecord  # model
# If you centralize Base in db.py, import it there; otherwise MfrRecord.metadata works too.
from .mfr_record import Base  # adjust to `.db import Base` if that's your project pattern


logger = logger_base.get_logger(__name__)

# --- PostgreSQL connection ---
# Assumes you completed:
#   - DB name: mfr_database
#   - User:    fms_user  (password: secure_password)
#   - Host:    localhost (default port 5432)
DATABASE_URL = "postgresql+psycopg2://fms_user:secure_password@localhost/mfr_database"


class MfrDatabase:
    def __init__(self, db_url: str = DATABASE_URL, echo: bool = False) -> None:
        self.db_url = db_url
        self.engine = create_engine(
            db_url,
            echo=echo,
            pool_pre_ping=True,  # survive stale connections
            future=True,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False, future=True)
        logger.debug('Created session')

        # Create tables if they don't exist (fine for dev/test)
        Base.metadata.create_all(self.engine)

    # ---- sessions ----
    def create_session(self) -> Session:
        """Create a new SQLAlchemy Session. Prefer use as a context manager: `with db.create_session() as s:`"""
        return self.SessionLocal()

    # ---- creation ----
    def create_mfr_record(self, data: Dict[str, str]) -> Tuple[bool, Optional[int]]:
        """Insert a new MfrRecord from a dict payload."""
        try:
            with self.create_session() as session:
                rec = MfrRecord(**data)
                # keep your timestamp side-effects
                if getattr(rec, "requested", None) == "true" and getattr(rec, "requested_at", None) is None:
                    # timestamp is set by your model helper in earlier version; if not, leave as-is
                    pass
                if getattr(rec, "allocated", None) == "true" and getattr(rec, "allocated_at", None) is None:
                    pass

                session.add(rec)
                session.flush()  # obtain PK
                rec_id = rec.id
                session.commit()
                return True, rec_id
        except Exception as e:
            # log if you have a logger; return safe default
            logger.error("create_mfr_record failed: %s", e)
            return False, None

    # ---- lookups ----
    def retrieve_root_password_and_hash(self, barcode: str) -> Tuple[bool, Optional[Dict[str, str]]]:
        try:
            with self.create_session() as session:
                rec = session.execute(
                    select(MfrRecord).where(MfrRecord.barcode == barcode)
                ).scalar_one_or_none()
                if rec:
                    return True, {"root_password": rec.root_password, "root_hash": rec.root_hash}
                return False, None
        except Exception:
            return False, None

    def retrieve_id_from_barcode(self, barcode: str) -> Tuple[bool, Optional[int]]:
        try:
            with self.create_session() as session:
                rec_id = session.execute(
                    select(MfrRecord.id).where(MfrRecord.barcode == barcode)
                ).scalar_one_or_none()
                return (True, rec_id) if rec_id is not None else (False, None)
        except Exception:
            return False, None

    # ---- lifecycle: request / allocate ----
    def request_available_record(self, barcode: str) -> tuple[bool, int | None]:
        try:
            # check if barcode is already in database, if yes return ok and record id
            with self.create_session() as session:
                rec = session.execute(
                    select(MfrRecord)
                    .where(
                        MfrRecord.barcode == barcode
                    )
                    .order_by(MfrRecord.id.asc())
                ).scalar_one_or_none()
                if rec:
                    logger.info("Record {rec.id} already associated with barcode {barcode}")
                    return True, rec.id
                else:
                    logger.info("Attempting to find a record to associate with barcode {barcode}")
                    
            # check if there is an available record to associate with the barcode            
            with self.create_session() as session:
                rec = session.execute(
                    select(MfrRecord)
                    .where(
                        MfrRecord.barcode.is_(None),  # only unassigned
                        or_(MfrRecord.requested == "false", MfrRecord.requested.is_(None)),
                        or_(MfrRecord.allocated == "false", MfrRecord.allocated.is_(None)),
                    )
                    .order_by(MfrRecord.id.asc())
                ).scalars().first()
                if not rec:
                    logger.error('Could not find available record to associate with barcode {barcode}')
                    return False, None
                rec.barcode = barcode
                if hasattr(rec, "set_requested"):
                    rec.set_requested("true")
                else:
                    rec.requested = "true"
                session.commit()
                return True, rec.id

        except Exception as e:
            logger.error(f"Exception {e}")
            return False, None

    def allocate_requested_record(self, barcode: str) -> Tuple[bool, Optional[int]]:
        """
        If the record for 'barcode' is requested='true' and allocated='false',
        set allocated='true' (and timestamp if supported).
        """
        try:
            with self.create_session() as session:
                rec = session.execute(
                    select(MfrRecord).where(MfrRecord.barcode == barcode)
                ).scalar_one_or_none()

                if rec and rec.requested == "true" and rec.allocated == "false":
                    if hasattr(rec, "set_allocated"):
                        rec.set_allocated("true")
                    else:
                        rec.allocated = "true"
                    session.commit()
                    return True, rec.id

                return False, None
        except Exception:
            return False, None

    # ---- printing / formatting (string-returning helpers) ----
    def record_str_by_id(self, record_id: int) -> Optional[str]:
        try:
            with self.create_session() as session:
                rec = session.execute(
                    select(MfrRecord).where(MfrRecord.id == record_id)
                ).scalar_one_or_none()
            return self._format_record(rec) if rec else None
        except Exception:
            return None

    def record_str_by_barcode(self, barcode: str) -> Optional[str]:
        try:
            with self.create_session() as session:
                rec = session.execute(
                    select(MfrRecord).where(MfrRecord.barcode == barcode)
                ).scalar_one_or_none()
            return self._format_record(rec) if rec else None
        except Exception:
            return None

    def _format_record(self, rec: MfrRecord) -> str:
        n = 25
        lines = [
            "=" * 50,
            f"{'Record for ID':<{n}}:  {rec.id}",
            "=" * 50,
            f"{'ID':<{n}}:  {rec.id}",
            f"{'Barcode':<{n}}:  {rec.barcode or 'N/A'}",
            f"{'Variant Name':<{n}}:  {rec.variant_name or 'N/A'}",
            f"{'Root Password':<{n}}:  {rec.root_password or 'N/A'}",
            f"{'Root Hash':<{n}}:  {rec.root_hash or 'N/A'}",
            f"{'Ineez User Password':<{n}}:  {rec.ineez_user_password or 'N/A'}",
            f"{'Ineez Admin Password':<{n}}:  {rec.ineez_admin_password or 'N/A'}",
            f"{'Admin Password':<{n}}:  {rec.admin_password or 'N/A'}",
            f"{'Ineez User Hash':<{n}}:  {rec.ineez_user_hash or 'N/A'}",
            f"{'Ineez Admin Hash':<{n}}:  {rec.ineez_admin_hash or 'N/A'}",
            f"{'Admin Hash':<{n}}:  {rec.admin_hash or 'N/A'}",
            f"{'WLAN0 AP Password':<{n}}:  {rec.wlan0_ap_password or 'N/A'}",
            f"{'WLAN0 AP Password PSK':<{n}}:  {rec.wlan0_ap_password_psk or 'N/A'}",
            f"{'WLAN0 AP SSID':<{n}}:  {rec.wlan0_ap_ssid or 'N/A'}",
            f"{'Smart Charging':<{n}}:  {rec.smart_charging}",
            f"{'PLC Installed':<{n}}:  {rec.plc_installed}",
            f"{'LTE Installed':<{n}}:  {rec.lte_installed}",
            f"{'PPP0 Enabled':<{n}}:  {rec.ppp0_enabled}",
            f"{'Modem GSN':<{n}}:  {rec.modem_gsn or 'N/A'}",
            f"{'Modem QCCID':<{n}}:  {rec.modem_qccid or 'N/A'}",
            f"{'Requested':<{n}}:  {rec.requested_at if rec.requested == 'true' else '----------'}",
            f"{'Allocated':<{n}}:  {rec.allocated_at if rec.allocated == 'true' else '----------'}",
        ]
        return "\n".join(lines)

    # ---- dump/list helpers ----
    def get_mfr_records(self) -> List[MfrRecord]:
        with self.create_session() as session:
            return list(session.execute(select(MfrRecord).order_by(MfrRecord.id.asc())).scalars().all())

    # ---- selective retrieval / update ----
    def retrieve_data_by_barcode(self, barcode: str, columns: List[str]) -> Tuple[bool, Optional[Dict[str, str]]]:
        try:
            with self.create_session() as session:
                rec = session.execute(
                    select(MfrRecord).where(MfrRecord.barcode == barcode)
                ).scalar_one_or_none()

                if not rec:
                    return False, None

                data: Dict[str, str] = {}
                for col in columns:
                    if not hasattr(rec, col):
                        return False, None
                    data[col] = getattr(rec, col)
                return True, data
        except Exception:
            return False, None

    def set_data_by_barcode(self, barcode: str, data: Dict[str, str]) -> bool:
        try:
            with self.create_session() as session:
                rec = session.execute(
                    select(MfrRecord).where(MfrRecord.barcode == barcode)
                ).scalar_one_or_none()

                if not rec:
                    return False

                # validate keys
                for k in data.keys():
                    if not hasattr(rec, k):
                        return False

                for k, v in data.items():
                    setattr(rec, k, v)

                session.commit()
                return True
        except Exception:
            return False


# Default instance used by the shell/tests
mfr_database_instance = MfrDatabase(DATABASE_URL)
