from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIRECTORY = PROJECT_ROOT / "data" / "exports" / "advanced_analytics"
MPL_CACHE_DIRECTORY = PROJECT_ROOT / "data" / "exports" / ".matplotlib"
MPL_CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIRECTORY))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from analytics.forecasting.run import AdvancedAnalyticsRun  # noqa: E402


def save_advanced_analytics_figure(
    run: AdvancedAnalyticsRun,
    directory: Path = DEFAULT_REPORT_DIRECTORY,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(2, 1, figsize=(12, 11))
    names = [evaluation.model_name for evaluation in run.evaluations]
    mae_values = [evaluation.metrics["mae"] for evaluation in run.evaluations]
    colors = [
        "tab:green"
        if name == run.quality_gate.selected_model_name
        else "tab:blue"
        if evaluation.family == "baseline"
        else "tab:orange"
        for name, evaluation in zip(names, run.evaluations, strict=True)
    ]
    axes[0].bar(names, mae_values, color=colors)
    axes[0].set(title="MAE out-of-sample per model", ylabel="MAE (IDR per USD)")
    axes[0].tick_params(axis="x", rotation=20)

    history = run.series.tail(42)
    axes[1].plot(history.index, history.values, color="black", label="Observasi resmi")
    if run.future_forecast is not None:
        forecast = run.future_forecast.values
        forecast_dates = forecast["forecast_date"]
        point = forecast["point_forecast"].to_numpy(dtype=float)
        lower = forecast["lower_bound"].to_numpy(dtype=float)
        upper = forecast["upper_bound"].to_numpy(dtype=float)
        axes[1].plot(
            forecast_dates,
            point,
            color="tab:red",
            marker="o",
            label="Estimasi model",
        )
        axes[1].fill_between(
            forecast_dates,
            lower,
            upper,
            color="tab:red",
            alpha=0.2,
            label=(f"Interval {run.configuration.forecast.confidence_level:.0%}"),
        )
        axes[1].axvline(
            run.series.index.max(), color="grey", linestyle=":", label="Batas data"
        )
        title = "Estimasi JISDOR dengan confidence interval — bukan fakta"
    else:
        reason = "; ".join(run.quality_gate.reasons)
        axes[1].text(
            0.5,
            0.5,
            f"Forecast ditahan oleh quality gate\n{reason}",
            ha="center",
            va="center",
            transform=axes[1].transAxes,
            wrap=True,
        )
        title = "Forecast ditahan oleh quality gate"
    axes[1].set(title=title, xlabel="Bulan", ylabel="IDR per USD")
    axes[1].legend()
    finite_mae = [value for value in mae_values if np.isfinite(value)]
    if not finite_mae:
        raise RuntimeError("Tidak ada MAE finite untuk laporan advanced analytics")
    figure.tight_layout()
    destination = directory / f"advanced_analytics_{run.run_key[:16]}.png"
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return destination
