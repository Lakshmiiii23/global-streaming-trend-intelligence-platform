import pytest
from src.storage.r2_client import BronzeStorageManager

def test_bronze_storage_roundtrip(tmp_path):
    mgr = BronzeStorageManager()
    mgr.backend = "local"
    mgr.local_dir = tmp_path

    sample_data = [
        {"title": "Test Show", "platform": "netflix", "rank": 1, "points": 800}
    ]
    batch_key = mgr.save_batch(sample_data, batch_id="unit_test_1", chart_date="2026-10-01")
    assert "unit_test_1" in batch_key

    loaded = mgr.load_batch(batch_key)
    assert loaded["metadata"]["record_count"] == 1
    assert loaded["records"][0]["title"] == "Test Show"

    batches = mgr.list_batches(chart_date="2026-10-01")
    assert len(batches) >= 1
