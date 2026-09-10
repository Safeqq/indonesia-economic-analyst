import pandas as pd
import pytest

from analytics.descriptive.clustering import (
    InsufficientRegionalData,
    cluster_regional_features,
    prepare_regional_features,
)


def _regional_fixture() -> pd.DataFrame:
    rows = []
    values = {
        "A": (10.0, 2.0),
        "B": (11.0, 2.5),
        "C": (12.0, 2.2),
        "D": (40.0, 8.0),
        "E": (42.0, 8.5),
        "F": (41.0, 7.8),
    }
    for region, (first, second) in values.items():
        rows.extend(
            [
                {
                    "observation_year": 2024,
                    "indicator_code": "FIRST",
                    "region_code": region,
                    "value": first,
                },
                {
                    "observation_year": 2024,
                    "indicator_code": "SECOND",
                    "region_code": region,
                    "value": second,
                },
            ]
        )
    rows.append(
        {
            "observation_year": 2025,
            "indicator_code": "FIRST",
            "region_code": "A",
            "value": 12.0,
        }
    )
    return pd.DataFrame(rows)


def test_prepare_regional_features_uses_latest_complete_year() -> None:
    year, features = prepare_regional_features(_regional_fixture())

    assert year == 2024
    assert features.shape == (6, 2)
    assert list(features.index) == ["A", "B", "C", "D", "E", "F"]


def test_empty_regional_data_stops_without_synthetic_fallback() -> None:
    with pytest.raises(InsufficientRegionalData, match="BPS"):
        prepare_regional_features(pd.DataFrame())


def test_clustering_is_deterministic_and_assigns_every_region() -> None:
    year, features = prepare_regional_features(_regional_fixture())

    first = cluster_regional_features(year, features)
    second = cluster_regional_features(year, features)

    assert first.observation_year == 2024
    assert 2 <= first.cluster_count <= 5
    assert set(first.assignments["region_code"]) == set(features.index)
    assert (
        first.assignments["cluster"].tolist() == second.assignments["cluster"].tolist()
    )
    assert -1.0 <= first.silhouette <= 1.0
