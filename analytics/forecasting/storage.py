from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from datetime import UTC, date, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from analytics.forecasting.models import FutureForecast, ModelEvaluation
from analytics.forecasting.run import AdvancedAnalyticsRun
from pipelines.utils.database import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIRECTORY = PROJECT_ROOT / "data" / "exports" / "advanced_analytics"


@dataclass(frozen=True)
class PersistenceResult:
    forecast_run_id: int
    forecast_rows: int
    anomaly_rows: int


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def serialize_evaluation(evaluation: ModelEvaluation) -> dict[str, object]:
    predictions = evaluation.predictions.copy()
    if "observation_date" in predictions:
        predictions["observation_date"] = predictions["observation_date"].map(
            lambda value: pd.Timestamp(value).date().isoformat()
        )
    return _json_ready(
        {
            "model_name": evaluation.model_name,
            "family": evaluation.family,
            "parameters": evaluation.parameters,
            "train_start": evaluation.train_start.date().isoformat(),
            "train_end": evaluation.train_end.date().isoformat(),
            "test_start": evaluation.test_start.date().isoformat(),
            "test_end": evaluation.test_end.date().isoformat(),
            "training_observations": evaluation.training_observations,
            "test_observations": evaluation.test_observations,
            "metrics": evaluation.metrics,
            "interval_coverage_percent": evaluation.interval_coverage_percent,
            "converged": evaluation.converged,
            "aic": evaluation.aic,
            "bic": evaluation.bic,
            "warnings": evaluation.warnings,
            "predictions": predictions.to_dict("records"),
        }
    )


def serialize_final_model(forecast: FutureForecast | None) -> dict[str, object] | None:
    if forecast is None:
        return None
    return _json_ready(
        {
            "model_name": forecast.model_name,
            "family": forecast.family,
            "parameters": forecast.parameters,
            "confidence_level": forecast.confidence_level,
            "converged": forecast.converged,
            "aic": forecast.aic,
            "bic": forecast.bic,
            "warnings": forecast.warnings,
            "parameter_estimates": forecast.parameter_estimates,
            "library_versions": {
                "python": platform.python_version(),
                "numpy": version("numpy"),
                "pandas": version("pandas"),
                "statsmodels": version("statsmodels"),
            },
        }
    )


def build_run_payload(run: AdvancedAnalyticsRun) -> dict[str, object]:
    forecast_values: list[dict[str, object]] = []
    if run.future_forecast is not None:
        values = run.future_forecast.values.copy()
        values["forecast_date"] = values["forecast_date"].map(
            lambda value: pd.Timestamp(value).date().isoformat()
        )
        forecast_values = values.to_dict("records")
    anomaly_events = run.anomalies.events.copy()
    if not anomaly_events.empty:
        anomaly_events["observation_date"] = anomaly_events["observation_date"].map(
            lambda value: pd.Timestamp(value).date().isoformat()
        )
    return _json_ready(
        {
            "run_key": run.run_key,
            "pipeline_version": run.configuration.pipeline_version,
            "generated_at": run.generated_at,
            "indicator_code": run.configuration.forecast.indicator_code,
            "region_code": run.configuration.forecast.region_code,
            "source_code": run.configuration.forecast.source_code,
            "data_fingerprint": run.data_fingerprint,
            "config_fingerprint": run.config_fingerprint,
            "data_start": run.series.index.min(),
            "data_end": run.series.index.max(),
            "quality_gate": {
                "passed": run.quality_gate.passed,
                "selected_model_name": run.quality_gate.selected_model_name,
                "baseline_model_name": run.quality_gate.baseline_model_name,
                "mae_improvement_percent": (run.quality_gate.mae_improvement_percent),
                "reasons": run.quality_gate.reasons,
                "thresholds": run.quality_gate.thresholds,
            },
            "evaluations": [
                serialize_evaluation(evaluation) for evaluation in run.evaluations
            ],
            "final_model": serialize_final_model(run.future_forecast),
            "forecast_is_estimate_not_fact": True,
            "forecasts": forecast_values,
            "anomaly_detection": {
                "method": run.anomalies.method,
                "window": run.anomalies.window,
                "minimum_history": run.anomalies.minimum_history,
                "threshold": run.anomalies.threshold,
                "events": anomaly_events.to_dict("records"),
            },
        }
    )


