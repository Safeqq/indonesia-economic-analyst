from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pipelines.utils.api_client import get_json

BASE_URL = "https://api.worldbank.org/v2"
SOURCE_CODE = "world_bank"
SOURCE_NAME = "World Bank Open Data"
COUNTRY_PATTERN = re.compile(r"^[A-Za-z0-9]{2,3}$")
INDICATOR_PATTERN = re.compile(r"^[A-Za-z0-9.]+$")


@dataclass(frozen=True)
class WorldBankExtraction:
    country: str
    indicator: str
    source_url: str
    parameters: dict[str, str | int]
    payload: list[Any]
    records: list[dict[str, Any]]


def validate_year_range(start_year: int, end_year: int) -> None:
    if not 1 <= start_year <= 9999 or not 1 <= end_year <= 9999:
        raise ValueError("Tahun harus berada pada rentang 1 sampai 9999")
    if start_year > end_year:
        raise ValueError("Tahun awal tidak boleh lebih besar dari tahun akhir")


def _validate_code(value: str, pattern: re.Pattern[str], label: str) -> str:
    normalized = value.strip()
    if not normalized or not pattern.fullmatch(normalized):
        raise ValueError(f"{label} tidak valid: {value!r}")
    return normalized


def _validate_payload(payload: Any) -> tuple[list[Any], list[dict[str, Any]]]:
    if not isinstance(payload, list) or len(payload) != 2:
        raise ValueError(
            "World Bank mengembalikan respons tidak valid; format [metadata, records] "
            "tidak ditemukan"
        )
    metadata, records = payload
    if not isinstance(metadata, dict) or not isinstance(records, list):
        raise ValueError(
            "World Bank mengembalikan respons tidak valid; metadata atau records "
            "memiliki tipe yang salah"
        )
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("World Bank mengembalikan record dengan tipe yang salah")
    return payload, records


def extract_indicator(
    country: str,
    indicator: str,
    start_year: int,
    end_year: int,
) -> WorldBankExtraction:
    validate_year_range(start_year, end_year)
    country = _validate_code(country, COUNTRY_PATTERN, "Kode negara")
    indicator = _validate_code(indicator, INDICATOR_PATTERN, "Kode indikator")
    source_url = f"{BASE_URL}/country/{country}/indicator/{indicator}"
    parameters: dict[str, str | int] = {
        "format": "json",
        "per_page": 20000,
        "date": f"{start_year}:{end_year}",
    }
    payload, records = _validate_payload(get_json(source_url, parameters))
    return WorldBankExtraction(
        country=country,
        indicator=indicator,
        source_url=source_url,
        parameters=parameters,
        payload=payload,
        records=records,
    )
