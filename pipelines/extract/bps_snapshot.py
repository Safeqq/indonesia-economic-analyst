from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pipelines.extract.extract_bps import SOURCE_CODE, BPSExtraction

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BPS_RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw" / SOURCE_CODE


def _isoformat_utc(timestamp: datetime) -> str:
    return timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")


def build_bps_snapshot(
    extraction: BPSExtraction, retrieved_at: datetime
) -> dict[str, Any]:
    requests = extraction.requests
    if not requests:
        raise ValueError("Snapshot BPS memerlukan minimal satu respons")
    return {
        "source_code": SOURCE_CODE,
        "source_url": requests[0].source_url.split("/domain/")[0],
        "retrieved_at": _isoformat_utc(retrieved_at),
        "variable_ids": sorted(extraction.data_requests),
        "record_count": sum(
            len(request.payload.get("datacontent", {}))
            for request in extraction.data_requests.values()
            if isinstance(request.payload.get("datacontent"), dict)
        ),
        "requests": [
            {
                "resource": request.resource,
                "source_url": request.source_url,
                "parameters": request.parameters,
                "response": request.payload,
            }
            for request in requests
        ],
    }


def save_bps_snapshot(
    extraction: BPSExtraction,
    retrieved_at: datetime,
    directory: Path = DEFAULT_BPS_RAW_DIRECTORY,
) -> Path:
    snapshot = build_bps_snapshot(extraction, retrieved_at)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = retrieved_at.strftime("%Y%m%dT%H%M%S%fZ")
    destination = directory / f"bps_{timestamp}.json"
    with destination.open("x", encoding="utf-8") as snapshot_file:
        json.dump(snapshot, snapshot_file, ensure_ascii=False, indent=2)
        snapshot_file.write("\n")
    return destination
