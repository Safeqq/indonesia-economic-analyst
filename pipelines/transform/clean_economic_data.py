from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from pipelines.extract.extract_world_bank import BASE_URL, SOURCE_CODE, SOURCE_NAME
from pipelines.utils.config import IndicatorDefinition

STANDARD_COLUMNS = [
    "indicator_code",
    "indicator_name",
    "unit",
    "frequency",
    "region_code",
    "region_name",
    "region_level",
    "observation_date",
    "value",
    "source_code",
    "source_name",
    "source_url",
    "retrieved_at",
]


def clean_world_bank(
    records: list[dict[str, Any]],
    definitions: dict[str, IndicatorDefinition],
    retrieved_at: datetime,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for position, item in enumerate(records, start=1):
        if item.get("value") is None:
            continue
        try:
            indicator_code = str(item["indicator"]["id"])
            region_code = str(item["countryiso3code"])
            region_name = str(item["country"]["value"])
            year = int(item["date"])
            value = item["value"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Record World Bank ke-{position} memiliki struktur tidak valid"
            ) from exc

        definition = definitions.get(indicator_code)
        if definition is None:
            raise ValueError(
                f"Indikator {indicator_code} tidak ditemukan dalam konfigurasi"
            )
        rows.append(
            {
                "indicator_code": indicator_code,
                "indicator_name": definition.name,
                "unit": definition.unit,
                "frequency": definition.frequency,
                "region_code": region_code,
                "region_name": region_name,
                "region_level": "country",
                "observation_date": f"{year:04d}-01-01",
                "value": value,
                "source_code": SOURCE_CODE,
                "source_name": SOURCE_NAME,
                "source_url": BASE_URL,
                "retrieved_at": retrieved_at,
            }
        )

    frame = pd.DataFrame(rows, columns=STANDARD_COLUMNS)
    if frame.empty:
        return frame

    try:
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"], format="%Y-%m-%d", errors="raise"
        )
        frame["retrieved_at"] = pd.to_datetime(
            frame["retrieved_at"], utc=True, errors="raise"
        )
        frame["value"] = pd.to_numeric(frame["value"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("Tipe data World Bank tidak dapat dinormalisasi") from exc

    return frame.sort_values(
        ["indicator_code", "region_code", "observation_date"],
        ignore_index=True,
    )
