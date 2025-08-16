# tests/test_basic_insert.py
from fms_client.data.mfr_record import MfrRecord

barcode = "000000031019"

def test_insert_and_retrieve(tmp_db, sample_record_data):
    # Use model-driven defaults from conftest, then set a barcode for this test
    rec = MfrRecord(**sample_record_data)
    rec.barcode = barcode

    with tmp_db.create_session() as session:
        session.add(rec)
        session.commit()
        rec_id = rec.id

    with tmp_db.create_session() as session:
        fetched = session.get(MfrRecord, rec_id)
        assert fetched is not None
        assert fetched.barcode == barcode
        assert fetched.variant_name in (sample_record_data.get("variant_name"), None)
