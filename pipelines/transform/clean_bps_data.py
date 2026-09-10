from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from pipelines.extract.extract_bps import BPSExtraction, parse_paginated_response
from pipelines.transform.clean_economic_data import STANDARD_COLUMNS
from pipelines.utils.bps_config import (
    BPSConfiguration,
    BPSIndicatorDefinition,
    BPSProvinceConfiguration,
)

METADATA_COLUMNS = [
    "indicator_code",
    "source_code",
    "source_variable_id",
    "derived_variable_id",
    "derived_period_id",
    "indicator_name",
    "unit",
    "definition_text",
    "notes",
    "metadata_hash",
    "period_start",
    "period_end",
    "observed_at",
]
MISSING_VALUES = {"", "-", "–", "—", "...", "na", "n/a", "null"}
YEAR_PATTERN = re.compile(r"(?<!\d)(\d{4})(?!\d)")


@dataclass(frozen=True)
class BPSCleanResult:
    frame: pd.DataFrame
    metadata: pd.DataFrame
    provinces: dict[str, str]


def _identifier(value: object, field: str) -> str:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"ID {field} pada respons BPS tidak valid")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"ID {field} pada respons BPS tidak bulat")
        value = int(value)
    identifier = str(value).strip()
    if not identifier:
        raise ValueError(f"ID {field} pada respons BPS kosong")
    return identifier


def _items(payload: dict[str, Any], field: str) -> list[dict[str, Any]]:
    items = payload.get(field)
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise ValueError(f"Field {field} pada respons data BPS tidak valid")
    return items


