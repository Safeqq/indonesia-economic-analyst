from __future__ import annotations

import calendar
import posixpath
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from zipfile import BadZipFile, ZipFile

import pandas as pd

from pipelines.extract.extract_bank_indonesia import BankIndonesiaExtraction
from pipelines.transform.clean_economic_data import STANDARD_COLUMNS
from pipelines.utils.bank_indonesia_config import (
    BankIndonesiaConfiguration,
    BIRateDefinition,
    JISDORDefinition,
)

SPREADSHEET_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
CELL_REFERENCE_PATTERN = re.compile(r"^([A-Z]+)[1-9][0-9]*$")
INDONESIAN_DATE_PATTERN = re.compile(
    r"^(?P<day>[0-9]{1,2})\s+(?P<month>[A-Za-z]+)\s+(?P<year>[0-9]{4})$"
)
RATE_PATTERN = re.compile(r"^(?P<value>[0-9]+(?:[.,][0-9]+)?)\s*%$")
INDONESIAN_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}


class BankIndonesiaSchemaDriftError(ValueError):
    """Format resmi BI tidak lagi cocok dengan schema yang dikonfigurasi."""


@dataclass(frozen=True)
class BIRateRecord:
    effective_date: date
    value: Decimal


@dataclass(frozen=True)
class JISDORRecord:
    observation_date: date
    value: Decimal


@dataclass(frozen=True)
class CleanBankIndonesiaResult:
    frame: pd.DataFrame
    bi_rate_event_count: int
    jisdor_daily_count: int
    month_count: int


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _normalized_label(value: object) -> str:
    return " ".join(
        str(value).replace("\u200b", "").replace("\xa0", " ").split()
    ).casefold()


def _xlsx_path(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join("xl", target))


def _shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    except ET.ParseError as error:
        raise BankIndonesiaSchemaDriftError(
            "Schema drift BI-Rate: sharedStrings.xml tidak valid"
        ) from error
    return [
        "".join(
            element.text or ""
            for element in item.iter()
            if _local_name(element.tag) == "t"
        )
        for item in root
        if _local_name(item.tag) == "si"
    ]


def _worksheet_path(archive: ZipFile, sheet_names: tuple[str, ...]) -> str:
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ET.ParseError) as error:
        raise BankIndonesiaSchemaDriftError(
            "Schema drift BI-Rate: metadata workbook XLSX tidak lengkap"
        ) from error

    accepted = {_normalized_label(item) for item in sheet_names}
    available: list[str] = []
    relationship_id: str | None = None
    for sheet in workbook.iter(f"{{{SPREADSHEET_NAMESPACE}}}sheet"):
        name = sheet.attrib.get("name", "")
        available.append(name)
        if _normalized_label(name) in accepted:
            relationship_id = sheet.attrib.get(f"{{{OFFICE_RELATIONSHIP_NAMESPACE}}}id")
            break
    if relationship_id is None:
        raise BankIndonesiaSchemaDriftError(
            "Schema drift BI-Rate: sheet yang diterima tidak ditemukan; "
            f"sheet={available}, expected={list(sheet_names)}"
        )

    for relationship in relationships.iter(
        f"{{{PACKAGE_RELATIONSHIP_NAMESPACE}}}Relationship"
    ):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib.get("Target")
            if target:
                return _xlsx_path(target)
    raise BankIndonesiaSchemaDriftError(
        "Schema drift BI-Rate: relasi worksheet tidak ditemukan"
    )


def _column_number(reference: str) -> int:
    match = CELL_REFERENCE_PATTERN.fullmatch(reference)
    if not match:
        raise BankIndonesiaSchemaDriftError(
            f"Schema drift BI-Rate: referensi cell tidak valid {reference!r}"
        )
    result = 0
    for character in match.group(1):
        result = result * 26 + ord(character) - ord("A") + 1
    return result


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(
            item.text or "" for item in cell.iter() if _local_name(item.tag) == "t"
        )
    value_element = next((item for item in cell if _local_name(item.tag) == "v"), None)
    if value_element is None or value_element.text is None:
        return ""
    value = value_element.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (IndexError, ValueError) as error:
            raise BankIndonesiaSchemaDriftError(
                "Schema drift BI-Rate: indeks shared string tidak valid"
            ) from error
    return value


