from datetime import UTC, datetime

import pandas as pd

from pipelines.transform.clean_economic_data import clean_world_bank
from pipelines.utils.config import IndicatorDefinition


def record(year: str, value: float | None) -> dict:
    return {
        "indicator": {"id": "NY.GDP.MKTP.KD.ZG", "value": "GDP growth"},
        "country": {"id": "ID", "value": "Indonesia"},
        "countryiso3code": "IDN",
        "date": year,
        "value": value,
    }


def test_transform_produces_sorted_typed_data():
    definitions = {
        "NY.GDP.MKTP.KD.ZG": IndicatorDefinition(
            code="NY.GDP.MKTP.KD.ZG",
            name="GDP growth",
            unit="percent",
            frequency="annual",
            source="world_bank",
        )
    }
    retrieved_at = datetime(2026, 1, 1, tzinfo=UTC)

    frame = clean_world_bank(
        [record("2023", 5.05), record("2021", 3.7), record("2022", None)],
        definitions,
        retrieved_at,
    )

    assert frame["observation_date"].tolist() == [
        pd.Timestamp("2021-01-01"),
        pd.Timestamp("2023-01-01"),
    ]
    assert pd.api.types.is_datetime64_any_dtype(frame["observation_date"])
    assert pd.api.types.is_numeric_dtype(frame["value"])
    assert frame["unit"].unique().tolist() == ["percent"]
