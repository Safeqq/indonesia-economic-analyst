from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADVANCED_ANALYTICS_CONFIG = PROJECT_ROOT / "config" / "advanced_analytics.yml"


@dataclass(frozen=True)
class ModelSpecification:
    name: str
    family: str
    order: tuple[int, int, int]
    seasonal_order: tuple[int, int, int, int]
    trend: str


@dataclass(frozen=True)
class QualityGateConfiguration:
    minimum_mae_improvement_percent: float
    maximum_mape_percent: float
    minimum_interval_coverage_percent: float


@dataclass(frozen=True)
class ForecastConfiguration:
    indicator_code: str
    region_code: str
    source_code: str
    date_column: str
    value_column: str
    frequency: str
    test_periods: int
    horizon: int
    confidence_level: float
    baseline_lags: tuple[int, ...]
    candidate_models: tuple[ModelSpecification, ...]
    quality_gate: QualityGateConfiguration


@dataclass(frozen=True)
class AnomalyConfiguration:
    method: str
    window: int
    minimum_history: int
    threshold: float


@dataclass(frozen=True)
class AdvancedAnalyticsConfiguration:
    pipeline_version: str
    forecast: ForecastConfiguration
    anomaly_detection: AnomalyConfiguration


def _mapping(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError(f"Konfigurasi {label} harus berupa mapping")
    return payload


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"Konfigurasi {label} harus berupa integer positif")
    return value


def _bounded_percentage(value: object, label: str) -> float:
    number = float(value)
    if not 0 <= number <= 100:
        raise ValueError(f"Konfigurasi {label} harus berada pada rentang 0 sampai 100")
    return number


def _integer_tuple(value: object, length: int, label: str) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"Konfigurasi {label} harus memiliki {length} integer")
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0
        for item in value
    ):
        raise ValueError(f"Konfigurasi {label} hanya menerima integer non-negatif")
    return tuple(value)


def _model_specifications(payload: object) -> tuple[ModelSpecification, ...]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("candidate_models harus berupa list yang tidak kosong")
    models: list[ModelSpecification] = []
    for position, raw_model in enumerate(payload, start=1):
        model = _mapping(raw_model, f"candidate_models ke-{position}")
        family = str(model.get("family", ""))
        if family not in {"arima", "sarima"}:
            raise ValueError(f"Family model tidak didukung: {family!r}")
        trend = str(model.get("trend", ""))
        if trend not in {"n", "c", "t", "ct"}:
            raise ValueError(f"Trend model tidak didukung: {trend!r}")
        models.append(
            ModelSpecification(
                name=str(model.get("name", "")).strip(),
                family=family,
                order=_integer_tuple(model.get("order"), 3, "order"),
                seasonal_order=_integer_tuple(
                    model.get("seasonal_order"), 4, "seasonal_order"
                ),
                trend=trend,
            )
        )
    names = [model.name for model in models]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("Nama candidate_models wajib unik dan tidak boleh kosong")
    for model in models:
        seasonal_period = model.seasonal_order[3]
        if model.family == "arima" and model.seasonal_order != (0, 0, 0, 0):
            raise ValueError(
                f"Model ARIMA tidak boleh memiliki seasonal order: {model.name}"
            )
        if model.family == "sarima" and seasonal_period < 2:
            raise ValueError(f"Model SARIMA memerlukan periode musiman: {model.name}")
    return tuple(models)


