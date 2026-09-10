from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import pandas as pd

from analytics.anomaly_detection.statistical import (
    AnomalyDetectionResult,
    detect_rolling_mad_anomalies,
)
from analytics.forecasting.config import AdvancedAnalyticsConfiguration
from analytics.forecasting.models import (
    FutureForecast,
    ModelEvaluation,
    backtest_sarima,
    evaluate_naive_baseline,
    fit_future_forecast,
    prepare_regular_series,
)
from analytics.forecasting.quality_gate import (
    QualityGateDecision,
    evaluate_quality_gate,
)


@dataclass(frozen=True)
class AdvancedAnalyticsRun:
    run_key: str
    data_fingerprint: str
    config_fingerprint: str
    generated_at: datetime
    configuration: AdvancedAnalyticsConfiguration
    series: pd.Series
    evaluations: tuple[ModelEvaluation, ...]
    quality_gate: QualityGateDecision
    future_forecast: FutureForecast | None
    anomalies: AnomalyDetectionResult


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fingerprint_series(series: pd.Series) -> str:
    records = [
        {"date": pd.Timestamp(index).date().isoformat(), "value": float(value)}
        for index, value in series.items()
    ]
    return _sha256(json.dumps(records, sort_keys=True, separators=(",", ":")))


def fingerprint_configuration(configuration: AdvancedAnalyticsConfiguration) -> str:
    return _sha256(
        json.dumps(asdict(configuration), sort_keys=True, separators=(",", ":"))
    )


def execute_advanced_analytics(
    frame: pd.DataFrame,
    configuration: AdvancedAnalyticsConfiguration,
    *,
    revision_events: dict[object, str] | None = None,
    generated_at: datetime | None = None,
) -> AdvancedAnalyticsRun:
    forecast_configuration = configuration.forecast
    anomaly_configuration = configuration.anomaly_detection
    anomalies = detect_rolling_mad_anomalies(
        frame,
        date_column=forecast_configuration.date_column,
        value_column=forecast_configuration.value_column,
        frequency=forecast_configuration.frequency,
        window=anomaly_configuration.window,
        minimum_history=anomaly_configuration.minimum_history,
        threshold=anomaly_configuration.threshold,
        revision_events=revision_events,
    )
    series = prepare_regular_series(
        frame,
        date_column=forecast_configuration.date_column,
        value_column=forecast_configuration.value_column,
        frequency=forecast_configuration.frequency,
    )
    evaluations: list[ModelEvaluation] = []
    for prediction_lag in forecast_configuration.baseline_lags:
        evaluations.append(
            evaluate_naive_baseline(
                series,
                test_periods=forecast_configuration.test_periods,
                prediction_lag=prediction_lag,
            )
        )
    for specification in forecast_configuration.candidate_models:
        evaluations.append(
            backtest_sarima(
                series,
                specification,
                test_periods=forecast_configuration.test_periods,
                confidence_level=forecast_configuration.confidence_level,
            )
        )
    decision = evaluate_quality_gate(evaluations, forecast_configuration.quality_gate)
    future_forecast = None
    if decision.passed:
        selected_specification = next(
            specification
            for specification in forecast_configuration.candidate_models
            if specification.name == decision.selected_model_name
        )
        future_forecast = fit_future_forecast(
            series,
            selected_specification,
            horizon=forecast_configuration.horizon,
            confidence_level=forecast_configuration.confidence_level,
        )

    data_fingerprint = fingerprint_series(series)
    config_fingerprint = fingerprint_configuration(configuration)
    run_key = _sha256(
        ":".join([configuration.pipeline_version, data_fingerprint, config_fingerprint])
    )
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    else:
        timestamp = timestamp.astimezone(UTC)
    return AdvancedAnalyticsRun(
        run_key=run_key,
        data_fingerprint=data_fingerprint,
        config_fingerprint=config_fingerprint,
        generated_at=timestamp,
        configuration=configuration,
        series=series,
        evaluations=tuple(evaluations),
        quality_gate=decision,
        future_forecast=future_forecast,
        anomalies=anomalies,
    )
