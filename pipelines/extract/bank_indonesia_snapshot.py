from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pipelines.extract.extract_bank_indonesia import (
    SOURCE_CODE,
    BankIndonesiaExtraction,
    BankIndonesiaResource,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BANK_INDONESIA_RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw" / SOURCE_CODE


@dataclass(frozen=True)
class BankIndonesiaSnapshot:
    manifest_path: Path
    bi_rate_path: Path
    jisdor_path: Path


def _isoformat_utc(timestamp: datetime) -> str:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Waktu snapshot BI harus memiliki timezone")
    return (
        timestamp.astimezone(UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _resource_manifest(
    resource: BankIndonesiaResource, filename: str
) -> dict[str, object]:
    return {
        "name": resource.name,
        "source_url": resource.source_url,
        "request_method": resource.request_method,
        "parameters": resource.parameters,
        "content_type": resource.content_type,
        "content_disposition": resource.content_disposition,
        "filename": filename,
        "byte_count": len(resource.payload),
        "sha256": hashlib.sha256(resource.payload).hexdigest(),
    }


def save_bank_indonesia_snapshot(
    extraction: BankIndonesiaExtraction,
    retrieved_at: datetime,
    directory: Path = DEFAULT_BANK_INDONESIA_RAW_DIRECTORY,
) -> BankIndonesiaSnapshot:
    if not extraction.bi_rate.payload or not extraction.jisdor.payload:
        raise ValueError("Snapshot BI tidak dapat menyimpan respons kosong")
    timestamp = retrieved_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    bi_rate_name = f"bank_indonesia_bi_rate_{timestamp}.xlsx"
    jisdor_name = f"bank_indonesia_jisdor_{timestamp}.xml"
    manifest_name = f"bank_indonesia_{timestamp}.json"
    directory.mkdir(parents=True, exist_ok=True)
    bi_rate_path = directory / bi_rate_name
    jisdor_path = directory / jisdor_name
    manifest_path = directory / manifest_name

    with bi_rate_path.open("xb") as output:
        output.write(extraction.bi_rate.payload)
    with jisdor_path.open("xb") as output:
        output.write(extraction.jisdor.payload)
    manifest = {
        "source_code": SOURCE_CODE,
        "retrieved_at": _isoformat_utc(retrieved_at),
        "resources": [
            _resource_manifest(extraction.bi_rate, bi_rate_name),
            _resource_manifest(extraction.jisdor, jisdor_name),
        ],
    }
    with manifest_path.open("x", encoding="utf-8") as output:
        json.dump(manifest, output, ensure_ascii=False, indent=2)
        output.write("\n")
    return BankIndonesiaSnapshot(
        manifest_path=manifest_path,
        bi_rate_path=bi_rate_path,
        jisdor_path=jisdor_path,
    )
