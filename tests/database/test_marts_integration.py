import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import inspect, text

from pipelines.utils.database import get_engine
from scripts.build_marts import build_marts
from scripts.check_data_quality import (
    BLOCKING_CHECK_FILES,
    INFORMATIONAL_CHECK_FILES,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 untuk integration test MariaDB",
    ),
]

EXPECTED_VIEWS = {
    "stg_world_bank",
    "stg_bps",
    "stg_bank_indonesia",
    "mart_national_overview",
    "mart_indicator_trends",
    "mart_asean_comparison",
    "mart_regional_analysis",
    "mart_monetary_conditions",
}


@pytest.fixture(scope="module")
def engine():
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    return get_engine()


def test_marts_build_and_have_expected_grain(engine):
    assert set(build_marts(engine)) == EXPECTED_VIEWS
    assert EXPECTED_VIEWS.issubset(inspect(engine).get_view_names())

    grain_checks = (
        "check_stg_world_bank_grain.sql",
        "check_stg_bps_grain.sql",
        "check_stg_bank_indonesia_grain.sql",
        "check_mart_national_overview_grain.sql",
        "check_mart_indicator_trends_grain.sql",
        "check_mart_asean_comparison_grain.sql",
        "check_mart_regional_analysis_grain.sql",
        "check_mart_monetary_conditions_grain.sql",
    )
    quality_directory = Path(__file__).resolve().parents[2] / "sql" / "quality"
    with engine.connect() as connection:
        for filename in grain_checks:
            sql = (quality_directory / filename).read_text(encoding="utf-8")
            assert connection.exec_driver_sql(sql).all() == []


def test_marts_contain_real_world_bank_observations(engine):
    with engine.connect() as connection:
        staging_count = connection.execute(
            text("SELECT COUNT(*) FROM stg_world_bank")
        ).scalar_one()
        trend_count = connection.execute(
            text("SELECT COUNT(*) FROM mart_indicator_trends")
        ).scalar_one()
        national_coverage = connection.execute(
            text("SELECT MAX(indicator_coverage) FROM mart_national_overview")
        ).scalar_one()
        asean_country_count = connection.execute(
            text("SELECT COUNT(DISTINCT region_code) FROM mart_asean_comparison")
        ).scalar_one()

    assert staging_count > 0
    assert trend_count == staging_count
    assert national_coverage >= 4
    assert asean_country_count == 11


def test_quality_queries_execute_against_marts(engine):
    with engine.connect() as connection:
        for sql_file in BLOCKING_CHECK_FILES + INFORMATIONAL_CHECK_FILES:
            result = connection.exec_driver_sql(sql_file.read_text(encoding="utf-8"))
            result.fetchmany(1)


def test_bank_indonesia_mart_combines_two_real_monthly_series(engine):
    with engine.connect() as connection:
        staging_count = connection.execute(
            text("SELECT COUNT(*) FROM stg_bank_indonesia")
        ).scalar_one()
        mart_count = connection.execute(
            text("SELECT COUNT(*) FROM mart_monetary_conditions")
        ).scalar_one()
        incomplete = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM mart_monetary_conditions
                WHERE bi_rate_percent IS NULL
                   OR jisdor_idr_per_usd IS NULL
                   OR indicator_coverage <> 2
                """
            )
        ).scalar_one()

    assert staging_count > 0
    assert mart_count * 2 == staging_count
    assert incomplete == 0