def _worksheet_rows(archive: ZipFile, worksheet_path: str) -> list[dict[int, str]]:
    try:
        worksheet = ET.fromstring(archive.read(worksheet_path))
    except (KeyError, ET.ParseError) as error:
        raise BankIndonesiaSchemaDriftError(
            "Schema drift BI-Rate: worksheet XLSX tidak dapat dibaca"
        ) from error
    shared_strings = _shared_strings(archive)
    rows: list[dict[int, str]] = []
    for row in worksheet.iter(f"{{{SPREADSHEET_NAMESPACE}}}row"):
        values: dict[int, str] = {}
        for cell in row.findall(f"{{{SPREADSHEET_NAMESPACE}}}c"):
            reference = cell.attrib.get("r", "")
            values[_column_number(reference)] = _cell_text(cell, shared_strings)
        rows.append(values)
    return rows


def _find_bi_rate_columns(
    rows: list[dict[int, str]], definition: BIRateDefinition
) -> tuple[int, int, int]:
    accepted_dates = {_normalized_label(item) for item in definition.date_columns}
    accepted_values = {_normalized_label(item) for item in definition.value_columns}
    observed: list[list[str]] = []
    for position, row in enumerate(rows):
        normalized = {column: _normalized_label(value) for column, value in row.items()}
        date_columns = [
            column for column, value in normalized.items() if value in accepted_dates
        ]
        value_columns = [
            column for column, value in normalized.items() if value in accepted_values
        ]
        nonempty = [value for value in row.values() if str(value).strip()]
        if len(nonempty) >= 2:
            observed.append(nonempty)
        if len(date_columns) == 1 and len(value_columns) == 1:
            return position, date_columns[0], value_columns[0]
    raise BankIndonesiaSchemaDriftError(
        "Schema drift BI-Rate: kolom tanggal/nilai tidak ditemukan; "
        f"header_terbaca={observed[:5]}"
    )


def _parse_indonesian_date(value: str, position: int) -> date:
    normalized = " ".join(value.replace("\u200b", "").split())
    match = INDONESIAN_DATE_PATTERN.fullmatch(normalized)
    if not match:
        raise BankIndonesiaSchemaDriftError(
            f"Format tanggal BI-Rate berubah pada baris {position}: {value!r}"
        )
    month_name = match.group("month").casefold()
    month = INDONESIAN_MONTHS.get(month_name)
    if month is None:
        raise BankIndonesiaSchemaDriftError(
            f"Nama bulan BI-Rate tidak dikenal pada baris {position}: {value!r}"
        )
    try:
        return date(int(match.group("year")), month, int(match.group("day")))
    except ValueError as error:
        raise BankIndonesiaSchemaDriftError(
            f"Tanggal BI-Rate tidak valid pada baris {position}: {value!r}"
        ) from error


def _parse_rate(value: str, position: int) -> Decimal:
    match = RATE_PATTERN.fullmatch(value.strip())
    if not match:
        raise BankIndonesiaSchemaDriftError(
            f"Format nilai BI-Rate berubah pada baris {position}: {value!r}"
        )
    try:
        result = Decimal(match.group("value").replace(",", "."))
    except InvalidOperation as error:
        raise BankIndonesiaSchemaDriftError(
            f"Nilai BI-Rate tidak valid pada baris {position}: {value!r}"
        ) from error
    if not result.is_finite():
        raise BankIndonesiaSchemaDriftError(
            f"Nilai BI-Rate tidak finite pada baris {position}"
        )
    return result


def parse_bi_rate_xlsx(
    payload: bytes, definition: BIRateDefinition
) -> tuple[BIRateRecord, ...]:
    try:
        with ZipFile(BytesIO(payload)) as archive:
            worksheet_path = _worksheet_path(archive, definition.sheet_names)
            rows = _worksheet_rows(archive, worksheet_path)
    except BadZipFile as error:
        raise BankIndonesiaSchemaDriftError(
            "Format BI-Rate berubah: respons bukan workbook XLSX valid"
        ) from error

    header_position, date_column, value_column = _find_bi_rate_columns(rows, definition)
    records: list[BIRateRecord] = []
    for worksheet_position, row in enumerate(
        rows[header_position + 1 :], start=header_position + 2
    ):
        raw_date = row.get(date_column, "").strip()
        raw_value = row.get(value_column, "").strip()
        if not raw_date and not raw_value:
            continue
        if not raw_date or not raw_value:
            raise BankIndonesiaSchemaDriftError(
                "Schema drift BI-Rate: tanggal atau nilai kosong pada baris "
                f"{worksheet_position}"
            )
        records.append(
            BIRateRecord(
                effective_date=_parse_indonesian_date(raw_date, worksheet_position),
                value=_parse_rate(raw_value, worksheet_position),
            )
        )
    if not records:
        raise ValueError("Workbook BI-Rate tidak memiliki observasi")
    dates = [record.effective_date for record in records]
    if len(dates) != len(set(dates)):
        raise ValueError("Workbook BI-Rate memiliki tanggal keputusan duplikat")
    return tuple(sorted(records, key=lambda item: item.effective_date))


