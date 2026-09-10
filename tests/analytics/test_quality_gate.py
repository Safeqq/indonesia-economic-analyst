import pandas as pd

from analytics.forecasting.config import QualityGateConfiguration
from analytics.forecasting.models import ModelEvaluation
from analytics.forecasting.quality_gate import evaluate_quality_gate


def _evaluation(
    name: str,
    family: str,
    *,
    mae: float,
    mape: float,
    coverage: float | None,
    converged: bool = True,
) -> ModelEvaluation:
    return ModelEvaluation(
        model_name=name,
        family=family,
        parameters={},
        train_start=pd.Timestamp("2020-01-01"),
        train_end=pd.Timestamp("2022-12-01"),
        test_start=pd.Timestamp("2023-01-01"),
        test_end=pd.Timestamp("2023-12-01"),
        training_observations=36,
        test_observations=12,
        metrics={"mae": mae, "rmse": mae * 1.2, "mape_percent": mape},
        interval_coverage_percent=coverage,
        converged=converged,
        aic=None,
        bic=None,
        warnings=(),
        predictions=pd.DataFrame(),
    )


def _configuration() -> QualityGateConfiguration:
    return QualityGateConfiguration(
        minimum_mae_improvement_percent=5.0,
        maximum_mape_percent=5.0,
        minimum_interval_coverage_percent=70.0,
    )


def test_quality_gate_passes_model_that_beats_best_baseline() -> None:
    evaluations = [
        _evaluation("naive", "baseline", mae=100, mape=4, coverage=None),
        _evaluation("seasonal", "baseline", mae=120, mape=5, coverage=None),
        _evaluation("arima", "arima", mae=85, mape=3, coverage=80),
    ]

    decision = evaluate_quality_gate(evaluations, _configuration())

    assert decision.passed
    assert decision.selected_model_name == "arima"
    assert decision.baseline_model_name == "naive"
    assert decision.mae_improvement_percent == 15.0


def test_quality_gate_withholds_low_quality_model_with_reasons() -> None:
    evaluations = [
        _evaluation("naive", "baseline", mae=100, mape=4, coverage=None),
        _evaluation("arima", "arima", mae=98, mape=6, coverage=60, converged=False),
    ]

    decision = evaluate_quality_gate(evaluations, _configuration())

    assert not decision.passed
    assert len(decision.reasons) == 4
    assert any("konvergen" in reason for reason in decision.reasons)
    assert any("peningkatan MAE" in reason for reason in decision.reasons)
    assert any("MAPE" in reason for reason in decision.reasons)
    assert any("coverage interval" in reason for reason in decision.reasons)
