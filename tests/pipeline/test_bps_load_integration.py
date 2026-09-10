import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

from pipelines.load.load_to_mysql import load_bps_connection
from pipelines.transform.clean_bps_data import clean_bps, validate_bps_metadata
from pipelines.transform.validate_data import validate
from pipelines.utils.database import get_engine
from tests.pipeline.bps_fixtures import (
    configuration,
    extraction,
    province_configuration,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 untuk integration test MariaDB",
    ),
]


def test_bps_upsert_is_idempotent_and_preserves_metadata_versions():
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    first = clean_bps(
        extraction(second_variable_unit="Persen"),
        configuration(),
        province_configuration(),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    changed = clean_bps(
        extraction(second_variable_unit="Poin"),
        configuration(),
        province_configuration(),
        datetime(2026, 2, 1, tzinfo=UTC),
    )
    for cleaned in (first, changed):
        validate(cleaned.frame)
        validate_bps_metadata(cleaned.metadata, cleaned.frame)

    engine = get_engine()
    with engine.begin() as connection:
        temporary_tables = (
            """
            CREATE TEMPORARY TABLE dim_source (
                source_id INT AUTO_INCREMENT PRIMARY KEY,
                source_code VARCHAR(50) NOT NULL UNIQUE,
                source_name VARCHAR(150) NOT NULL,
                source_url VARCHAR(500) NOT NULL
            )
            """,
            """
            CREATE TEMPORARY TABLE dim_indicator (
                indicator_id INT AUTO_INCREMENT PRIMARY KEY,
                indicator_code VARCHAR(100) NOT NULL UNIQUE,
                indicator_name VARCHAR(255) NOT NULL,
                unit VARCHAR(100),
                frequency ENUM('daily', 'monthly', 'quarterly', 'annual') NOT NULL
            )
            """,
            """
            CREATE TEMPORARY TABLE dim_region (
                region_id INT AUTO_INCREMENT PRIMARY KEY,
                region_code VARCHAR(50) NOT NULL UNIQUE,
                region_name VARCHAR(150) NOT NULL,
                region_level ENUM('country', 'province', 'city') NOT NULL,
                parent_region_code VARCHAR(50)
            )
            """,
            """
            CREATE TEMPORARY TABLE dim_date (
                date_id INT PRIMARY KEY,
                full_date DATE NOT NULL UNIQUE,
                year SMALLINT NOT NULL,
                quarter TINYINT NOT NULL,
                month TINYINT NOT NULL
            )
            """,
            """
            CREATE TEMPORARY TABLE fact_economic_indicator (
                observation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                indicator_id INT NOT NULL,
                region_id INT NOT NULL,
                source_id INT NOT NULL,
                observation_date DATE NOT NULL,
                value DECIMAL(24, 6) NOT NULL,
                ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_observation
                    (indicator_id, region_id, source_id, observation_date)
            )
            """,
            """
            CREATE TEMPORARY TABLE fact_pipeline_run (
                run_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                source_code VARCHAR(50) NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP NULL,
                status ENUM('running', 'success', 'failed') NOT NULL,
                rows_loaded INT NOT NULL DEFAULT 0,
                error_message TEXT
            )
            """,
            """
            CREATE TEMPORARY TABLE dim_indicator_metadata_history (
                metadata_version_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                indicator_id INT NOT NULL,
                source_id INT NOT NULL,
                source_variable_id VARCHAR(50) NOT NULL,
                derived_variable_id VARCHAR(50) NOT NULL,
                derived_period_id VARCHAR(50) NOT NULL,
                indicator_name VARCHAR(255) NOT NULL,
                unit VARCHAR(100) NOT NULL,
                definition_text TEXT,
                notes TEXT,
                metadata_hash CHAR(64) NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                first_observed_at TIMESTAMP NOT NULL,
                last_observed_at TIMESTAMP NOT NULL,
                UNIQUE KEY uq_indicator_metadata_version
                    (indicator_id, source_id, metadata_hash)
            )
            """,
        )
        for statement in temporary_tables:
            connection.execute(text(statement))

        for cleaned in (first, first, changed):
            result = connection.execute(
                text(
                    """
                    INSERT INTO fact_pipeline_run
                        (source_code, started_at, status)
                    VALUES ('bps', CURRENT_TIMESTAMP, 'running')
                    """
                )
            )
            assert (
                load_bps_connection(
                    cleaned.frame,
                    cleaned.metadata,
                    int(result.lastrowid),
                    connection,
                )
                == 4
            )

        fact_count = connection.execute(
            text("SELECT COUNT(*) FROM fact_economic_indicator")
        ).scalar_one()
        metadata_count = connection.execute(
            text("SELECT COUNT(*) FROM dim_indicator_metadata_history")
        ).scalar_one()
        run_statuses = connection.execute(
            text("SELECT status FROM fact_pipeline_run ORDER BY run_id")
        ).scalars()

        assert fact_count == 4
        assert metadata_count == 3
        assert list(run_statuses) == ["success", "success", "success"]
