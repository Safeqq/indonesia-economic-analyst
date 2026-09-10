from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BANK_INDONESIA_CONFIG = PROJECT_ROOT / "config" / "bank_indonesia.yml"


@dataclass(frozen=True)
class BankIndonesiaSource:
    code: str
    name: str
    base_url: str
    default_start_date: date


@dataclass(frozen=True)
class BIRateDefinition:
    code: str
    name: str
    unit: str
    frequency: str
    page_url: str
    source_format: str
    sheet_names: tuple[str, ...]
    date_columns: tuple[str, ...]
    value_columns: tuple[str, ...]
    aggregation: str


@dataclass(frozen=True)
class JISDORDefinition:
    code: str
    name: str
    unit: str
    frequency: str
    endpoint_url: str
    information_url: str
    source_format: str
    currency: str
    fields: dict[str, str]
    aggregation: str


@dataclass(frozen=True)
class BankIndonesiaConfiguration:
    source: BankIndonesiaSource
    bi_rate: BIRateDefinition
    jisdor: JISDORDefinition


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Konfigurasi BI untuk {context} harus berupa mapping")
    return value


def _text(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Konfigurasi BI {context}.{key} wajib berupa teks")
    return value.strip()


def _text_list(mapping: dict[str, Any], key: str, context: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ValueError(f"Konfigurasi BI {context}.{key} wajib berupa daftar teks")
    normalized = tuple(item.strip() for item in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"Konfigurasi BI {context}.{key} memiliki nilai duplikat")
    return normalized


def _parse_date(value: Any, context: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Konfigurasi BI {context} wajib berupa tanggal ISO")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Konfigurasi BI {context} bukan tanggal ISO valid") from error


def load_bank_indonesia_configuration(
    path: Path = DEFAULT_BANK_INDONESIA_CONFIG,
) -> BankIndonesiaConfiguration:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"Konfigurasi BI tidak dapat dibaca: {path}") from error
    root = _mapping(payload, "root")
    source_payload = _mapping(root.get("source"), "source")
    indicators = _mapping(root.get("indicators"), "indicators")
    bi_rate_payload = _mapping(indicators.get("bi_rate"), "indicators.bi_rate")
    jisdor_payload = _mapping(indicators.get("jisdor"), "indicators.jisdor")

    columns = _mapping(bi_rate_payload.get("columns"), "indicators.bi_rate.columns")
    fields_payload = _mapping(jisdor_payload.get("fields"), "indicators.jisdor.fields")
    required_fields = {
        "record",
        "id",
        "link",
        "denomination",
        "value_buy",
        "value_sell",
        "date",
        "currency",
    }
    if set(fields_payload) != required_fields:
        missing = sorted(required_fields.difference(fields_payload))
        extra = sorted(set(fields_payload).difference(required_fields))
        raise ValueError(
            "Konfigurasi BI indicators.jisdor.fields tidak valid: "
            f"missing={missing}, extra={extra}"
        )
    fields = {
        key: _text(fields_payload, key, "indicators.jisdor.fields")
        for key in sorted(required_fields)
    }

    source = BankIndonesiaSource(
        code=_text(source_payload, "code", "source"),
        name=_text(source_payload, "name", "source"),
        base_url=_text(source_payload, "base_url", "source"),
        default_start_date=_parse_date(
            source_payload.get("default_start_date"), "source.default_start_date"
        ),
    )
    bi_rate = BIRateDefinition(
        code=_text(bi_rate_payload, "code", "indicators.bi_rate"),
        name=_text(bi_rate_payload, "name", "indicators.bi_rate"),
        unit=_text(bi_rate_payload, "unit", "indicators.bi_rate"),
        frequency=_text(bi_rate_payload, "frequency", "indicators.bi_rate"),
        page_url=_text(bi_rate_payload, "page_url", "indicators.bi_rate"),
        source_format=_text(bi_rate_payload, "format", "indicators.bi_rate"),
        sheet_names=_text_list(bi_rate_payload, "sheet_names", "indicators.bi_rate"),
        date_columns=_text_list(columns, "date", "indicators.bi_rate.columns"),
        value_columns=_text_list(columns, "value", "indicators.bi_rate.columns"),
        aggregation=_text(bi_rate_payload, "aggregation", "indicators.bi_rate"),
    )
    jisdor = JISDORDefinition(
        code=_text(jisdor_payload, "code", "indicators.jisdor"),
        name=_text(jisdor_payload, "name", "indicators.jisdor"),
        unit=_text(jisdor_payload, "unit", "indicators.jisdor"),
        frequency=_text(jisdor_payload, "frequency", "indicators.jisdor"),
        endpoint_url=_text(jisdor_payload, "endpoint_url", "indicators.jisdor"),
        information_url=_text(jisdor_payload, "information_url", "indicators.jisdor"),
        source_format=_text(jisdor_payload, "format", "indicators.jisdor"),
        currency=_text(jisdor_payload, "currency", "indicators.jisdor"),
        fields=fields,
        aggregation=_text(jisdor_payload, "aggregation", "indicators.jisdor"),
    )

    if source.code != "bank_indonesia":
        raise ValueError("Konfigurasi BI source.code harus bank_indonesia")
    codes = {bi_rate.code, jisdor.code}
    if len(codes) != 2:
        raise ValueError("Kode indikator BI harus unik")
    for label, definition in (("bi_rate", bi_rate), ("jisdor", jisdor)):
        if definition.frequency != "monthly":
            raise ValueError(f"Frekuensi indikator BI {label} harus monthly")
    if bi_rate.source_format != "xlsx" or jisdor.source_format != "xml":
        raise ValueError(
            "Format sumber BI harus xlsx untuk BI-Rate dan xml untuk JISDOR"
        )

    return BankIndonesiaConfiguration(
        source=source,
        bi_rate=bi_rate,
        jisdor=jisdor,
    )
