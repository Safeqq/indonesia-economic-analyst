from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics.descriptive.data_access import load_eda_data  # noqa: E402
from analytics.forecasting.config import (  # noqa: E402
    load_advanced_analytics_configuration,
)
from analytics.forecasting.models import prepare_regular_series  # noqa: E402
from analytics.forecasting.run import (  # noqa: E402
    fingerprint_configuration,
    fingerprint_series,
)
from pipelines.utils.database import get_engine  # noqa: E402


def verify_advanced_analytics() -> None:
    configuration = load_advanced_analytics_configuration()
    forecast_configuration = configuration.forecast
    engine = get_engine()
    current_data = load_eda_data(engine)
    current_series = prepare_regular_series(
        current_data.monetary,
        date_column=forecast_configuration.date_column,
        value_column=forecast_configuration.value_column,
        frequency=forecast_configuration.frequency,
    )
    with engine.connect() as connection:
        run = (
            connection.execute(
                text(
                    """
                SELECT
                    fr.*,
                    i.indicator_code,
                    r.region_code,
                    s.source_code
                FROM fact_forecast_run AS fr
                JOIN dim_indicator AS i ON i.indicator_id = fr.indicator_id
                JOIN dim_region AS r ON r.region_id = fr.region_id
                JOIN dim_source AS s ON s.source_id = fr.source_id
                WHERE i.indicator_code = :indicator_code
                  AND r.region_code = :region_code
                  AND s.source_code = :source_code
                ORDER BY fr.generated_at DESC, fr.forecast_run_id DESC
                LIMIT 1
                    """
                ),
                {
                    "indicator_code": forecast_configuration.indicator_code,
                    "region_code": forecast_configuration.region_code,
                    "source_code": forecast_configuration.source_code,
                },
            )
            .mappings()
            .one_or_none()
        )
        if run is None:
            raise RuntimeError("Belum ada advanced analytics run untuk diverifikasi")
        forecasts = (
            connection.execute(
                text(
                    """
                SELECT forecast_date, point_forecast, lower_bound, upper_bound,
                       is_publishable
                FROM fact_forecast
                WHERE forecast_run_id = :forecast_run_id
                ORDER BY forecast_date
                    """
                ),
                {"forecast_run_id": run["forecast_run_id"]},
            )
            .mappings()
            .all()
        )
        anomalies = (
            connection.execute(
                text(
                    """
                SELECT observation_date, anomaly_type, reason
                FROM fact_anomaly_event
                WHERE forecast_run_id = :forecast_run_id
                ORDER BY observation_date, anomaly_type
                    """
                ),
                {"forecast_run_id": run["forecast_run_id"]},
            )
            .mappings()
            .all()
        )

    evaluations = json.loads(run["evaluation_metadata_json"])
    if run["pipeline_version"] != configuration.pipeline_version:
        raise RuntimeError("Versi pipeline run tidak sesuai konfigurasi aktif")
    if run["config_fingerprint"] != fingerprint_configuration(configuration):
        raise RuntimeError("Konfigurasi berubah; jalankan ulang advanced analytics")
    if run["data_fingerprint"] != fingerprint_series(current_series):
        raise RuntimeError("Data berubah; jalankan ulang advanced analytics")
    if pd.Timestamp(run["data_end"]) != current_series.index.max():
        raise RuntimeError("Periode akhir run tidak sesuai data saat ini")
    families = {item["family"] for item in evaluations}
    if "baseline" not in families or not {"arima", "sarima"}.issubset(families):
        raise RuntimeError("Evaluasi wajib membandingkan baseline, ARIMA, dan SARIMA")
    if run["test_start"] <= run["train_end"]:
        raise RuntimeError("Train/test split tidak mengikuti urutan waktu")
    if int(run["test_observations"]) != forecast_configuration.test_periods:
        raise RuntimeError("Jumlah observasi holdout tidak sesuai konfigurasi")
    for evaluation in evaluations:
        if evaluation["train_end"] >= evaluation["test_start"]:
            raise RuntimeError("Metadata evaluasi memiliki train/test yang overlap")
        if int(evaluation["test_observations"]) != forecast_configuration.test_periods:
            raise RuntimeError("Metadata evaluasi memiliki ukuran holdout yang salah")
        if len(evaluation["predictions"]) != forecast_configuration.test_periods:
            raise RuntimeError("Prediksi out-of-sample tidak lengkap")
        if evaluation["family"] != "baseline":
            if evaluation["interval_coverage_percent"] is None:
                raise RuntimeError("Model lanjutan tidak memiliki interval coverage")
            if any(
                not item["lower_bound"] <= item["prediction"] <= item["upper_bound"]
                for item in evaluation["predictions"]
            ):
                raise RuntimeError("Prediksi holdout berada di luar interval")
    if any(not str(item["reason"]).strip() for item in anomalies):
        raise RuntimeError("Anomaly event ditemukan tanpa alasan")

    if run["quality_status"] == "passed":
        gate = forecast_configuration.quality_gate
        if len(forecasts) != forecast_configuration.horizon:
            raise RuntimeError("Jumlah forecast tidak sesuai horizon")
        if any(not row["is_publishable"] for row in forecasts):
            raise RuntimeError("Forecast yang lulus gate harus publishable")
        if any(row["forecast_date"] <= run["data_end"] for row in forecasts):
            raise RuntimeError("Forecast date bukan periode masa depan")
        if any(
            not row["lower_bound"] <= row["point_forecast"] <= row["upper_bound"]
            for row in forecasts
        ):
            raise RuntimeError("Point forecast berada di luar confidence interval")
        if float(run["mae_improvement_percent"]) < gate.minimum_mae_improvement_percent:
            raise RuntimeError("Run lulus tanpa memenuhi threshold peningkatan MAE")
        if float(run["selected_mape_percent"]) > gate.maximum_mape_percent:
            raise RuntimeError("Run lulus tanpa memenuhi threshold MAPE")
        if (
            float(run["interval_coverage_percent"])
            < gate.minimum_interval_coverage_percent
        ):
            raise RuntimeError("Run lulus tanpa memenuhi threshold interval coverage")
        if run["final_model_metadata_json"] is None:
            raise RuntimeError("Metadata model final tidak tersimpan")
    else:
        if forecasts:
            raise RuntimeError("Forecast tersimpan meskipun quality gate gagal")
        if run["final_model_metadata_json"] is not None:
            raise RuntimeError("Model final tersimpan meskipun quality gate gagal")

    print(
        f"[OK] Run {run['forecast_run_id']}: {run['selected_model_name']} vs "
        f"{run['baseline_model_name']}, holdout {run['test_start']} sampai "
        f"{run['test_end']}"
    )
    print(
        f"[OK] Quality gate={run['quality_status']}; "
        f"MAE improvement={run['mae_improvement_percent']}%; "
        f"forecast={len(forecasts)}, anomaly={len(anomalies)}"
    )
    if run["quality_status"] == "passed":
        print("[OK] Forecast tersimpan sebagai estimasi dengan confidence interval")
    else:
        print("[OK] Forecast ditahan dan alasan quality gate tersimpan")


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        verify_advanced_analytics()
    except Exception as error:
        print(f"Verifikasi advanced analytics gagal: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
