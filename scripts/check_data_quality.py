from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.utils.database import get_engine  # noqa: E402

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
)
INFORMATIONAL_CHECK_FILES = (
    QUALITY_DIRECTORY / "check_data_freshness.sql",
    QUALITY_DIRECTORY / "check_missing_periods.sql",
    QUALITY_DIRECTORY / "check_bps_missing_periods.sql",
    QUALITY_DIRECTORY / "check_bi_missing_periods.sql",
)


@dataclass(frozen=True)
class QualityResult:
    name: str
    blocking: bool
    rows: tuple[dict[str, object], ...]


def run_quality_checks(engine: Engine | None = None) -> tuple[QualityResult, ...]:
    engine = engine or get_engine()
    checks = tuple((path, True) for path in BLOCKING_CHECK_FILES) + tuple(
        (path, False) for path in INFORMATIONAL_CHECK_FILES
    )
    results: list[QualityResult] = []
    with engine.connect() as connection:
        for sql_file, blocking in checks:
            statement = sql_file.read_text(encoding="utf-8")
            mappings = connection.exec_driver_sql(statement).mappings()
            rows = tuple(dict(row) for row in mappings)
            results.append(
                QualityResult(name=sql_file.stem, blocking=blocking, rows=rows)
            )
    return tuple(results)


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    failed = False
    for result in run_quality_checks():
        if result.blocking and result.rows:
            failed = True
            label = "FAIL"
        elif result.blocking:
            label = "OK"
        else:
            label = "INFO"
        print(f"[{label}] {result.name}: {len(result.rows)} baris")
        if result.rows:
            for row in result.rows[:3]:
                print(f"  {row}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