def _dimension_items(
    payload: dict[str, Any], field: str, default_label: str
) -> list[dict[str, Any]]:
    items = _items(payload, field)
    return items or [{"val": 0, "label": default_label}]


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _numeric_value(value: object, key: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Nilai BPS pada datacontent {key} bukan numerik")
    if isinstance(value, (int, float)):
        numeric = float(value)
    else:
        normalized = str(value).strip()
        if normalized.casefold() in MISSING_VALUES:
            return None
        if "," in normalized:
            raise ValueError(
                f"Nilai BPS pada datacontent {key} memakai format angka ambigu"
            )
        try:
            numeric = float(normalized)
        except ValueError as error:
            raise ValueError(
                f"Nilai BPS pada datacontent {key} bukan numerik"
            ) from error
    if not pd.notna(numeric) or numeric in (float("inf"), float("-inf")):
        raise ValueError(f"Nilai BPS pada datacontent {key} tidak finite")
    return numeric


def _year(value: object) -> int:
    match = YEAR_PATTERN.search(_text(value))
    if not match:
        raise ValueError(f"Label tahun BPS tidak valid: {value!r}")
    year = int(match.group(1))
    if not 1900 <= year <= 9999:
        raise ValueError(f"Tahun BPS di luar rentang: {year}")
    return year


def _series_code(
    definition: BPSIndicatorDefinition,
    derived_variable_id: str,
    derived_period_id: str,
) -> str:
    return f"{definition.code_prefix}.TV{derived_variable_id}.TP{derived_period_id}"


def _series_name(
    variable_label: str, derived_variable_label: str, derived_period_label: str
) -> str:
    parts = [variable_label]
    if derived_variable_label and derived_variable_label.casefold() not in {
        variable_label.casefold(),
        "-",
    }:
        parts.append(derived_variable_label)
    if derived_period_label.casefold() not in {"", "tahun", "tahunan", "annual"}:
        parts.append(f"Periode {derived_period_label}")
    return " — ".join(parts)


def reconcile_provinces(
    extraction: BPSExtraction,
    configured: BPSProvinceConfiguration,
) -> dict[str, str]:
    _, rows = parse_paginated_response(
        extraction.province_request.payload, "daftar domain provinsi"
    )
    official: dict[str, str] = {}
    for position, item in enumerate(rows, start=1):
        try:
            code = _identifier(item["domain_id"], "domain_id")
            name = _text(item["domain_name"])
        except KeyError as error:
            raise ValueError(
                f"Domain provinsi BPS ke-{position} tidak lengkap"
            ) from error
        if len(code) != 4 or not code.isdigit() or not name:
            raise ValueError(f"Domain provinsi BPS ke-{position} tidak valid")
        if code in official:
            raise ValueError(f"Kode domain provinsi BPS duplikat: {code}")
        official[code] = name

    configured_codes = set(configured.provinces)
    official_codes = set(official)
    if configured_codes != official_codes:
        missing = sorted(official_codes - configured_codes)
        retired = sorted(configured_codes - official_codes)
        raise ValueError(
            "Mapping provinsi tidak sama dengan domain resmi BPS; "
            f"belum dipetakan={missing}, tidak lagi tersedia={retired}"
        )
    return official


def _period_ids(extraction: BPSExtraction, variable_id: int) -> set[str]:
    identifiers: set[str] = set()
    requests = extraction.period_requests.get(variable_id)
    if not requests:
        raise ValueError(f"Inventaris periode variabel BPS {variable_id} kosong")
    for request in requests:
        _, rows = parse_paginated_response(
            request.payload, f"periode variabel {variable_id}"
        )
        for item in rows:
            if "th_id" not in item:
                raise ValueError(
                    f"Inventaris periode variabel BPS {variable_id} tanpa th_id"
                )
            identifiers.add(_identifier(item["th_id"], "th_id"))
    if not identifiers:
        raise ValueError(f"Inventaris periode variabel BPS {variable_id} kosong")
    return identifiers


def _metadata_hash(payload: dict[str, str]) -> str:
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _clean_variable(
    payload: dict[str, Any],
    definition: BPSIndicatorDefinition,
    official_provinces: dict[str, str],
    parent_region_code: str,
    period_ids: set[str],
    configuration: BPSConfiguration,
    retrieved_at: datetime,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    variable_items = _items(payload, "var")
    matching_variables = [
        item
        for item in variable_items
        if _identifier(item.get("val"), "var") == str(definition.variable_id)
    ]
    if len(matching_variables) != 1:
        raise ValueError(
            f"Metadata variabel BPS {definition.variable_id} tidak unik/tersedia"
        )
    variable = matching_variables[0]
    variable_label = _text(variable.get("label"))
    unit = _text(variable.get("unit"))
    if not variable_label or not unit:
        raise ValueError(f"Nama atau unit variabel BPS {definition.variable_id} kosong")
    if "provinsi" not in _text(payload.get("labelvervar")).casefold():
        raise ValueError(
            f"Variabel BPS {definition.variable_id} tidak berdimensi provinsi"
        )
    if definition.frequency != "annual":
        raise ValueError(
            f"Frequency {definition.frequency} untuk variabel BPS "
            f"{definition.variable_id} belum didukung transform ini"
        )

    derived_variables = _dimension_items(payload, "turvar", "")
    regions = _items(payload, "vervar")
    years = _items(payload, "tahun")
    derived_periods = _dimension_items(payload, "turtahun", "Tahun")
    content = payload.get("datacontent")
    if not isinstance(content, dict):
        raise ValueError(
            f"datacontent variabel BPS {definition.variable_id} tidak valid"
        )

    rows: list[dict[str, object]] = []
    series_metadata: dict[str, dict[str, object]] = {}
    consumed_keys: set[str] = set()
    variable_code = str(definition.variable_id)
    for region in regions:
        region_code = _identifier(region.get("val"), "vervar")
        for derived_variable in derived_variables:
            derived_variable_id = _identifier(derived_variable.get("val"), "turvar")
            derived_variable_label = _text(derived_variable.get("label"))
            for year_item in years:
                year_id = _identifier(year_item.get("val"), "tahun")
                if year_id not in period_ids:
                    raise ValueError(
                        f"Periode {year_id} variabel BPS {definition.variable_id} "
                        "tidak ada dalam inventaris resmi"
                    )
                observation_year = _year(year_item.get("label"))
                for derived_period in derived_periods:
                    derived_period_id = _identifier(
                        derived_period.get("val"), "turtahun"
                    )
                    derived_period_label = _text(derived_period.get("label"))
                    key = (
                        f"{region_code}{variable_code}{derived_variable_id}"
                        f"{year_id}{derived_period_id}"
                    )
                    if key not in content:
                        continue
                    consumed_keys.add(key)
                    numeric = _numeric_value(content[key], key)
                    if numeric is None or region_code == "9999":
                        continue
                    if region_code not in official_provinces:
                        raise ValueError(
                            f"Kode wilayah BPS {region_code} belum dipetakan"
                        )
                    indicator_code = _series_code(
                        definition, derived_variable_id, derived_period_id
                    )
                    indicator_name = _series_name(
                        variable_label,
                        derived_variable_label,
                        derived_period_label,
                    )
                    observation_date = f"{observation_year:04d}-01-01"
                    rows.append(
                        {
                            "indicator_code": indicator_code,
                            "indicator_name": indicator_name,
                            "unit": unit,
                            "frequency": definition.frequency,
                            "region_code": region_code,
                            "region_name": official_provinces[region_code],
                            "region_level": "province",
                            "parent_region_code": parent_region_code,
                            "observation_date": observation_date,
                            "value": numeric,
                            "source_code": configuration.source.code,
                            "source_name": configuration.source.name,
                            "source_url": configuration.source.base_url,
                            "retrieved_at": retrieved_at,
                            "source_variable_id": variable_code,
                            "derived_variable_id": derived_variable_id,
                            "derived_period_id": derived_period_id,
                        }
                    )
                    metadata_payload = {
                        "indicator_name": indicator_name,
                        "unit": unit,
                        "definition_text": _text(variable.get("def")),
                        "notes": _text(variable.get("note")),
                        "source_variable_id": variable_code,
                        "derived_variable_id": derived_variable_id,
                        "derived_period_id": derived_period_id,
                    }
                    series_metadata[indicator_code] = {
                        **metadata_payload,
                        "indicator_code": indicator_code,
                        "source_code": configuration.source.code,
                        "metadata_hash": _metadata_hash(metadata_payload),
                        "observed_at": retrieved_at,
                    }

    unrecognized = sorted(set(map(str, content)) - consumed_keys)
    if unrecognized:
        preview = unrecognized[:3]
        raise ValueError(
            f"Schema datacontent variabel BPS {definition.variable_id} berubah; "
            f"key tidak dikenali: {preview}"
        )
    if not rows:
        raise ValueError(
            f"Variabel BPS {definition.variable_id} tidak memiliki observasi provinsi"
        )

    metadata_rows: list[dict[str, object]] = []
    for indicator_code, item in series_metadata.items():
        dates = [
            str(row["observation_date"])
            for row in rows
            if row["indicator_code"] == indicator_code
        ]
        metadata_rows.append(
            {
                **item,
                "period_start": min(dates),
                "period_end": max(dates),
            }
        )
    return rows, metadata_rows


def clean_bps(
    extraction: BPSExtraction,
    configuration: BPSConfiguration,
    province_configuration: BPSProvinceConfiguration,
    retrieved_at: datetime,
) -> BPSCleanResult:
    official_provinces = reconcile_provinces(extraction, province_configuration)
    rows: list[dict[str, object]] = []
    metadata_rows: list[dict[str, object]] = []
    for variable_id, definition in configuration.indicators.items():
        request = extraction.data_requests.get(variable_id)
        if request is None:
            raise ValueError(f"Respons variabel BPS {variable_id} tidak tersedia")
        variable_rows, variable_metadata = _clean_variable(
            request.payload,
            definition,
            official_provinces,
            province_configuration.parent_region_code,
            _period_ids(extraction, variable_id),
            configuration,
            retrieved_at,
        )
        rows.extend(variable_rows)
        metadata_rows.extend(variable_metadata)

    frame_columns = STANDARD_COLUMNS + [
        "parent_region_code",
        "source_variable_id",
        "derived_variable_id",
        "derived_period_id",
    ]
    frame = pd.DataFrame(rows, columns=frame_columns)
    metadata = pd.DataFrame(metadata_rows, columns=METADATA_COLUMNS)
    if not frame.empty:
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"], format="%Y-%m-%d", errors="raise"
        )
        frame["retrieved_at"] = pd.to_datetime(
            frame["retrieved_at"], utc=True, errors="raise"
        )
        frame["value"] = pd.to_numeric(frame["value"], errors="raise")
        frame = frame.sort_values(
            ["indicator_code", "region_code", "observation_date"],
            ignore_index=True,
        )
    if not metadata.empty:
        metadata["period_start"] = pd.to_datetime(
            metadata["period_start"], format="%Y-%m-%d", errors="raise"
        )
        metadata["period_end"] = pd.to_datetime(
            metadata["period_end"], format="%Y-%m-%d", errors="raise"
        )
        metadata["observed_at"] = pd.to_datetime(
            metadata["observed_at"], utc=True, errors="raise"
        )
    return BPSCleanResult(
        frame=frame,
        metadata=metadata,
        provinces=official_provinces,
    )


def validate_bps_coverage(
    frame: pd.DataFrame,
    configuration: BPSConfiguration,
    provinces: dict[str, str],
) -> dict[int, str]:
    supported = set(provinces)
    completed: dict[int, str] = {}
    for variable_id, definition in configuration.indicators.items():
        candidates = frame[frame["source_variable_id"].eq(str(variable_id))]
        for (indicator_code, observation_date), group in candidates.groupby(
            ["indicator_code", "observation_date"]
        ):
            if set(group["region_code"]) == supported:
                completed[variable_id] = (
                    f"{indicator_code}@{pd.Timestamp(observation_date).date()}"
                )
                break
        if variable_id not in completed:
            raise ValueError(
                f"Variabel BPS {definition.name} ({variable_id}) tidak memiliki "
                f"satu periode lengkap untuk {len(supported)} provinsi"
            )
    required_count = min(2, len(configuration.indicators))
    if len(completed) < required_count:
        raise ValueError("Cakupan BPS belum memiliki dua indikator regional")
    return completed


def validate_bps_metadata(metadata: pd.DataFrame, frame: pd.DataFrame) -> None:
    missing = set(METADATA_COLUMNS).difference(metadata.columns)
    if missing:
        raise ValueError(f"Kolom metadata BPS tidak tersedia: {sorted(missing)}")
    if metadata.empty:
        raise ValueError("Riwayat metadata BPS kosong")
    if metadata[METADATA_COLUMNS].isnull().any().any():
        raise ValueError("Riwayat metadata BPS memiliki nilai null")
    if metadata["indicator_code"].duplicated().any():
        raise ValueError("Riwayat metadata BPS duplikat dalam satu snapshot")
    if not metadata["metadata_hash"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all():
        raise ValueError("Hash metadata BPS tidak valid")
    if (metadata["period_start"] > metadata["period_end"]).any():
        raise ValueError("Rentang periode metadata BPS tidak valid")
    if set(metadata["indicator_code"]) != set(frame["indicator_code"]):
        raise ValueError("Metadata BPS tidak mencakup seluruh seri hasil transform")


def validate_bps_value_ranges(frame: pd.DataFrame) -> None:
    values = pd.to_numeric(frame["value"], errors="coerce")
    tpt = frame["source_variable_id"].eq("543")
    population = frame["source_variable_id"].eq("1975")
    if (tpt & ~values.between(0, 100)).any():
        raise ValueError("Tingkat pengangguran terbuka BPS harus 0 sampai 100")
    if (population & values.le(0)).any():
        raise ValueError("Jumlah penduduk BPS harus lebih besar dari nol")
