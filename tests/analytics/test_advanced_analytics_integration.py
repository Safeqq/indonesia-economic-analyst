import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

from analytics.descriptive.data_access import load_eda_data
from analytics.forecasting.config import load_advanced_analytics_configuration
from analytics.forecasting.run import execute_advanced_analytics
from analytics.forecasting.storage import persist_advanced_analytics
from pipelines.utils.database import get_engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 untuk integration test MariaDB",
    ),
]


def test_advanced_analytics_persistence_is_idempotent() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    engine = get_engine()
    configuration = load_advanced_analytics_configuration()
    data = load_eda_data(engine)
    run = execute_advanced_analytics(data.monetary, configuration)

    first = persist_advanced_analytics(run, engine)
    second = persist_advanced_analytics(run, engine)

    assert first.forecast_run_id == second.forecast_run_id
    expected_forecasts = (
        configuration.forecast.horizon if run.quality_gate.passed else 0
    )
    assert first.forecast_rows == expected_forecasts
    with engine.connect() as connection:
        stored_runs = connection.execute(
            text("SELECT COUNT(*) FROM fact_forecast_run WHERE run_key = :run_key"),
            {"run_key": run.run_key},
        ).scalar_one()
        stored_forecasts = connection.execute(
            text(
                "SELECT COUNT(*) FROM fact_forecast "
                "WHERE forecast_run_id = :forecast_run_id"
            ),
            {"forecast_run_id": first.forecast_run_id},
        ).scalar_one()
        metadata = connection.execute(
            text(
                "SELECT evaluation_metadata_json FROM fact_forecast_run "
                "WHERE forecast_run_id = :forecast_run_id"
            ),
            {"forecast_run_id": first.forecast_run_id},
        ).scalar_one()

    assert stored_runs == 1
    assert stored_forecasts == expected_forecasts
    families = {item["family"] for item in json.loads(metadata)}
    assert {"baseline", "arima", "sarima"}.issubset(families)
