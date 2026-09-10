from pathlib import Path

import pytest

from analytics.forecasting.config import (
    DEFAULT_ADVANCED_ANALYTICS_CONFIG,
    load_advanced_analytics_configuration,
)


def test_default_advanced_analytics_config_is_complete() -> None:
    configuration = load_advanced_analytics_configuration()

    assert configuration.pipeline_version == "phase6-v1"
    assert configuration.forecast.indicator_code == "BI.JISDOR.USD_IDR.MONTHLY_AVG"
    assert configuration.forecast.baseline_lags == (1, 12)
    assert {model.family for model in configuration.forecast.candidate_models} == {
        "arima",
        "sarima",
    }
    assert configuration.forecast.quality_gate.minimum_mae_improvement_percent > 0
    assert configuration.anomaly_detection.minimum_history <= (
        configuration.anomaly_detection.window
    )


def test_invalid_confidence_level_is_rejected(tmp_path: Path) -> None:
    content = DEFAULT_ADVANCED_ANALYTICS_CONFIG.read_text(encoding="utf-8")
    path = tmp_path / "invalid.yml"
    path.write_text(content.replace("confidence_level: 0.95", "confidence_level: 1"))

    with pytest.raises(ValueError, match="confidence_level"):
        load_advanced_analytics_configuration(path)


def test_missing_baseline_list_is_rejected(tmp_path: Path) -> None:
    content = DEFAULT_ADVANCED_ANALYTICS_CONFIG.read_text(encoding="utf-8")
    path = tmp_path / "invalid.yml"
    path.write_text(
        content.replace("baseline_lags:\n    - 1\n    - 12", "baseline_lags:")
    )

    with pytest.raises(ValueError, match="baseline_lags"):
        load_advanced_analytics_configuration(path)


def test_candidate_name_cannot_collide_with_baseline(tmp_path: Path) -> None:
    content = DEFAULT_ADVANCED_ANALYTICS_CONFIG.read_text(encoding="utf-8")
    path = tmp_path / "invalid.yml"
    path.write_text(content.replace("name: arima_011_drift", "name: naive_lag_1"))

    with pytest.raises(ValueError, match="bertabrakan"):
        load_advanced_analytics_configuration(path)