def _decimal(value: str | None, field: str, position: int) -> Decimal:
    try:
        result = Decimal(value or "")
    except InvalidOperation as error:
        raise BankIndonesiaSchemaDriftError(
            f"Nilai JISDOR {field} tidak valid pada record {position}: {value!r}"
        ) from error
    if not result.is_finite():
        raise BankIndonesiaSchemaDriftError(
            f"Nilai JISDOR {field} tidak finite pada record {position}"
        )
    return result


def _parse_jisdor_date(value: str | None, position: int) -> date:
    try:
        return datetime.fromisoformat(value or "").date()
    except ValueError as error:
        raise BankIndonesiaSchemaDriftError(
            f"Format tanggal JISDOR berubah pada record {position}: {value!r}"
        ) from error


def parse_jisdor_xml(
    payload: bytes,
    definition: JISDORDefinition,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[JISDORRecord, ...]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise BankIndonesiaSchemaDriftError(
            "Format JISDOR berubah: respons bukan XML valid"
        ) from error
    if _local_name(root.tag) != "DataSet":
        raise BankIndonesiaSchemaDriftError(
            "Schema drift JISDOR: root XML "
            f"{_local_name(root.tag)!r}, expected 'DataSet'"
        )

    record_name = definition.fields["record"]
    field_names = {
        key: value for key, value in definition.fields.items() if key != "record"
    }
    expected_fields = set(field_names.values())
    records: list[JISDORRecord] = []
    for position, element in enumerate(
        (item for item in root.iter() if _local_name(item.tag) == record_name),
        start=1,
    ):
        raw = {_local_name(child.tag): child.text for child in element}
        actual_fields = set(raw)
        if actual_fields != expected_fields:
            raise BankIndonesiaSchemaDriftError(
                "Schema drift JISDOR pada record "
                f"{position}: missing={sorted(expected_fields - actual_fields)}, "
                f"extra={sorted(actual_fields - expected_fields)}"
            )
        currency = (raw[field_names["currency"]] or "").strip()
        if currency != definition.currency:
            raise ValueError(
                f"Mata uang JISDOR pada record {position} adalah {currency!r}, "
                f"expected {definition.currency!r}"
            )
        denomination = _decimal(
            raw[field_names["denomination"]], "denomination", position
        )
        if denomination != Decimal("1"):
            raise ValueError(
                f"Denominasi JISDOR pada record {position} bukan 1 {currency}"
            )
        value_buy = _decimal(raw[field_names["value_buy"]], "value_buy", position)
        value_sell = _decimal(raw[field_names["value_sell"]], "value_sell", position)
        if value_buy != value_sell:
            raise ValueError(f"Nilai beli/jual JISDOR berbeda pada record {position}")
        observation_date = _parse_jisdor_date(raw[field_names["date"]], position)
        if start_date is not None and observation_date < start_date:
            raise ValueError(
                f"JISDOR mengembalikan tanggal sebelum rentang: {observation_date}"
            )
        if end_date is not None and observation_date > end_date:
            raise ValueError(
                f"JISDOR mengembalikan tanggal setelah rentang: {observation_date}"
            )
        records.append(JISDORRecord(observation_date, value_buy))
    if not records:
        raise ValueError("Respons JISDOR tidak memiliki observasi")
    dates = [record.observation_date for record in records]
    if len(dates) != len(set(dates)):
        raise ValueError("Respons JISDOR memiliki tanggal observasi duplikat")
    return tuple(sorted(records, key=lambda item: item.observation_date))


def _month_end(value: date) -> date:
    return date(
        value.year, value.month, calendar.monthrange(value.year, value.month)[1]
    )


def validate_complete_month_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise ValueError("Tanggal awal BI tidak boleh melewati tanggal akhir")
    if start_date.day != 1:
        raise ValueError("Tanggal awal BI harus tanggal pertama bulan")
    if end_date != _month_end(end_date):
        raise ValueError("Tanggal akhir BI harus akhir bulan kalender yang lengkap")


def _month_starts(start_date: date, end_date: date) -> tuple[date, ...]:
    values: list[date] = []
    year, month = start_date.year, start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        values.append(date(year, month, 1))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return tuple(values)


def _monthly_bi_rate(
    records: tuple[BIRateRecord, ...], months: tuple[date, ...]
) -> dict[date, Decimal]:
    monthly: dict[date, Decimal] = {}
    index = 0
    active: BIRateRecord | None = None
    for month in months:
        end = _month_end(month)
        while index < len(records) and records[index].effective_date <= end:
            active = records[index]
            index += 1
        if active is None:
            raise ValueError(
                f"BI-Rate tidak memiliki keputusan yang berlaku untuk {month:%Y-%m}"
            )
        monthly[month] = active.value
    return monthly


def _monthly_jisdor(
    records: tuple[JISDORRecord, ...], months: tuple[date, ...]
) -> dict[date, Decimal]:
    grouped: dict[date, list[Decimal]] = defaultdict(list)
    expected = set(months)
    for record in records:
        month = record.observation_date.replace(day=1)
        if month in expected:
            grouped[month].append(record.value)
    missing = sorted(expected.difference(grouped))
    if missing:
        formatted = [item.strftime("%Y-%m") for item in missing]
        raise ValueError(f"JISDOR tidak memiliki observasi untuk bulan: {formatted}")
    return {
        month: sum(values, Decimal("0")) / Decimal(len(values))
        for month, values in grouped.items()
    }


def clean_bank_indonesia(
    extraction: BankIndonesiaExtraction,
    configuration: BankIndonesiaConfiguration,
    retrieved_at: datetime,
    start_date: date,
    end_date: date,
) -> CleanBankIndonesiaResult:
    validate_complete_month_range(start_date, end_date)
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("retrieved_at BI harus memiliki timezone")
    bi_rate_records = parse_bi_rate_xlsx(
        extraction.bi_rate.payload, configuration.bi_rate
    )
    jisdor_records = parse_jisdor_xml(
        extraction.jisdor.payload,
        configuration.jisdor,
        start_date=start_date,
        end_date=end_date,
    )
    months = _month_starts(start_date, end_date)
    monthly_bi_rate = _monthly_bi_rate(bi_rate_records, months)
    monthly_jisdor = _monthly_jisdor(jisdor_records, months)

    source = configuration.source
    rows: list[dict[str, object]] = []
    for month in months:
        for definition, value in (
            (configuration.bi_rate, monthly_bi_rate[month]),
            (configuration.jisdor, monthly_jisdor[month]),
        ):
            rows.append(
                {
                    "indicator_code": definition.code,
                    "indicator_name": definition.name,
                    "unit": definition.unit,
                    "frequency": definition.frequency,
                    "region_code": "IDN",
                    "region_name": "Indonesia",
                    "region_level": "country",
                    "observation_date": month.isoformat(),
                    "value": float(value),
                    "source_code": source.code,
                    "source_name": source.name,
                    "source_url": source.base_url,
                    "retrieved_at": retrieved_at,
                }
            )
    frame = pd.DataFrame(rows, columns=STANDARD_COLUMNS)
    frame["observation_date"] = pd.to_datetime(
        frame["observation_date"], format="%Y-%m-%d", errors="raise"
    )
    frame["retrieved_at"] = pd.to_datetime(
        frame["retrieved_at"], utc=True, errors="raise"
    )
    frame["value"] = pd.to_numeric(frame["value"], errors="raise")
    frame = frame.sort_values(["indicator_code", "observation_date"], ignore_index=True)
    return CleanBankIndonesiaResult(
        frame=frame,
        bi_rate_event_count=len(bi_rate_records),
        jisdor_daily_count=len(jisdor_records),
        month_count=len(months),
    )


def validate_bank_indonesia_coverage(
    frame: pd.DataFrame, configuration: BankIndonesiaConfiguration
) -> None:
    expected_codes = {configuration.bi_rate.code, configuration.jisdor.code}
    actual_codes = set(frame["indicator_code"])
    if actual_codes != expected_codes:
        raise ValueError(
            "Cakupan indikator BI tidak lengkap: "
            f"expected={sorted(expected_codes)}, actual={sorted(actual_codes)}"
        )
    coverage = {
        code: set(frame.loc[frame["indicator_code"].eq(code), "observation_date"])
        for code in expected_codes
    }
    date_sets = list(coverage.values())
    if not date_sets[0] or date_sets[0] != date_sets[1]:
        raise ValueError("Periode BI-Rate dan JISDOR bulanan tidak sejajar")


def validate_bank_indonesia_value_ranges(
    frame: pd.DataFrame, configuration: BankIndonesiaConfiguration
) -> None:
    bi_rate_values = frame.loc[
        frame["indicator_code"].eq(configuration.bi_rate.code), "value"
    ]
    if bi_rate_values.empty or not bi_rate_values.between(0, 100).all():
        raise ValueError("BI-Rate berada di luar rentang 0 sampai 100 persen")
    jisdor_values = frame.loc[
        frame["indicator_code"].eq(configuration.jisdor.code), "value"
    ]
    if jisdor_values.empty or not jisdor_values.between(1, 1_000_000).all():
        raise ValueError("JISDOR berada di luar rentang positif yang didukung")
