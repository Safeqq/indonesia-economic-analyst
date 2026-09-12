from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

from pipelines.utils.database import get_engine
from pipelines.utils.freshness import (
    FreshnessFinding,
    FreshnessReport,
    SourceFreshnessSnapshot,
    persist_freshness_report_connection,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 untuk integration test MariaDB",
    ),
]


def test_freshness_alert_upsert_and_resolution_are_idempotent() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    engine = get_engine()
    checked_at = datetime(2026, 9, 12, tzinfo=UTC)
    snapshot = SourceFreshnessSnapshot("test_source", None, None, None)
    finding = FreshnessFinding(
        source_code="test_source",
        alert_type="missing_observations",
        severity="critical",
        message="Fixture integration test",
        last_success_at=None,
        last_ingested_at=None,
        latest_observation_date=None,
    )
    alert_report = FreshnessReport(checked_at, (snapshot,), (finding,))
    healthy_report = FreshnessReport(checked_at, (snapshot,), ())

    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    """
                    CREATE TEMPORARY TABLE data_freshness_alert (
                        alert_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        alert_key CHAR(64) NOT NULL UNIQUE,
                        source_code VARCHAR(50) NOT NULL,
                        alert_type VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) NOT NULL,
                        message TEXT NOT NULL,
                        last_success_at DATETIME NULL,
                        last_ingested_at DATETIME NULL,
                        latest_observation_date DATE NULL,
                        first_detected_at DATETIME NOT NULL,
                        last_detected_at DATETIME NOT NULL,
                        resolved_at DATETIME NULL
                    )
                    """
                )
            )
            persist_freshness_report_connection(alert_report, connection)
            persist_freshness_report_connection(alert_report, connection)
            assert (
                connection.execute(
                    text("SELECT COUNT(*) FROM data_freshness_alert")
                ).scalar_one()
                == 1
            )

            persist_freshness_report_connection(healthy_report, connection)
            assert (
                connection.execute(
                    text(
                        "SELECT resolved_at FROM data_freshness_alert "
                        "WHERE alert_key = :alert_key"
                    ),
                    {"alert_key": finding.alert_key},
                ).scalar_one()
                is not None
            )
    finally:
        engine.dispose()
