from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from analytics.forecasting.baseline import (
    calculate_error_metrics,
    naive_holdout_backtest,
)
from analytics.forecasting.config import ModelSpecification


@dataclass(frozen=True)
class ModelEvaluation:
    model_name: str
    family: str
    parameters: dict[str, object]
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    training_observations: int
    test_observations: int
    metrics: dict[str, float]
    interval_coverage_percent: float | None
    converged: bool
    aic: float | None
    bic: float | None
    warnings: tuple[str, ...]
    predictions: pd.DataFrame


@dataclass(frozen=True)
class FutureForecast:
    model_name: str
    family: str
    parameters: dict[str, object]
    confidence_level: float
    converged: bool
    aic: float
    bic: float
    warnings: tuple[str, ...]
    parameter_estimates: dict[str, float]
    values: pd.DataFrame


def prepare_regular_series(
    frame: pd.DataFrame,
    *,
    date_column: str,
    value_column: str,
    frequency: str,
) -> pd.Series:
    missing = {date_column, value_column}.difference(frame.columns)
    if missing:
        raise ValueError(f"Kolom time series tidak ditemukan: {sorted(missing)}")
    values = frame[[date_column, value_column]].copy()
    values[date_column] = pd.to_datetime(values[date_column], errors="raise")
    values[value_column] = pd.to_numeric(values[value_column], errors="raise")
    values = values.sort_values(date_column, ignore_index=True)
    if values.empty:
        raise ValueError("Time series kosong")
    if values[date_column].duplicated().any():
        raise ValueError("Time series memiliki periode duplikat")
    if values[value_column].isna().any():
        raise ValueError("Time series memiliki missing value")
    if not np.isfinite(values[value_column]).all():
        raise ValueError("Time series memiliki nilai non-finite")
    expected_dates = pd.date_range(
        values[date_column].min(), values[date_column].max(), freq=frequency
    )
    actual_dates = pd.DatetimeIndex(values[date_column])
    missing_dates = expected_dates.difference(actual_dates)
    unexpected_dates = actual_dates.difference(expected_dates)
    if len(missing_dates) or len(unexpected_dates):
        raise ValueError(
            "Time series tidak reguler: "
            f"missing={len(missing_dates)}, unexpected={len(unexpected_dates)}"
        )
    return pd.Series(
        values[value_column].to_numpy(dtype=float),
        index=pd.DatetimeIndex(actual_dates, freq=frequency),
        name=value_column,
    )


def _specification_parameters(specification: ModelSpecification) -> dict[str, object]:
    return {
        "order": list(specification.order),
        "seasonal_order": list(specification.seasonal_order),
        "trend": specification.trend,
    }


def evaluate_naive_baseline(
    series: pd.Series,
    *,
    test_periods: int,
    prediction_lag: int,
) -> ModelEvaluation:
    frame = series.rename("value").rename_axis("observation_date").reset_index()
    result = naive_holdout_backtest(
        frame,
        date_column="observation_date",
        value_column="value",
        test_periods=test_periods,
        prediction_lag=prediction_lag,
    )
    return ModelEvaluation(
        model_name=f"naive_lag_{prediction_lag}",
        family="baseline",
        parameters={"prediction_lag": prediction_lag},
        train_start=pd.Timestamp(series.index.min()),
        train_end=result.train_end,
        test_start=result.test_start,
        test_end=pd.Timestamp(result.predictions["observation_date"].max()),
        training_observations=len(series) - test_periods,
        test_observations=len(result.predictions),
        metrics=result.metrics,
        interval_coverage_percent=None,
        converged=True,
        aic=None,
        bic=None,
        warnings=(),
        predictions=result.predictions,
    )


def _fit_model(series: pd.Series, specification: ModelSpecification):
    caught: list[warnings.WarningMessage]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fitted = SARIMAX(
            series,
            order=specification.order,
            seasonal_order=specification.seasonal_order,
            trend=specification.trend,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False, maxiter=200)
    messages = tuple(dict.fromkeys(str(item.message) for item in caught))
    return fitted, messages


