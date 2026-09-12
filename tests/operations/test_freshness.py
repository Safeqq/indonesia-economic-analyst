from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from pipelines.utils.automation import SourceAutomation
from pipelines.utils.freshness import SourceFreshnessSnapshot, assess_freshness


def schedule(source_code: str) -> SourceAutomation:
    return SourceAutomation(
        source_code=source_code,
        frequency="monthly",
        run_after_day=5,
        run_after_month=None,
        max_ingestion_age_hours=48,
        max_observation_lag_days=60,
    )


def test_fresh_source_has_no_findings() -> None:
    now = datetime(2026, 9, 11, 12, tzinfo=UTC)
    snapshot = SourceFreshnessSnapshot(
        source_code="bank_indonesia",
        last_success_at=now - timedelta(hours=2),
        last_ingested_at=now - timedelta(hours=2),
        latest_observation_date=date(2026, 8, 1),
    )

    report = assess_freshness(
        (snapshot,), {snapshot.source_code: schedule(snapshot.source_code)}, now=now
    )

    assert report.is_fresh
    assert report.findings == ()


def test_missing_source_and_stale_data_raise_explicit_findings() -> None:
    now = datetime(2026, 9, 11, 12, tzinfo=UTC)
    missing = SourceFreshnessSnapshot("bps", None, None, None)
    stale = SourceFreshnessSnapshot(
        "bank_indonesia",
        now - timedelta(days=90),
        now - timedelta(days=3),
        date(2026, 1, 1),
    )
    schedules = {
        "bps": schedule("bps"),
        "bank_indonesia": schedule("bank_indonesia"),
    }

    report = assess_freshness((missing, stale), schedules, now=now)

    assert not report.is_fresh
    assert {(item.source_code, item.alert_type) for item in report.findings} == {
        ("bps", "missing_successful_run"),
        ("bps", "missing_observations"),
        ("bank_indonesia", "stale_ingestion"),
        ("bank_indonesia", "stale_observation"),
    }
