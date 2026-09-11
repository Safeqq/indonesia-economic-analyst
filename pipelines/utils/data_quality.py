from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine

from pipelines.utils.database import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUALITY_DIRECTORY = PROJECT_ROOT / "sql" / "quality"

BLOCKING_CHECK_FILES = (
    QUALITY_DIRECTORY / "check_duplicates.sql",
    QUALITY_DIRECTORY / "check_missing_mandatory_fields.sql",
    QUALITY_DIRECTORY / "check_value_ranges.sql",
    QUALITY_DIRECTORY / "check_latest_pipeline_failure.sql",
    QUALITY_DIRECTORY / "check_stg_world_bank_grain.sql",
    QUALITY_DIRECTORY / "check_stg_bps_grain.sql",
    QUALITY_DIRECTORY / "check_stg_bank_indonesia_grain.sql",
    QUALITY_DIRECTORY / "check_bps_missing_mandatory_fields.sql",
    QUALITY_DIRECTORY / "check_bps_region_codes.sql",
    QUALITY_DIRECTORY / "check_bps_metadata_history.sql",
    QUALITY_DIRECTORY / "check_bps_value_ranges.sql",
    QUALITY_DIRECTORY / "check_bi_missing_mandatory_fields.sql",
    QUALITY_DIRECTORY / "check_bi_value_ranges.sql",
    QUALITY_DIRECTORY / "check_bi_monthly_coverage.sql",
    QUALITY_DIRECTORY / "check_mart_national_overview_grain.sql",
    QUALITY_DIRECTORY / "check_mart_indicator_trends_grain.sql",
    QUALITY_DIRECTORY / "check_mart_asean_comparison_grain.sql",
    QUALITY_DIRECTORY / "check_mart_regional_analysis_grain.sql",
    QUALITY_DIRECTORY / "check_mart_monetary_conditions_grain.sql",
    QUALITY_DIRECTORY / "check_forecast_integrity.sql",
    QUALITY_DIRECTORY / "check_anomaly_integrity.sql",
)

INFORMATIONAL_CHECK_FILES = (
    QUALITY_DIRECTORY / "check_data_freshness.sql",
    QUALITY_DIRECTORY / "check_missing_periods.sql",
    QUALITY_DIRECTORY / "check_bps_missing_periods.sql",
    QUALITY_DIRECTORY / "check_bi_missing_periods.sql",
    QUALITY_DIRECTORY / "check_latest_forecast_run.sql",
)


@dataclass(frozen=True)
class QualityResult:
    name: str
    blocking: bool
    rows: tuple[dict[str, object], ...]


def run_quality_checks(engine: Engine | None = None) -> tuple[QualityResult, ...]:
    owns_engine = engine is None
    active_engine = engine or get_engine()
    checks = tuple((path, True) for path in BLOCKING_CHECK_FILES) + tuple(
        (path, False) for path in INFORMATIONAL_CHECK_FILES
    )
    results: list[QualityResult] = []
    try:
        with active_engine.connect() as connection:
            for sql_file, blocking in checks:
                statement = sql_file.read_text(encoding="utf-8")
                mappings = connection.exec_driver_sql(statement).mappings()
                rows = tuple(dict(row) for row in mappings)
                results.append(
                    QualityResult(name=sql_file.stem, blocking=blocking, rows=rows)
                )
    finally:
        if owns_engine:
            active_engine.dispose()
    return tuple(results)
