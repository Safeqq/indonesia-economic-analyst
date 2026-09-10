from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BaselineBacktest:
    prediction_lag: int
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    metrics: dict[str, float]
    predictions: pd.DataFrame


def time_series_readiness(
    frame: pd.DataFrame,
    *,
    date_column: str,
    value_column: str,
    frequency: str = "MS",
) -> dict[str, object]:
    values = frame[[date_column, value_column]].dropna().sort_values(date_column)
    if values.empty:
        raise ValueError("Time series kosong")
    dates = pd.DatetimeIndex(pd.to_datetime(values[date_column], errors="raise"))
    if dates.duplicated().any():
        raise ValueError("Time series memiliki periode duplikat")
    expected = pd.date_range(dates.min(), dates.max(), freq=frequency)
    missing = expected.difference(dates)
    return {
        "observation_count": len(values),
        "period_start": dates.min(),
        "period_end": dates.max(),
        "missing_period_count": len(missing),
        "missing_periods": tuple(missing),
    }


def _metrics(actual: pd.Series, prediction: pd.Series) -> dict[str, float]:
    errors = actual - prediction
    absolute = errors.abs()
    nonzero = actual.ne(0)
    mape = (
        float((absolute[nonzero] / actual[nonzero].abs()).mean() * 100)
        if nonzero.any()
        else np.nan
    )
    return {
        "mae": float(absolute.mean()),
        "rmse": float(np.sqrt((errors**2).mean())),
        "mape_percent": mape,
    }


def naive_holdout_backtest(
    frame: pd.DataFrame,
    *,
    date_column: str,
    value_column: str,
    test_periods: int,
    prediction_lag: int = 1,
) -> BaselineBacktest:
    if test_periods < 1 or prediction_lag < 1:
        raise ValueError("test_periods dan prediction_lag harus positif")
    values = frame[[date_column, value_column]].dropna().copy()
    values[date_column] = pd.to_datetime(values[date_column], errors="raise")
    values[value_column] = pd.to_numeric(values[value_column], errors="raise")
    values = values.sort_values(date_column, ignore_index=True)
    if values[date_column].duplicated().any():
        raise ValueError("Backtest memerlukan satu nilai per periode")
    if len(values) <= test_periods + prediction_lag:
        raise ValueError("Time series terlalu pendek untuk holdout yang diminta")

    values["prediction"] = values[value_column].shift(prediction_lag)
    test = values.tail(test_periods).dropna(subset=["prediction"]).copy()
    train_end = values.iloc[-test_periods - 1][date_column]
    predictions = test.rename(columns={value_column: "actual"})[
        [date_column, "actual", "prediction"]
    ]
    predictions["error"] = predictions["actual"] - predictions["prediction"]
    return BaselineBacktest(
        prediction_lag=prediction_lag,
        train_end=pd.Timestamp(train_end),
        test_start=pd.Timestamp(predictions[date_column].min()),
        metrics=_metrics(predictions["actual"], predictions["prediction"]),
        predictions=predictions.reset_index(drop=True),
    )
