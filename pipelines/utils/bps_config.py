from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BPS_CONFIG = PROJECT_ROOT / "config" / "bps.yml"
DEFAULT_PROVINCE_CONFIG = PROJECT_ROOT / "config" / "bps_provinces.yml"
ALLOWED_FREQUENCIES = {"annual"}


@dataclass(frozen=True)
class BPSSourceDefinition:
    code: str
    name: str
    base_url: str
    domain: str
    language: str


@dataclass(frozen=True)
class BPSIndicatorDefinition:
    variable_id: int
    code_prefix: str
    name: str
    frequency: str


@dataclass(frozen=True)
class BPSConfiguration:
    source: BPSSourceDefinition
    indicators: dict[int, BPSIndicatorDefinition]


@dataclass(frozen=True)
class BPSProvinceConfiguration:
    parent_region_code: str
    provinces: dict[str, str]


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as config_file:
        payload = yaml.safe_load(config_file)
    if not isinstance(payload, dict):
        raise ValueError(f"Konfigurasi YAML tidak valid: {path}")
    return payload


def load_bps_configuration(path: Path = DEFAULT_BPS_CONFIG) -> BPSConfiguration:
    payload = _load_yaml(path)
    source_payload = payload.get("source")
    indicator_payload = payload.get("indicators")
    if not isinstance(source_payload, dict) or not isinstance(indicator_payload, list):
        raise ValueError(f"Konfigurasi BPS tidak lengkap: {path}")

    required_source = {"code", "name", "base_url", "domain", "language"}
    missing_source = required_source.difference(source_payload)
    if missing_source:
        raise ValueError(f"Konfigurasi sumber BPS kurang: {sorted(missing_source)}")
    source = BPSSourceDefinition(
        code=str(source_payload["code"]).strip(),
        name=str(source_payload["name"]).strip(),
        base_url=str(source_payload["base_url"]).rstrip("/"),
        domain=str(source_payload["domain"]).strip(),
        language=str(source_payload["language"]).strip(),
    )
    if not all((source.code, source.name, source.base_url, source.domain)):
        raise ValueError("Field sumber BPS tidak boleh kosong")

    definitions: dict[int, BPSIndicatorDefinition] = {}
    required_indicator = {"variable_id", "code_prefix", "name", "frequency"}
    for position, item in enumerate(indicator_payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Indikator BPS ke-{position} harus berupa mapping")
        missing = required_indicator.difference(item)
        if missing:
            raise ValueError(
                f"Indikator BPS ke-{position} tidak memiliki field: {sorted(missing)}"
            )
        try:
            variable_id = int(item["variable_id"])
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"variable_id indikator BPS ke-{position} tidak valid"
            ) from error
        definition = BPSIndicatorDefinition(
            variable_id=variable_id,
            code_prefix=str(item["code_prefix"]).strip(),
            name=str(item["name"]).strip(),
            frequency=str(item["frequency"]).strip(),
        )
        if variable_id <= 0 or not definition.code_prefix or not definition.name:
            raise ValueError(f"Indikator BPS ke-{position} memiliki nilai kosong")
        if definition.frequency not in ALLOWED_FREQUENCIES:
            raise ValueError(
                f"Frequency indikator BPS {variable_id} tidak didukung: "
                f"{definition.frequency}"
            )
        if variable_id in definitions:
            raise ValueError(f"variable_id BPS duplikat: {variable_id}")
        definitions[variable_id] = definition
    if len(definitions) < 2:
        raise ValueError("Pipeline BPS memerlukan minimal dua variabel")
    return BPSConfiguration(source=source, indicators=definitions)


def load_bps_provinces(
    path: Path = DEFAULT_PROVINCE_CONFIG,
) -> BPSProvinceConfiguration:
    payload = _load_yaml(path)
    metadata = payload.get("metadata")
    province_payload = payload.get("provinces")
    if not isinstance(metadata, dict) or not isinstance(province_payload, list):
        raise ValueError(f"Konfigurasi provinsi BPS tidak lengkap: {path}")
    parent_region_code = str(metadata.get("parent_region_code", "")).strip()
    if not parent_region_code:
        raise ValueError("parent_region_code BPS tidak boleh kosong")

    provinces: dict[str, str] = {}
    for position, item in enumerate(province_payload, start=1):
        if not isinstance(item, dict) or not {"code", "name"}.issubset(item):
            raise ValueError(f"Provinsi BPS ke-{position} tidak valid")
        code = str(item["code"]).strip()
        name = str(item["name"]).strip()
        if len(code) != 4 or not code.isdigit() or not name:
            raise ValueError(f"Kode/nama provinsi BPS ke-{position} tidak valid")
        if code in provinces:
            raise ValueError(f"Kode provinsi BPS duplikat: {code}")
        provinces[code] = name
    if not provinces:
        raise ValueError("Mapping provinsi BPS kosong")
    return BPSProvinceConfiguration(
        parent_region_code=parent_region_code,
        provinces=provinces,
    )
