# src/fms_client/data/mfr_record.py
from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class MfrRecord(Base):
    __tablename__ = "mfr"

    id = Column(Integer, primary_key=True, autoincrement=True)

    barcode = Column(String(64), nullable=True)
    variant_name = Column(String(64), nullable=True)

    root_password = Column(String(128), nullable=False)
    root_hash = Column(String(128), nullable=False)

    admin_password = Column(String(128), nullable=False)
    admin_hash = Column(String(128), nullable=False)

    ineez_admin_password = Column(String(128), nullable=False)
    ineez_admin_hash = Column(String(128), nullable=False)

    ineez_user_password = Column(String(128), nullable=False)
    ineez_user_hash = Column(String(128), nullable=False)

    wlan0_ap_password = Column(String(128), nullable=False)
    wlan0_ap_password_psk = Column(String(128), nullable=False)

    device_id = Column(String(128), nullable=True)
    wlan0_ap_ssid = Column(String(128), nullable=True)

    smart_charging = Column(String(8), default="false")
    plc_installed = Column(String(8), default="false")
    lte_installed = Column(String(8), default="false")

    ppp0_enabled = Column(String(8), default="false")

    modem_gsn = Column(String(128), nullable=True)
    modem_qccid = Column(String(128), nullable=True)

    requested = Column(String(8), default="false")
    allocated = Column(String(8), default="false")

    requested_at = Column(DateTime, nullable=True)
    allocated_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<MfrRecord(id={self.id}, barcode={self.barcode}, "
            f"requested={self.requested}, allocated={self.allocated})>"
        )
