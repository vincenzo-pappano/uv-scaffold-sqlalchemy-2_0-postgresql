#!/usr/bin/python3
from __future__ import annotations

import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Dict, Tuple, List

from fms_client.utils.logger import logger_base
logger = logger_base.get_logger(__name__)


def _immutable_board_variants() -> Mapping[str, Dict[str, str]]:
    return MappingProxyType({
        "1013": {"name": "local"},
        "1019": {"name": "connected"},
        "1020": {"name": "smart"},
    })


@dataclass(frozen=True, slots=True)
class Params:
    # device / versions
    modem_port: str = "/dev/ttyUSB6"
    hmi_version: str = "2008"
    m2_version: str = "220810220e20"
    fw_version: str = "Ag-MBI-v4.5.3-0-g0ec30e6c"

    # lifecycle / status
    start_time: float = field(default_factory=time.time)
    error: bool = False
    error_message: Tuple[str, ...] = field(default_factory=tuple)
    error_code: str = ""
    error_description: str = ""

    # The database record ID
    record_id: int = -1


    # keys to fetch/update (now immutable tuple)
    list: Tuple[str, ...] = (
        "root_hash",
        "admin_hash",
        "ineez_admin_hash",
        "ineez_user_hash",
        "smart_charging",
        "plc_installed",
        "lte_installed",
        "ppp0_enabled",
        "wlan0_ap_ssid",
        "wlan0_ap_password_psk",
    )

    use_hash: bool = True

    # barcode and variants (immutable mapping)
    board_variants: Mapping[str, Dict[str, str]] = field(
        default_factory=_immutable_board_variants
    )

    # ---------------------------------------------------------------
    # Charger agnostic - No need for barcode or device_id
    # ---------------------------------------------------------------
    root_password: str = "?"
    root_hash: str = "??"
    root_hash_remote: str = "remote???"

    admin_password: str = "?"
    admin_hash: str = "?"
    admin_hash_remote: str = "remote???"

    ineez_admin_password: str = "?"
    ineez_admin_hash: str = "??"
    ineez_admin_hash_remote: str = "remote???"

    ineez_user_password: str = "?"
    ineez_user_hash: str = "??"
    ineez_user_hash_remote: str = "remote???"

    wlan0_ap_password: str = "?"

    # ---------------------------------------------------------------
    # FormQrScanner - After acquiring the barcode
    # ---------------------------------------------------------------
    barcode: str = ""          # complete barcode
    board_variant: str = ""    # 1013,1019,1020
    board_serial: str = ""     #
    variant_name: str = ""     #

    # ---------------------------------------------------------------
    # Configured after barcode is validated
    # ---------------------------------------------------------------
    smart_charging: str = "false"
    smart_charging_remote: str = "remote???"

    plc_installed: str = "false"
    plc_installed_remote: str = "remote???"

    lte_installed: str = "false"
    lte_installed_remote: str = "remote???"

    ppp0_enabled: str = "false"
    ppp0_enabled_remote: str = "remote???"

    # ---------------------------------------------------------------
    # Configured after first boot: needs device_id
    # ---------------------------------------------------------------
    device_id: str = ""            # get_devid()
    board_indentifier: str = ""    # IOTM+device_id

    wlan0_ap_ssid: str = "?"
    wlan0_ap_ssid_remote: str = "remote???"

    wlan0_ap_password_psk: str = "??"
    wlan0_ap_password_psk_remote: str = "remote???"

    fw_version_remote: str = "remote???"



# keep your module-level singleton
device_params_instance = Params()
logger.debug("Instantiated frozen Params dataclass")
