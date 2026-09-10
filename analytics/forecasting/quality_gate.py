from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from analytics.forecasting.config import QualityGateConfiguration
from analytics.forecasting.models import ModelEvaluation


@dataclass(frozen=True)
class QualityGateDecision:
    passed: bool
    selected_model_name: str
    baseline_model_name: str
    mae_improvement_percent: float | None
    reasons: tuple[str, ...]
    thresholds: dict[str, float]


def _best_by_mae(
    evaluations: list[ModelEvaluation], family: str | None = None
) -> ModelEvaluation:
    candidates = [
        evaluation
        for evaluation in evaluations
        if family is None or evaluation.family == family
    ]
    finite = [
        evaluation
        for evaluation in candidates
        if np.isfinite(evaluation.metrics.get("mae", np.nan))
    ]
    if not finite:
        label = family or "model"
        raise ValueError(f"Tidak ada evaluasi MAE valid untuk {label}")
    return min(
        finite,
        key=lambda evaluation: (evaluation.metrics["mae"], evaluation.model_name),
    )


def evaluate_quality_gate(
    evaluations: list[ModelEvaluation],
    configuration: QualityGateConfiguration,
) -> QualityGateDecision:
    baseline = _best_by_mae(evaluations, "baseline")
    advanced_candidates = [
        evaluation for evaluation in evaluations if evaluation.family != "baseline"
    ]
    selected = _best_by_mae(advanced_candidates)
    baseline_mae = baseline.metrics["mae"]
    selected_mae = selected.metrics["mae"]
    reasons: list[str] = []
    improvement: float | None
    if baseline_mae == 0:
        improvement = None
        reasons.append(
            "baseline MAE nol sehingga peningkatan relatif tidak terdefinisi"
        )
    else:
        improvement = 100 * (baseline_mae - selected_mae) / baseline_mae
    if not selected.converged:
        reasons.append("model terpilih tidak konvergen")
    if (
        improvement is not None
        and improvement < configuration.minimum_mae_improvement_percent
    ):
        reasons.append(
            "peningkatan MAE terhadap baseline "
            f"{improvement:.2f}% lebih rendah dari threshold "
            f"{configuration.minimum_mae_improvement_percent:.2f}%"
        )
    mape = selected.metrics.get("mape_percent", np.nan)
    if not np.isfinite(mape) or mape > configuration.maximum_mape_percent:
        reasons.append(
            f"MAPE {mape:.2f}% melebihi threshold "
            f"{configuration.maximum_mape_percent:.2f}%"
        )
    coverage = selected.interval_coverage_percent
    if (
        coverage is None
        or not np.isfinite(coverage)
        or coverage < configuration.minimum_interval_coverage_percent
    ):
        coverage_text = "tidak tersedia" if coverage is None else f"{coverage:.2f}%"
        reasons.append(
            f"coverage interval {coverage_text} lebih rendah dari threshold "
            f"{configuration.minimum_interval_coverage_percent:.2f}%"
        )
    thresholds = {
        "minimum_mae_improvement_percent": (
            configuration.minimum_mae_improvement_percent
        ),
        "maximum_mape_percent": configuration.maximum_mape_percent,
        "minimum_interval_coverage_percent": (
            configuration.minimum_interval_coverage_percent
        ),
    }
    return QualityGateDecision(
        passed=not reasons,
        selected_model_name=selected.model_name,
        baseline_model_name=baseline.model_name,
        mae_improvement_percent=improvement,
        reasons=tuple(reasons),
        thresholds=thresholds,
    )
