from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests

import pipelines.jobs.run_scheduled_pipelines as scheduled_job
from pipelines.utils.automation import (
    SourceAutomation,
    is_source_due,
    latest_successful_runs,
    load_automation_configuration,
    run_with_retry,
    scheduled_period,
)


def source(
    frequency: str,
    *,
    day: int,
    month: int | None = None,
    options: dict[str, object] | None = None,
) -> SourceAutomation:
    return SourceAutomation(
        source_code="test_source",
        frequency=frequency,  # type: ignore[arg-type]
        run_after_day=day,
        run_after_month=month,
        max_ingestion_age_hours=100,
        max_observation_lag_days=100,
        pipeline_options=options or {},
    )


def test_project_automation_configuration_covers_all_production_sources() -> None:
    configuration = load_automation_configuration()

    assert configuration.timezone == "Asia/Jakarta"
    assert set(configuration.sources) == {
        "world_bank",
        "bps",
        "bank_indonesia",
    }
    assert configuration.sources["bps"].credential_environment == "BPS_API_KEY"
    assert configuration.sources["world_bank"].pipeline_options == {
        "countries": [
            "BRN",
            "KHM",
            "IDN",
            "LAO",
            "MYS",
            "MMR",
            "PHL",
            "SGP",
            "THA",
            "TLS",
            "VNM",
        ],
        "start_year": 2000,
    }


def test_schedule_cadence_only_uses_completed_scheduler_runs() -> None:
    completed_at = datetime(2026, 9, 5, tzinfo=UTC)
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value = (
        {
            "source_code": "bank_indonesia",
            "completed_at": completed_at,
        },
    )

    result = latest_successful_runs(engine)
    query = str(connection.execute.call_args.args[0])

    assert result == {"bank_indonesia": completed_at}
    assert "pipeline_schedule_run" in query
    assert "fact_pipeline_run" not in query


def test_monthly_schedule_waits_for_configured_day_and_runs_once() -> None:
    schedule = source("monthly", day=5)

    assert not is_source_due(
        schedule, None, datetime(2026, 9, 4, 12, tzinfo=UTC), "Asia/Jakarta"
    )
    assert is_source_due(
        schedule,
        datetime(2026, 8, 5, tzinfo=UTC),
        datetime(2026, 9, 5, 12, tzinfo=UTC),
        "Asia/Jakarta",
    )
    assert not is_source_due(
        schedule,
        datetime(2026, 9, 5, 1, tzinfo=UTC),
        datetime(2026, 9, 10, tzinfo=UTC),
        "Asia/Jakarta",
    )
    assert (
        scheduled_period(
            schedule, datetime(2026, 9, 10, tzinfo=UTC), "Asia/Jakarta"
        ).isoformat()
        == "2026-09-01"
    )


def test_annual_schedule_uses_release_boundary() -> None:
    schedule = source("annual", day=15, month=7)

    assert not is_source_due(
        schedule, None, datetime(2026, 7, 14, tzinfo=UTC), "Asia/Jakarta"
    )
    assert is_source_due(
        schedule,
        datetime(2025, 8, 1, tzinfo=UTC),
        datetime(2026, 7, 16, tzinfo=UTC),
        "Asia/Jakarta",
    )
    assert not is_source_due(
        schedule,
        datetime(2026, 7, 16, tzinfo=UTC),
        datetime(2026, 8, 1, tzinfo=UTC),
        "Asia/Jakarta",
    )


def test_retry_only_repeats_transient_failures() -> None:
    attempts = 0
    delays: list[float] = []

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise requests.Timeout("sementara")
        return "ok"

    result = run_with_retry(
        operation,
        attempts=3,
        base_delay_seconds=2,
        sleep=delays.append,
    )

    assert result == "ok"
    assert attempts == 3
    assert delays == [2, 4]


def test_retry_does_not_repeat_validation_errors() -> None:
    attempts = 0

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("schema berubah")

    with pytest.raises(ValueError, match="schema berubah"):
        run_with_retry(
            operation,
            attempts=3,
            base_delay_seconds=0,
            sleep=lambda _delay: None,
        )

    assert attempts == 1


def test_world_bank_scheduler_refreshes_all_configured_asean_countries(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    def execute(**kwargs):
        calls.append(kwargs)
        run_id = len(calls)
        return SimpleNamespace(rows_loaded=5, run_id=run_id)

    monkeypatch.setattr(scheduled_job, "execute_pipeline", execute)
    schedule = source(
        "annual",
        day=15,
        month=7,
        options={"countries": ["IDN", "MYS", "SGP"], "start_year": 2000},
    )

    result = scheduled_job._run_world_bank(
        object(), schedule, datetime(2026, 9, 1, tzinfo=UTC)
    )

    assert [call["country"] for call in calls] == ["IDN", "MYS", "SGP"]
    assert all(call["end_year"] == 2025 for call in calls)
    assert result.rows_loaded == 15
    assert result.pipeline_run_ids == (1, 2, 3)
