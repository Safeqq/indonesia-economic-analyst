import json
from datetime import UTC, datetime

from pipelines.extract.bps_snapshot import save_bps_snapshot
from tests.pipeline.bps_fixtures import extraction


def test_bps_snapshot_preserves_payload_without_api_key(tmp_path):
    source = extraction()

    path = save_bps_snapshot(source, datetime(2026, 1, 1, tzinfo=UTC), tmp_path)
    serialized = path.read_text(encoding="utf-8")
    snapshot = json.loads(serialized)

    assert snapshot["variable_ids"] == [543, 1975]
    assert snapshot["record_count"] == 6
    assert snapshot["requests"][0]["response"] == source.province_request.payload
    assert "key" not in serialized.casefold()
    assert "secret" not in serialized.casefold()
