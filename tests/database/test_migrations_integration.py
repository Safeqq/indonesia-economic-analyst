from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import inspect, text

from pipelines.utils.database import get_engine
from scripts.apply_migrations import apply_migrations, discover_migrations

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 untuk integration test MariaDB",
    ),
]


def test_migrations_are_recorded_and_idempotent() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    engine = get_engine()
    try:
        apply_migrations(engine)
        second = apply_migrations(engine)
        expected_versions = {item.version for item in discover_migrations()}

        assert second.applied == ()
        assert set(second.skipped) == expected_versions
        assert {
            "schema_migration",
            "data_freshness_alert",
            "pipeline_schedule_run",
        }.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            recorded = set(
                connection.execute(
                    text("SELECT version FROM schema_migration")
                ).scalars()
            )
            timezone_offset = connection.execute(
                text("SELECT TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW())")
            ).scalar_one()
        assert expected_versions.issubset(recorded)
        assert timezone_offset == 0
    finally:
        engine.dispose()
