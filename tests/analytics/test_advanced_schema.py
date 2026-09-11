from pipelines.utils.data_quality import (
    BLOCKING_CHECK_FILES,
    INFORMATIONAL_CHECK_FILES,
)
from scripts.apply_schema import SCHEMA_FILES


def test_advanced_analytics_schema_is_registered() -> None:
    filenames = {path.name for path in SCHEMA_FILES}
    assert "06_create_advanced_analytics.sql" in filenames
    schema = next(
        path for path in SCHEMA_FILES if path.name == "06_create_advanced_analytics.sql"
    ).read_text(encoding="utf-8")

    for table in ("fact_forecast_run", "fact_forecast", "fact_anomaly_event"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
    assert "quality_status ENUM('passed', 'failed')" in schema
    assert "source_revision" in schema
    assert "economic_anomaly" in schema


def test_advanced_quality_queries_are_registered() -> None:
    blocking = {path.name for path in BLOCKING_CHECK_FILES}
    informational = {path.name for path in INFORMATIONAL_CHECK_FILES}

    assert "check_forecast_integrity.sql" in blocking
    assert "check_anomaly_integrity.sql" in blocking
    assert "check_latest_forecast_run.sql" in informational
