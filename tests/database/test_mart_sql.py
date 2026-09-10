from scripts.build_marts import MART_SQL_FILES
from scripts.check_data_quality import (
    BLOCKING_CHECK_FILES,
    INFORMATIONAL_CHECK_FILES,
)


def test_all_required_mart_files_are_registered():
    assert {path.name for path in MART_SQL_FILES} == {
        "stg_world_bank.sql",
        "mart_national_overview.sql",
        "mart_indicator_trends.sql",
        "mart_asean_comparison.sql",
    }
    for path in MART_SQL_FILES:
        sql = path.read_text(encoding="utf-8")
        assert sql.startswith("-- Grain:")
        assert "CREATE OR REPLACE VIEW" in sql


def test_marts_use_required_analytical_sql_features():
    combined_sql = "\n".join(
        path.read_text(encoding="utf-8").upper() for path in MART_SQL_FILES
    )

    for feature in (
        " JOIN ",
        "GROUP BY",
        "WITH ",
        " OVER ",
        "LAG(",
        "LEAD(",
        "ROWS BETWEEN 2 PRECEDING AND CURRENT ROW",
        "YOY_PERCENT_CHANGE",
        "RANK()",
        "PERCENT_RANK()",
        "CASE",
    ):
        assert feature in combined_sql


def test_all_required_quality_checks_are_registered():
    registered = {
        path.name for path in BLOCKING_CHECK_FILES + INFORMATIONAL_CHECK_FILES
    }
    assert {
        "check_duplicates.sql",
        "check_missing_mandatory_fields.sql",
        "check_value_ranges.sql",
        "check_data_freshness.sql",
        "check_latest_pipeline_failure.sql",
        "check_missing_periods.sql",
        "check_stg_world_bank_grain.sql",
        "check_mart_national_overview_grain.sql",
        "check_mart_indicator_trends_grain.sql",
        "check_mart_asean_comparison_grain.sql",
    } == registered
