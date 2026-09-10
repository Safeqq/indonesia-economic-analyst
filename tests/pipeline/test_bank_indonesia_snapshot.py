import hashlib
import json
from datetime import UTC, datetime

from pipelines.extract.bank_indonesia_snapshot import (
    save_bank_indonesia_snapshot,
)
from tests.pipeline.bank_indonesia_fixtures import extraction_fixture


def test_bank_indonesia_snapshot_preserves_exact_source_bytes(tmp_path):
    extraction = extraction_fixture()
    snapshot = save_bank_indonesia_snapshot(
        extraction,
        datetime(2026, 3, 1, tzinfo=UTC),
        tmp_path,
    )

    assert snapshot.bi_rate_path.read_bytes() == extraction.bi_rate.payload
    assert snapshot.jisdor_path.read_bytes() == extraction.jisdor.payload
    manifest = json.loads(snapshot.manifest_path.read_text(encoding="utf-8"))
    resources = {item["name"]: item for item in manifest["resources"]}
    assert (
        resources["bi_rate"]["sha256"]
        == hashlib.sha256(extraction.bi_rate.payload).hexdigest()
    )
    assert resources["jisdor"]["parameters"]["mts"] == "USD"