def write_run_artifact(
    run: AdvancedAnalyticsRun,
    directory: Path = DEFAULT_ARTIFACT_DIRECTORY,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"advanced_analytics_{run.run_key[:16]}.json"
    temporary = destination.with_suffix(".json.tmp")
    payload = build_run_payload(run)
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def _dimension_ids(connection: Connection, run: AdvancedAnalyticsRun) -> dict[str, int]:
    configuration = run.configuration.forecast
    row = (
        connection.execute(
            text(
                """
            SELECT i.indicator_id, r.region_id, s.source_id
            FROM dim_indicator AS i
            CROSS JOIN dim_region AS r
            CROSS JOIN dim_source AS s
            WHERE i.indicator_code = :indicator_code
              AND r.region_code = :region_code
              AND s.source_code = :source_code
                """
            ),
            {
                "indicator_code": configuration.indicator_code,
                "region_code": configuration.region_code,
                "source_code": configuration.source_code,
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise RuntimeError(
            "Dimensi indikator, wilayah, atau sumber analytics tidak ditemukan"
        )
    return {key: int(row[key]) for key in ("indicator_id", "region_id", "source_id")}


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _optional_float(value: object) -> float | None:
    return None if pd.isna(value) else float(value)


def persist_advanced_analytics_connection(
    run: AdvancedAnalyticsRun, connection: Connection
) -> PersistenceResult:
    identifiers = _dimension_ids(connection, run)
    evaluations = {evaluation.model_name: evaluation for evaluation in run.evaluations}
    selected = evaluations[run.quality_gate.selected_model_name]
    baseline = evaluations[run.quality_gate.baseline_model_name]
    generated_at = _utc_naive(run.generated_at)
    evaluation_metadata = [
        serialize_evaluation(evaluation) for evaluation in run.evaluations
    ]
    final_model_metadata = serialize_final_model(run.future_forecast)
    quality_metadata = {
        "reasons": run.quality_gate.reasons,
        "thresholds": run.quality_gate.thresholds,
    }
    values = {
        "run_key": run.run_key,
        "pipeline_version": run.configuration.pipeline_version,
        "data_fingerprint": run.data_fingerprint,
        "config_fingerprint": run.config_fingerprint,
        **identifiers,
        "data_start": run.series.index.min().date(),
        "data_end": run.series.index.max().date(),
        "train_start": selected.train_start.date(),
        "train_end": selected.train_end.date(),
        "test_start": selected.test_start.date(),
        "test_end": selected.test_end.date(),
        "test_observations": selected.test_observations,
        "selected_model_name": selected.model_name,
        "selected_model_family": selected.family,
        "baseline_model_name": baseline.model_name,
        "selected_mae": selected.metrics["mae"],
        "selected_rmse": selected.metrics["rmse"],
        "selected_mape_percent": selected.metrics["mape_percent"],
        "baseline_mae": baseline.metrics["mae"],
        "baseline_rmse": baseline.metrics["rmse"],
        "baseline_mape_percent": baseline.metrics["mape_percent"],
        "mae_improvement_percent": run.quality_gate.mae_improvement_percent,
        "interval_coverage_percent": selected.interval_coverage_percent,
        "forecast_horizon": run.configuration.forecast.horizon,
        "confidence_level": run.configuration.forecast.confidence_level,
        "quality_status": "passed" if run.quality_gate.passed else "failed",
        "quality_reasons_json": json.dumps(
            _json_ready(quality_metadata), ensure_ascii=False, sort_keys=True
        ),
        "evaluation_metadata_json": json.dumps(
            evaluation_metadata, ensure_ascii=False, sort_keys=True
        ),
        "final_model_metadata_json": (
            json.dumps(final_model_metadata, ensure_ascii=False, sort_keys=True)
            if final_model_metadata is not None
            else None
        ),
        "generated_at": generated_at,
    }
    connection.execute(
        text(
            """
            INSERT INTO fact_forecast_run (
                run_key, pipeline_version, data_fingerprint, config_fingerprint,
                indicator_id, region_id, source_id, data_start, data_end,
                train_start, train_end, test_start, test_end, test_observations,
                selected_model_name, selected_model_family, baseline_model_name,
                selected_mae, selected_rmse, selected_mape_percent,
                baseline_mae, baseline_rmse, baseline_mape_percent,
                mae_improvement_percent, interval_coverage_percent,
                forecast_horizon, confidence_level, quality_status,
                quality_reasons_json, evaluation_metadata_json,
                final_model_metadata_json, generated_at
            ) VALUES (
                :run_key, :pipeline_version, :data_fingerprint, :config_fingerprint,
                :indicator_id, :region_id, :source_id, :data_start, :data_end,
                :train_start, :train_end, :test_start, :test_end, :test_observations,
                :selected_model_name, :selected_model_family, :baseline_model_name,
                :selected_mae, :selected_rmse, :selected_mape_percent,
                :baseline_mae, :baseline_rmse, :baseline_mape_percent,
                :mae_improvement_percent, :interval_coverage_percent,
                :forecast_horizon, :confidence_level, :quality_status,
                :quality_reasons_json, :evaluation_metadata_json,
                :final_model_metadata_json, :generated_at
            )
            ON DUPLICATE KEY UPDATE
                pipeline_version = VALUES(pipeline_version),
                data_fingerprint = VALUES(data_fingerprint),
                config_fingerprint = VALUES(config_fingerprint),
                indicator_id = VALUES(indicator_id),
                region_id = VALUES(region_id),
                source_id = VALUES(source_id),
                data_start = VALUES(data_start),
                data_end = VALUES(data_end),
                train_start = VALUES(train_start),
                train_end = VALUES(train_end),
                test_start = VALUES(test_start),
                test_end = VALUES(test_end),
                test_observations = VALUES(test_observations),
                selected_model_name = VALUES(selected_model_name),
                selected_model_family = VALUES(selected_model_family),
                baseline_model_name = VALUES(baseline_model_name),
                selected_mae = VALUES(selected_mae),
                selected_rmse = VALUES(selected_rmse),
                selected_mape_percent = VALUES(selected_mape_percent),
                baseline_mae = VALUES(baseline_mae),
                baseline_rmse = VALUES(baseline_rmse),
                baseline_mape_percent = VALUES(baseline_mape_percent),
                mae_improvement_percent = VALUES(mae_improvement_percent),
                interval_coverage_percent = VALUES(interval_coverage_percent),
                forecast_horizon = VALUES(forecast_horizon),
                confidence_level = VALUES(confidence_level),
                generated_at = VALUES(generated_at),
                quality_status = VALUES(quality_status),
                quality_reasons_json = VALUES(quality_reasons_json),
                evaluation_metadata_json = VALUES(evaluation_metadata_json),
                final_model_metadata_json = VALUES(final_model_metadata_json)
            """
        ),
        values,
    )
    forecast_run_id = int(
        connection.execute(
            text(
                "SELECT forecast_run_id FROM fact_forecast_run WHERE run_key = :run_key"
            ),
            {"run_key": run.run_key},
        ).scalar_one()
    )
    connection.execute(
        text("DELETE FROM fact_forecast WHERE forecast_run_id = :forecast_run_id"),
        {"forecast_run_id": forecast_run_id},
    )
    forecast_rows: list[dict[str, object]] = []
    if run.quality_gate.passed:
        if run.future_forecast is None:
            raise RuntimeError(
                "Quality gate lulus tetapi hasil forecast tidak tersedia"
            )
        if run.future_forecast.values["forecast_date"].min() <= run.series.index.max():
            raise RuntimeError("Forecast date harus berada setelah observasi terakhir")
        for row in run.future_forecast.values.itertuples(index=False):
            forecast_rows.append(
                {
                    "forecast_run_id": forecast_run_id,
                    "forecast_date": pd.Timestamp(row.forecast_date).date(),
                    "point_forecast": float(row.point_forecast),
                    "lower_bound": float(row.lower_bound),
                    "upper_bound": float(row.upper_bound),
                    "is_publishable": True,
                    "generated_at": generated_at,
                }
            )
    if forecast_rows:
        connection.execute(
            text(
                """
                INSERT INTO fact_forecast (
                    forecast_run_id, forecast_date, point_forecast,
                    lower_bound, upper_bound, is_publishable, generated_at
                ) VALUES (
                    :forecast_run_id, :forecast_date, :point_forecast,
                    :lower_bound, :upper_bound, :is_publishable, :generated_at
                )
                """
            ),
            forecast_rows,
        )

    connection.execute(
        text("DELETE FROM fact_anomaly_event WHERE forecast_run_id = :forecast_run_id"),
        {"forecast_run_id": forecast_run_id},
    )
    anomaly_rows: list[dict[str, object]] = []
    for row in run.anomalies.events.itertuples(index=False):
        anomaly_rows.append(
            {
                "forecast_run_id": forecast_run_id,
                "observation_date": pd.Timestamp(row.observation_date).date(),
                "observed_value": _optional_float(row.observed_value),
                "value_change": _optional_float(row.change),
                "anomaly_score": _optional_float(row.score),
                "threshold_value": float(row.threshold),
                "anomaly_type": row.anomaly_type,
                "detection_method": row.method,
                "reason": row.reason,
                "detected_at": generated_at,
            }
        )
    if anomaly_rows:
        connection.execute(
            text(
                """
                INSERT INTO fact_anomaly_event (
                    forecast_run_id, observation_date, observed_value, value_change,
                    anomaly_score, threshold_value, anomaly_type, detection_method,
                    reason, detected_at
                ) VALUES (
                    :forecast_run_id, :observation_date, :observed_value,
                    :value_change, :anomaly_score, :threshold_value, :anomaly_type,
                    :detection_method, :reason, :detected_at
                )
                """
            ),
            anomaly_rows,
        )
    return PersistenceResult(
        forecast_run_id=forecast_run_id,
        forecast_rows=len(forecast_rows),
        anomaly_rows=len(anomaly_rows),
    )


def persist_advanced_analytics(
    run: AdvancedAnalyticsRun, engine: Engine | None = None
) -> PersistenceResult:
    active_engine = engine or get_engine()
    with active_engine.begin() as connection:
        return persist_advanced_analytics_connection(run, connection)
