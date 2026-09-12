from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics.descriptive.data_access import load_eda_data  # noqa: E402
from analytics.forecasting.config import (  # noqa: E402
    load_advanced_analytics_configuration,
)
from analytics.forecasting.reporting import (  # noqa: E402
    save_advanced_analytics_figure,
)
from analytics.forecasting.run import (  # noqa: E402
    AdvancedAnalyticsRun,
    execute_advanced_analytics,
)
from analytics.forecasting.storage import (  # noqa: E402
    PersistenceResult,
    persist_advanced_analytics,
    write_run_artifact,
)


@dataclass(frozen=True)
class AdvancedAnalyticsExecution:
    run: AdvancedAnalyticsRun
    persisted: PersistenceResult
    artifact_path: Path
    figure_path: Path


def execute_and_persist_advanced_analytics(
    engine: Engine | None = None,
) -> AdvancedAnalyticsExecution:
    configuration = load_advanced_analytics_configuration()
    data = load_eda_data(engine)
    run = execute_advanced_analytics(data.monetary, configuration)
    persisted = persist_advanced_analytics(run, engine)
    artifact_path = write_run_artifact(run)
    figure_path = save_advanced_analytics_figure(run)
    return AdvancedAnalyticsExecution(
        run=run,
        persisted=persisted,
        artifact_path=artifact_path,
        figure_path=figure_path,
    )


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        execution = execute_and_persist_advanced_analytics()
    except Exception as error:
        print(f"Advanced analytics gagal: {error}", file=sys.stderr)
        return 1

    run = execution.run
    persisted = execution.persisted
    print("Evaluasi out-of-sample:")
    for evaluation in run.evaluations:
        coverage = (
            "n/a"
            if evaluation.interval_coverage_percent is None
            else f"{evaluation.interval_coverage_percent:.2f}%"
        )
        print(
            f"- {evaluation.model_name}: MAE={evaluation.metrics['mae']:.2f}, "
            f"RMSE={evaluation.metrics['rmse']:.2f}, "
            f"MAPE={evaluation.metrics['mape_percent']:.2f}%, "
            f"interval_coverage={coverage}"
        )
    if run.quality_gate.passed:
        print(
            "[OK] Quality gate lulus. Forecast tersimpan sebagai estimasi model, "
            "bukan fakta observasi."
        )
    else:
        print(
            "[WITHHELD] Forecast tidak dibuat karena quality gate gagal: "
            + "; ".join(run.quality_gate.reasons)
        )
    print(
        f"[OK] forecast_run_id={persisted.forecast_run_id}, "
        f"forecast_rows={persisted.forecast_rows}, "
        f"anomaly_rows={persisted.anomaly_rows}"
    )
    print(f"Artifact metadata: {execution.artifact_path}")
    print(f"Laporan visual: {execution.figure_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
