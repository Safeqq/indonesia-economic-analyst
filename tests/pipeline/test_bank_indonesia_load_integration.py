import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

from pipelines.load.load_to_mysql import load_bank_indonesia_connection
from pipelines.transform.clean_bank_indonesia_data import clean_bank_indonesia
from pipelines.transform.validate_data import validate
from pipelines.utils.bank_indonesia_config import (
    load_bank_indonesia_configuration,
)
from pipelines.utils.database import get_engine
from tests.pipeline.bank_indonesia_fixtures import extraction_fixture

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 untuk integration test MariaDB",
    ),
]


def test_bank_indonesia_upsert_is_idempotent():
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    configuration = load_bank_indonesia_configuration()
    frame = clean_bank_indonesia(
        extraction_fixture(),
        configuration,
        datetime(2026, 3, 1, tzinfo=UTC),
        date(2026, 1, 1),
        date(2026, 2, 28),
    ).frame
    validate(frame)

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
        )
        for statement in temporary_tables:
            connection.execute(text(statement))

        for _ in range(2):
            result = connection.execute(
                text(
                    """
                    INSERT INTO fact_pipeline_run
                        (source_code, started_at, status)
                    VALUES ('bank_indonesia', CURRENT_TIMESTAMP, 'running')
                    """
                )
            )
            assert (
                load_bank_indonesia_connection(frame, int(result.lastrowid), connection)
                == 4
            )

        fact_count = connection.execute(
            text("SELECT COUNT(*) FROM fact_economic_indicator")
        ).scalar_one()
        statuses = connection.execute(
            text("SELECT status FROM fact_pipeline_run ORDER BY run_id")
        ).scalars()

        assert fact_count == 4
        assert list(statuses) == ["success", "success"]
