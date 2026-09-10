from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pipelines.extract.extract_world_bank import (
    BASE_URL,
    SOURCE_CODE,
    WorldBankExtraction,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw" / SOURCE_CODE


def _isoformat_utc(timestamp: datetime) -> str:
    return timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")


def build_snapshot(
    extractions: list[WorldBankExtraction], retrieved_at: datetime
) -> dict[str, Any]:
    if not extractions:
        raise ValueError("Snapshot World Bank memerlukan minimal satu hasil ekstraksi")

    countries = {extraction.country for extraction in extractions}
    if len(countries) != 1:
        raise ValueError("Satu snapshot hanya boleh berisi satu negara")

    return {
        "source_code": SOURCE_CODE,
        "source_url": BASE_URL,
        "retrieved_at": _isoformat_utc(retrieved_at),
        "country": extractions[0].country,
        "indicator_list": [item.indicator for item in extractions],
        "record_count": sum(len(item.records) for item in extractions),
        "requests": [
            {
                "source_url": item.source_url,
                "parameters": item.parameters,
                "response": item.payload,
            }
            for item in extractions
        ],
    }


def save_snapshot(
    extractions: list[WorldBankExtraction],
    retrieved_at: datetime,
    directory: Path = DEFAULT_RAW_DIRECTORY,
) -> Path:
    snapshot = build_snapshot(extractions, retrieved_at)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = retrieved_at.strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"world_bank_{extractions[0].country}_{timestamp}.json"
    destination = directory / filename
    with destination.open("x", encoding="utf-8") as snapshot_file:
        json.dump(snapshot, snapshot_file, ensure_ascii=False, indent=2)
        snapshot_file.write("\n")
    return destination