def backtest_sarima(
    series: pd.Series,
    specification: ModelSpecification,
    *,
    test_periods: int,
    confidence_level: float,
) -> ModelEvaluation:
    if len(series) <= test_periods + max(3, specification.seasonal_order[3]):
        raise ValueError(f"Time series terlalu pendek untuk {specification.name}")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level harus lebih dari 0 dan kurang dari 1")
    training = series.iloc[:-test_periods]
    test = series.iloc[-test_periods:]
    initial_result, fit_warnings = _fit_model(training, specification)
    converged = bool(initial_result.mle_retvals.get("converged", False))
    current_result = initial_result
    rows: list[dict[str, object]] = []
    alpha = 1 - confidence_level
    for observation_date, actual in test.items():
        estimate = current_result.get_forecast(steps=1)
        prediction = float(estimate.predicted_mean.iloc[0])
        interval = estimate.conf_int(alpha=alpha).iloc[0]
        lower_bound = float(interval.iloc[0])
        upper_bound = float(interval.iloc[1])
        rows.append(
            {
                "observation_date": pd.Timestamp(observation_date),
                "actual": float(actual),
                "prediction": prediction,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "error": float(actual) - prediction,
            }
        )
        new_observation = pd.Series(
            [actual],
            index=pd.DatetimeIndex([observation_date], freq=series.index.freq),
            name=series.name,
        )
        current_result = current_result.append(new_observation, refit=False)
    predictions = pd.DataFrame(rows)
    metrics = calculate_error_metrics(predictions["actual"], predictions["prediction"])
    covered = predictions["actual"].between(
        predictions["lower_bound"], predictions["upper_bound"], inclusive="both"
    )
    return ModelEvaluation(
        model_name=specification.name,
        family=specification.family,
        parameters=_specification_parameters(specification),
        train_start=pd.Timestamp(training.index.min()),
        train_end=pd.Timestamp(training.index.max()),
        test_start=pd.Timestamp(test.index.min()),
        test_end=pd.Timestamp(test.index.max()),
        training_observations=len(training),
        test_observations=len(test),
        metrics=metrics,
        interval_coverage_percent=float(covered.mean() * 100),
        converged=converged,
        aic=float(initial_result.aic),
        bic=float(initial_result.bic),
        warnings=fit_warnings,
        predictions=predictions,
    )


def fit_future_forecast(
    series: pd.Series,
    specification: ModelSpecification,
    *,
    horizon: int,
    confidence_level: float,
) -> FutureForecast:
    if horizon < 1:
        raise ValueError("Forecast horizon harus positif")
    fitted, fit_warnings = _fit_model(series, specification)
    converged = bool(fitted.mle_retvals.get("converged", False))
    if not converged:
        raise RuntimeError(f"Model final tidak konvergen: {specification.name}")
    estimate = fitted.get_forecast(steps=horizon)
    interval = estimate.conf_int(alpha=1 - confidence_level)
    values = pd.DataFrame(
        {
            "forecast_date": pd.DatetimeIndex(estimate.predicted_mean.index),
            "point_forecast": estimate.predicted_mean.to_numpy(dtype=float),
            "lower_bound": interval.iloc[:, 0].to_numpy(dtype=float),
            "upper_bound": interval.iloc[:, 1].to_numpy(dtype=float),
        }
    )
    if not np.isfinite(values.iloc[:, 1:].to_numpy()).all():
        raise RuntimeError("Forecast menghasilkan nilai non-finite")
    parameter_estimates = {
        str(name): float(value)
        for name, value in zip(fitted.param_names, fitted.params, strict=True)
    }
    return FutureForecast(
        model_name=specification.name,
        family=specification.family,
        parameters=_specification_parameters(specification),
        confidence_level=confidence_level,
        converged=converged,
        aic=float(fitted.aic),
        bic=float(fitted.bic),
        warnings=fit_warnings,
        parameter_estimates=parameter_estimates,
        values=values,
    )
