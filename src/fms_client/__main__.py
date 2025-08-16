# app/main.py
from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

from fms_client.data.mfr_database import mfr_database_instance as mfr_database
from fms_client.device.params import device_params_instance as device_params  # implied
from fms_client.data.passwords import passwords_instance as passwords        # implied


from fms_client.utils.logger import logger_base
logger = logger_base.get_logger(__name__)


def main() -> None:

    logger.info("START -- POSTGRESQL")

    # 1) Generate passwords/secrets
    ok, mfr_data = passwords.generate_all()  # type: ignore[assignment]
    if not ok or mfr_data is None:
        logger.error("Failed to generate password data.")
        return

    # 2) Insert a new record
    ok, record_id = mfr_database.create_mfr_record(mfr_data)
    if not ok or record_id is None:
        logger.error("Failed to create MFR record.")
        return

    logger.info("Created record: %s", record_id)
    s = mfr_database.record_str_by_id(record_id)
    if s:
        print(s)

    # 3) Request an available record by assigning a barcode
    barcode = "000000221013"
    ok, requested_id = mfr_database.request_available_record(barcode)
    if not ok or requested_id is None:
        logger.error("Failed to request an available record for barcode %s.", barcode)
        return

    logger.info("Requested record: %s", requested_id)
    s = mfr_database.record_str_by_barcode(barcode)
    if s:
        print(s)

    # 4) Retrieve root password & hash
    ok, info = mfr_database.retrieve_root_password_and_hash(barcode)
    if not ok or info is None:
        logger.error("Failed to retrieve root password/hash for barcode %s.", barcode)
        return

    logger.info("root_info: %s", info.get("root_password"))
    logger.info("root_hash: %s", info.get("root_hash"))

    # 5) Retrieve a selected set of fields
    requested_fields = [
        "root_password",
        "root_hash",
        "ineez_user_password",
        "ineez_user_hash",
        "ineez_admin_password",
        "ineez_admin_hash",
        "admin_password",
        "admin_hash",
    ]
    ok, data = mfr_database.retrieve_data_by_barcode(barcode, requested_fields)
    if not ok or data is None:
        logger.error("Failed to retrieve selected fields for barcode %s.", barcode)
        return

    for k, v in data.items():
        print(f"{k}: {v}")

    # 6) Update feature flags
    patch = {
        "smart_charging": "true",
        "plc_installed": "true",
        "lte_installed": "true",
        "ppp0_enabled": "true",
    }
    if not mfr_database.set_data_by_barcode(barcode, patch):
        logger.error("Failed to update feature flags for barcode %s.", barcode)
        return

    s = mfr_database.record_str_by_barcode(barcode)
    if s:
        print(s)
    time.sleep(2.0)

    # 7) Allocate the requested record
    ok, allocated_id = mfr_database.allocate_requested_record(barcode)
    if not ok or allocated_id is None:
        logger.error("Failed to allocate record for barcode %s.", barcode)
        return

    s = mfr_database.record_str_by_id(allocated_id)
    if s:
        print(s)
        
    logger.info("Done")


if __name__ == "__main__":
    main()
