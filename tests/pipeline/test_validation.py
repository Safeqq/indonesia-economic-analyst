from datetime import UTC, datetime

import pandas as pd
import pytest

from pipelines.transform.clean_economic_data import STANDARD_COLUMNS
from pipelines.transform.validate_data import validate


def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "indicator_code": "NY.GDP.MKTP.KD.ZG",
                "indicator_name": "GDP growth",
                "unit": "percent",
                "frequency": "annual",
                "region_code": "IDN",
                "region_name": "Indonesia",
                "region_level": "country",
                "observation_date": pd.Timestamp("2023-01-01"),
                "value": 5.05,
                "source_code": "world_bank",
                "source_name": "World Bank Open Data",
                "source_url": "https://api.worldbank.org/v2",
                "retrieved_at": datetime(2026, 1, 1, tzinfo=UTC),
            }
        ]
    )


def test_empty_dataset_is_rejected():
    with pytest.raises(ValueError, match="Dataset kosong"):
        validate(pd.DataFrame(columns=STANDARD_COLUMNS))


def test_duplicate_observation_is_rejected():
    frame = pd.concat([valid_frame(), valid_frame()], ignore_index=True)

    with pytest.raises(ValueError, match="observasi duplikat"):
        validate(frame)


def test_non_finite_value_is_rejected():
    frame = valid_frame()
    frame.loc[0, "value"] = float("inf")

    with pytest.raises(ValueError, match="tidak finite"):
        validate(frame)
