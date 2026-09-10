import numpy as np
import pandas as pd
import pytest

from analytics.forecasting.config import ModelSpecification
from analytics.forecasting.models import (
    backtest_sarima,
    fit_future_forecast,
    prepare_regular_series,
)


def _monthly_fixture(periods: int = 72) -> pd.DataFrame:
    index = np.arange(periods)
    return pd.DataFrame(
        {
            "observation_date": pd.date_range("2019-01-01", periods=periods, freq="MS"),
            "value": 14_000 + 15 * index + 80 * np.sin(2 * np.pi * index / 12),
        }
    )


def _arima_specification() -> ModelSpecification:
    return ModelSpecification(
        name="arima_test",
        family="arima",
        order=(0, 1, 1),
        seasonal_order=(0, 0, 0, 0),
        trend="t",
    )


def test_prepare_regular_series_rejects_missing_month() -> None:
    frame = _monthly_fixture(12).drop(index=5)

    with pytest.raises(ValueError, match="tidak reguler"):
        prepare_regular_series(
            frame,
            date_column="observation_date",
            value_column="value",
            frequency="MS",
        )


def test_arima_backtest_is_out_of_sample_with_intervals() -> None:
    series = prepare_regular_series(
        _monthly_fixture(),
        date_column="observation_date",
        value_column="value",
        frequency="MS",
    )

    result = backtest_sarima(
        series,
        _arima_specification(),
        test_periods=12,
        confidence_level=0.95,
    )

    assert result.train_end < result.test_start
    assert result.test_observations == 12
    assert len(result.predictions) == 12
    assert (
        result.predictions["actual"]
        .between(result.predictions["lower_bound"], result.predictions["upper_bound"])
        .all()
    )
    assert all(np.isfinite(value) for value in result.metrics.values())


def test_future_forecast_starts_after_last_observation() -> None:
    series = prepare_regular_series(
        _monthly_fixture(),
        date_column="observation_date",
        value_column="value",
        frequency="MS",
    )

    result = fit_future_forecast(
        series,
        _arima_specification(),
        horizon=3,
        confidence_level=0.95,
    )

    assert len(result.values) == 3
    assert result.values.iloc[0]["forecast_date"] > series.index.max()
    assert (
        result.values["point_forecast"]
        .between(result.values["lower_bound"], result.values["upper_bound"])
        .all()
    )