def load_advanced_analytics_configuration(
    path: Path = DEFAULT_ADVANCED_ANALYTICS_CONFIG,
) -> AdvancedAnalyticsConfiguration:
    with path.open(encoding="utf-8") as config_file:
        root = _mapping(yaml.safe_load(config_file), "advanced analytics")

    forecast = _mapping(root.get("forecast"), "forecast")
    gate = _mapping(forecast.get("quality_gate"), "quality_gate")
    anomaly = _mapping(root.get("anomaly_detection"), "anomaly_detection")
    confidence_level = float(forecast.get("confidence_level", 0))
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level harus lebih dari 0 dan kurang dari 1")
    raw_baseline_lags = forecast.get("baseline_lags")
    if not isinstance(raw_baseline_lags, list) or not raw_baseline_lags:
        raise ValueError("baseline_lags harus berupa list yang tidak kosong")
    baseline_lags = _integer_tuple(
        raw_baseline_lags, len(raw_baseline_lags), "baseline_lags"
    )
    if not baseline_lags or any(lag < 1 for lag in baseline_lags):
        raise ValueError("baseline_lags wajib berisi integer positif")
    if len(set(baseline_lags)) != len(baseline_lags):
        raise ValueError("baseline_lags tidak boleh duplikat")

    configuration = AdvancedAnalyticsConfiguration(
        pipeline_version=str(root.get("pipeline_version", "")).strip(),
        forecast=ForecastConfiguration(
            indicator_code=str(forecast.get("indicator_code", "")).strip(),
            region_code=str(forecast.get("region_code", "")).strip(),
            source_code=str(forecast.get("source_code", "")).strip(),
            date_column=str(forecast.get("date_column", "")).strip(),
            value_column=str(forecast.get("value_column", "")).strip(),
            frequency=str(forecast.get("frequency", "")).strip(),
            test_periods=_positive_integer(
                forecast.get("test_periods"), "test_periods"
            ),
            horizon=_positive_integer(forecast.get("horizon"), "horizon"),
            confidence_level=confidence_level,
            baseline_lags=baseline_lags,
            candidate_models=_model_specifications(forecast.get("candidate_models")),
            quality_gate=QualityGateConfiguration(
                minimum_mae_improvement_percent=float(
                    gate.get("minimum_mae_improvement_percent")
                ),
                maximum_mape_percent=_bounded_percentage(
                    gate.get("maximum_mape_percent"), "maximum_mape_percent"
                ),
                minimum_interval_coverage_percent=_bounded_percentage(
                    gate.get("minimum_interval_coverage_percent"),
                    "minimum_interval_coverage_percent",
                ),
            ),
        ),
        anomaly_detection=AnomalyConfiguration(
            method=str(anomaly.get("method", "")).strip(),
            window=_positive_integer(anomaly.get("window"), "anomaly window"),
            minimum_history=_positive_integer(
                anomaly.get("minimum_history"), "anomaly minimum_history"
            ),
            threshold=float(anomaly.get("threshold", 0)),
        ),
    )
    required_strings = {
        "pipeline_version": configuration.pipeline_version,
        "indicator_code": configuration.forecast.indicator_code,
        "region_code": configuration.forecast.region_code,
        "source_code": configuration.forecast.source_code,
        "date_column": configuration.forecast.date_column,
        "value_column": configuration.forecast.value_column,
        "frequency": configuration.forecast.frequency,
    }
    missing = [name for name, value in required_strings.items() if not value]
    if missing:
        raise ValueError(f"Konfigurasi wajib kosong: {missing}")
    baseline_names = {
        f"naive_lag_{lag}" for lag in configuration.forecast.baseline_lags
    }
    candidate_names = {model.name for model in configuration.forecast.candidate_models}
    collisions = sorted(baseline_names.intersection(candidate_names))
    if collisions:
        raise ValueError(
            f"Nama candidate_models bertabrakan dengan baseline: {collisions}"
        )
    if configuration.forecast.quality_gate.minimum_mae_improvement_percent < 0:
        raise ValueError("minimum_mae_improvement_percent tidak boleh negatif")
    if configuration.anomaly_detection.method != "rolling_mad_first_difference":
        raise ValueError("Metode anomaly detection belum didukung")
    if (
        configuration.anomaly_detection.minimum_history
        > configuration.anomaly_detection.window
    ):
        raise ValueError("minimum_history tidak boleh melebihi anomaly window")
    if configuration.anomaly_detection.threshold <= 0:
        raise ValueError("Anomaly threshold harus positif")
    return configuration
