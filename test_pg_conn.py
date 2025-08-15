# test_pg_conn.py
from fms_client.data.mfr_database import mfr_database_instance

# Force table creation (if they don't exist)
print("Creating tables...")
mfr_database_instance.engine.echo = True  # Show SQL for debugging
from fms_client.data.mfr_record import Base
Base.metadata.create_all(mfr_database_instance.engine)

# Try inserting a dummy record
ok, rec_id = mfr_database_instance.create_mfr_record({
    "barcode": "TEST123",
    "variant_name": "PostgreSQL Test",
    "root_password": "pass",
    "root_hash": "hash",
    "admin_password": "pass",
    "admin_hash": "hash",
    "ineez_admin_password": "pass",
    "ineez_admin_hash": "hash",
    "ineez_user_password": "pass",
    "ineez_user_hash": "hash",
    "wlan0_ap_password": "pass",
    "wlan0_ap_password_psk": "psk",
    "smart_charging": "false",
    "plc_installed": "false",
    "lte_installed": "false",
    "ppp0_enabled": "false",
    "requested": "false",
    "allocated": "false",
})
print(f"Insert OK: {ok}, Record ID: {rec_id}")

# Try retrieving it
if rec_id:
    print(mfr_database_instance.record_str_by_id(rec_id))
