import numpy as np
import pandas as pd
import pytest

from analytics.descriptive.statistics import (
    add_growth_rates,
    correlation_with_overlap,
    iqr_outliers,
    lagged_correlation,
    latest_indonesia_vs_asean,
    monthly_seasonality,
    profile_frame,
)


def test_profile_frame_reports_missing_values() -> None:
    frame = pd.DataFrame({"complete": [1, 2], "partial": [1.0, np.nan]})

    profile = profile_frame(frame).set_index("column")

    assert profile.at["complete", "missing_count"] == 0
    assert profile.at["partial", "missing_count"] == 1
    assert profile.at["partial", "missing_percent"] == pytest.approx(50.0)


def test_growth_rate_uses_previous_period_and_handles_zero() -> None:
    frame = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(
                ["2022-01-01", "2020-01-01", "2021-01-01"]
            ),
            "value": [12.0, 0.0, 10.0],
        }
    )

    result = add_growth_rates(frame, ["value"])

    assert result["value"].tolist() == [0.0, 10.0, 12.0]
    assert np.isnan(result.iloc[1]["value_growth_percent"])
    assert result.iloc[2]["value_growth_percent"] == pytest.approx(20.0)


def test_iqr_outliers_reports_bounds_and_period() -> None:
    frame = pd.DataFrame(
        {
            "observation_date": pd.date_range("2020-01-01", periods=8, freq="YS"),
            "value": [10, 10, 11, 9, 10, 11, 10, 100],
        }
    )

    result = iqr_outliers(frame, ["value"])

    assert len(result) == 1
    assert result.iloc[0]["value"] == 100
    assert result.iloc[0]["direction"] == "high"
    assert result.iloc[0]["observation_date"] == pd.Timestamp("2027-01-01")


def test_monthly_seasonality_groups_same_calendar_month() -> None:
    frame = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(
                ["2023-01-01", "2023-02-01", "2024-01-01", "2024-02-01"]
            ),
            "value": [10.0, 20.0, 14.0, 24.0],
        }
    )

    result = monthly_seasonality(frame, "value").set_index("calendar_month")

    assert result.at[1, "observation_count"] == 2
    assert result.at[1, "mean"] == pytest.approx(12.0)
    assert result.at[2, "median"] == pytest.approx(22.0)


def test_correlation_reports_pairwise_overlap() -> None:
    frame = pd.DataFrame(
        {
            "first": [1.0, 2.0, 3.0, 4.0],
            "second": [2.0, 4.0, np.nan, 8.0],
        }
    )

    correlations, overlap = correlation_with_overlap(
        frame, ["first", "second"], min_periods=3
    )

    assert correlations.at["first", "second"] == pytest.approx(1.0)
    assert overlap.at["first", "second"] == 3


def test_positive_lag_compares_target_with_prior_feature() -> None:
    feature = [2, 8, 1, 7, 3, 9, 4, 6, 0, 5]
    frame = pd.DataFrame(
        {
            "observation_year": range(2010, 2020),
            "feature": feature,
            "target": [np.nan, *feature[:-1]],
        }
    )

    result = lagged_correlation(frame, "target", "feature", [0, 1])

    lag_one = result.loc[result["lag"].eq(1)].iloc[0]
    assert lag_one["correlation"] == pytest.approx(1.0)
    assert lag_one["observation_count"] == 9


def test_indonesia_asean_summary_uses_latest_year_per_indicator() -> None:
    frame = pd.DataFrame(
        [
            {
                "indicator_code": "GDP",
                "indicator_name": "GDP growth",
                "unit": "percent",
                "region_code": "IDN",
                "observation_year": 2023,
                "value": 5.0,
                "asean_average": 4.0,
                "difference_from_asean_average": 1.0,
                "country_coverage": 10,
                "value_rank_desc": 4,
            },
            {
                "indicator_code": "GDP",
                "indicator_name": "GDP growth",
                "unit": "percent",
                "region_code": "IDN",
                "observation_year": 2024,
                "value": 5.1,
                "asean_average": 4.2,
                "difference_from_asean_average": 0.9,
                "country_coverage": 11,
                "value_rank_desc": 5,
            },
            {
                "indicator_code": "GDP",
                "indicator_name": "GDP growth",
                "unit": "percent",
                "region_code": "MYS",
                "observation_year": 2025,
                "value": 4.5,
                "asean_average": 4.3,
                "difference_from_asean_average": 0.2,
                "country_coverage": 11,
                "value_rank_desc": 6,
            },
        ]
    )

    result = latest_indonesia_vs_asean(frame)

    assert len(result) == 1
    assert result.iloc[0]["observation_year"] == 2024
    assert result.iloc[0]["value"] == pytest.approx(5.1)
