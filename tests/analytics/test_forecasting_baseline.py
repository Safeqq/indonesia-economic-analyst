import math

import pandas as pd
import pytest

from analytics.forecasting.baseline import (
    calculate_error_metrics,
    naive_holdout_backtest,
    time_series_readiness,
)


def test_time_series_readiness_detects_missing_month() -> None:
    frame = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(["2025-01-01", "2025-03-01"]),
            "value": [1.0, 2.0],
        }
    )

    result = time_series_readiness(
        frame, date_column="observation_date", value_column="value"
    )

    assert result["missing_period_count"] == 1
    assert result["missing_periods"] == (pd.Timestamp("2025-02-01"),)


def test_naive_backtest_uses_time_based_holdout() -> None:
    frame = pd.DataFrame(
        {
            "observation_date": pd.date_range("2024-01-01", periods=8, freq="MS"),
            "value": [1.0, 3.0, 2.0, 5.0, 4.0, 7.0, 6.0, 9.0],
        }
    )

    result = naive_holdout_backtest(
        frame,
        date_column="observation_date",
        value_column="value",
        test_periods=3,
    )

    assert result.train_end == pd.Timestamp("2024-05-01")
    assert result.test_start == pd.Timestamp("2024-06-01")
    assert result.predictions["prediction"].tolist() == [4.0, 7.0, 6.0]
    assert result.metrics["mae"] == pytest.approx(7 / 3)


def test_mape_ignores_zero_actual_values() -> None:
    frame = pd.DataFrame(
        {
            "observation_date": pd.date_range("2024-01-01", periods=5, freq="MS"),
            "value": [1.0, 2.0, 3.0, 0.0, 5.0],
        }
    )

    result = naive_holdout_backtest(
        frame,
        date_column="observation_date",
        value_column="value",
        test_periods=2,
    )

    assert math.isfinite(result.metrics["mape_percent"])
    assert result.metrics["mape_percent"] == pytest.approx(100.0)


def test_error_metrics_compare_values_by_position() -> None:
    actual = pd.Series([10.0, 20.0], index=[100, 101])
    prediction = pd.Series([8.0, 24.0], index=[1, 2])

    result = calculate_error_metrics(actual, prediction)

    assert result["mae"] == pytest.approx(3.0)
    assert result["rmse"] == pytest.approx(math.sqrt(10))
    assert result["mape_percent"] == pytest.approx(20.0)
