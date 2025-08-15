from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class MfrRecord(Base):
    __tablename__ = "mfr_records"
    __table_args__ = (
        UniqueConstraint("barcode", name="uq_mfr_records_barcode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers / variant
    barcode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    variant_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Passwords (plaintext saved per your existing workflow)
    root_password: Mapped[str] = mapped_column(String(32), nullable=False)
    ineez_user_password: Mapped[str] = mapped_column(String(32), nullable=False)
    ineez_admin_password: Mapped[str] = mapped_column(String(32), nullable=False)
    admin_password: Mapped[str] = mapped_column(String(32), nullable=False)
    wlan0_ap_password: Mapped[str] = mapped_column(String(32), nullable=False)

    # Hashes
    root_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    ineez_user_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    ineez_admin_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    admin_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    # Wi‑Fi extras (optional)
    wlan0_ap_password_psk: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    wlan0_ap_ssid: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Feature flags (stored as 'true'/'false' strings, per existing code)
    smart_charging: Mapped[Optional[str]] = mapped_column(String(8), default="false")
    plc_installed: Mapped[Optional[str]] = mapped_column(String(8), default="false")
    lte_installed: Mapped[Optional[str]] = mapped_column(String(8), default="false")
    ppp0_enabled: Mapped[Optional[str]] = mapped_column(String(8), default="false")

    # Modem (optional)
    modem_gsn: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    modem_qccid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Lifecycle flags + timestamps
    requested: Mapped[str] = mapped_column(String(5), default="false", nullable=False)
    allocated: Mapped[str] = mapped_column(String(5), default="false", nullable=False)
    requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    allocated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Helpers to set timestamps when flag flips true
    def set_requested(self, value: str) -> None:
        if value == "true" and self.requested != "true":
            self.requested_at = datetime.utcnow()
        self.requested = value

    def set_allocated(self, value: str) -> None:
        if value == "true" and self.allocated != "true":
            self.allocated_at = datetime.utcnow()
        self.allocated = value
