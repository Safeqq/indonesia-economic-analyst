import json
from datetime import UTC, datetime

from pipelines.extract.extract_world_bank import WorldBankExtraction
from pipelines.extract.raw_snapshot import save_snapshot


def test_snapshot_preserves_source_response(tmp_path):
    source_record = {
        "indicator": {"id": "SP.POP.TOTL", "value": "Population"},
        "country": {"id": "ID", "value": "Indonesia"},
        "countryiso3code": "IDN",
        "date": "2023",
        "value": 281190067,
    }
    payload = [{"page": 1, "total": 1}, [source_record]]
    extraction = WorldBankExtraction(
        country="IDN",
        indicator="SP.POP.TOTL",
        source_url=(
            "https://api.worldbank.org/v2/country/IDN/indicator/SP.POP.TOTL"
        ),
        parameters={"format": "json", "date": "2023:2023"},
        payload=payload,
        records=payload[1],
    )

    path = save_snapshot(
        [extraction], datetime(2026, 1, 1, tzinfo=UTC), tmp_path
    )
    snapshot = json.loads(path.read_text(encoding="utf-8"))

    assert snapshot["record_count"] == 1
    assert snapshot["indicator_list"] == ["SP.POP.TOTL"]
    assert snapshot["requests"][0]["response"] == payload
