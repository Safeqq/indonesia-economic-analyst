from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from pipelines.utils.automation import SourceAutomation

FreshnessAlertType = Literal[
    "missing_successful_run",
    "missing_observations",
    "stale_ingestion",
    "stale_observation",
]


@dataclass(frozen=True)
class SourceFreshnessSnapshot:
    source_code: str
    last_success_at: datetime | None
    last_ingested_at: datetime | None
    latest_observation_date: date | None


@dataclass(frozen=True)
class FreshnessFinding:
    source_code: str
    alert_type: FreshnessAlertType
    severity: Literal["warning", "critical"]
    message: str
    last_success_at: datetime | None
    last_ingested_at: datetime | None
    latest_observation_date: date | None

    @property
    def alert_key(self) -> str:
        value = f"{self.source_code}:{self.alert_type}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FreshnessReport:
    checked_at: datetime
    snapshots: tuple[SourceFreshnessSnapshot, ...]
    findings: tuple[FreshnessFinding, ...]

    @property
    def is_fresh(self) -> bool:
        return not self.findings


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def load_freshness_snapshots(
    engine: Engine, source_codes: tuple[str, ...]
) -> tuple[SourceFreshnessSnapshot, ...]:
    with engine.connect() as connection:
        successful_runs = {
            str(row["source_code"]): row["last_success_at"]
            for row in connection.execute(
                text(
                    """
                    SELECT source_code, MAX(completed_at) AS last_success_at
                    FROM fact_pipeline_run
                    WHERE status = 'success' AND completed_at IS NOT NULL
                    GROUP BY source_code
                    """
                )
            ).mappings()
        }
        observations = {
            str(row["source_code"]): row
            for row in connection.execute(
                text(
                    """
                    SELECT
                        source.source_code,
                        MAX(fact.ingested_at) AS last_ingested_at,
                        MAX(fact.observation_date) AS latest_observation_date
                    FROM fact_economic_indicator AS fact
                    JOIN dim_source AS source ON source.source_id = fact.source_id
                    GROUP BY source.source_code
                    """
                )
            ).mappings()
        }

    return tuple(
        SourceFreshnessSnapshot(
            source_code=source_code,
            last_success_at=successful_runs.get(source_code),
            last_ingested_at=(
                observations[source_code]["last_ingested_at"]
                if source_code in observations
                else None
            ),
            latest_observation_date=(
                observations[source_code]["latest_observation_date"]
                if source_code in observations
                else None
            ),
        )
        for source_code in source_codes
    )


def assess_freshness(
    snapshots: tuple[SourceFreshnessSnapshot, ...],
    schedules: dict[str, SourceAutomation],
    *,
    now: datetime | None = None,
) -> FreshnessReport:
    checked_at = _as_utc(now or datetime.now(UTC))
    findings: list[FreshnessFinding] = []
    for snapshot in snapshots:
        schedule = schedules[snapshot.source_code]
        if snapshot.last_success_at is None:
            findings.append(
                FreshnessFinding(
                    source_code=snapshot.source_code,
                    alert_type="missing_successful_run",
                    severity="critical",
                    message="Belum ada pipeline run yang berhasil untuk sumber ini",
                    last_success_at=None,
                    last_ingested_at=snapshot.last_ingested_at,
                    latest_observation_date=snapshot.latest_observation_date,
                )
            )
        if (
            snapshot.last_ingested_at is None
            or snapshot.latest_observation_date is None
        ):
            findings.append(
                FreshnessFinding(
                    source_code=snapshot.source_code,
                    alert_type="missing_observations",
                    severity="critical",
                    message="Belum ada observasi produksi untuk sumber ini",
                    last_success_at=snapshot.last_success_at,
                    last_ingested_at=snapshot.last_ingested_at,
                    latest_observation_date=snapshot.latest_observation_date,
                )
            )
            continue

        ingestion_age_hours = (
            checked_at - _as_utc(snapshot.last_ingested_at)
        ).total_seconds() / 3600
        if ingestion_age_hours > schedule.max_ingestion_age_hours:
            findings.append(
                FreshnessFinding(
                    source_code=snapshot.source_code,
                    alert_type="stale_ingestion",
                    severity="warning",
                    message=(
                        f"Ingestion terakhir berumur {ingestion_age_hours:.1f} jam; "
                        f"batas {schedule.max_ingestion_age_hours} jam"
                    ),
                    last_success_at=snapshot.last_success_at,
                    last_ingested_at=snapshot.last_ingested_at,
                    latest_observation_date=snapshot.latest_observation_date,
                )
            )

        observation_lag_days = (
            checked_at.date() - snapshot.latest_observation_date
        ).days
        if observation_lag_days > schedule.max_observation_lag_days:
            findings.append(
                FreshnessFinding(
                    source_code=snapshot.source_code,
                    alert_type="stale_observation",
                    severity="warning",
                    message=(
                        f"Observasi terbaru tertinggal {observation_lag_days} hari; "
                        f"batas {schedule.max_observation_lag_days} hari"
                    ),
                    last_success_at=snapshot.last_success_at,
                    last_ingested_at=snapshot.last_ingested_at,
                    latest_observation_date=snapshot.latest_observation_date,
                )
            )

    return FreshnessReport(
        checked_at=checked_at,
        snapshots=snapshots,
        findings=tuple(findings),
    )


def persist_freshness_report_connection(
    report: FreshnessReport, connection: Connection
) -> None:
    checked_at = report.checked_at.astimezone(UTC).replace(tzinfo=None)
    findings_by_source: dict[str, list[FreshnessFinding]] = {}
    for finding in report.findings:
        findings_by_source.setdefault(finding.source_code, []).append(finding)

    for snapshot in report.snapshots:
        connection.execute(
            text(
                """
                UPDATE data_freshness_alert
                SET resolved_at = :checked_at
                WHERE source_code = :source_code AND resolved_at IS NULL
                """
            ),
            {"source_code": snapshot.source_code, "checked_at": checked_at},
        )
        for finding in findings_by_source.get(snapshot.source_code, []):
            connection.execute(
                text(
                    """
                    INSERT INTO data_freshness_alert (
                        alert_key, source_code, alert_type, severity, message,
                        last_success_at, last_ingested_at,
                        latest_observation_date, first_detected_at,
                        last_detected_at, resolved_at
                    ) VALUES (
                        :alert_key, :source_code, :alert_type, :severity,
                        :message, :last_success_at, :last_ingested_at,
                        :latest_observation_date, :checked_at, :checked_at, NULL
                    )
                    ON DUPLICATE KEY UPDATE
                        severity = VALUES(severity),
                        message = VALUES(message),
                        last_success_at = VALUES(last_success_at),
                        last_ingested_at = VALUES(last_ingested_at),
                        latest_observation_date = VALUES(latest_observation_date),
                        last_detected_at = VALUES(last_detected_at),
                        resolved_at = NULL
                    """
                ),
                {
                    "alert_key": finding.alert_key,
                    "source_code": finding.source_code,
                    "alert_type": finding.alert_type,
                    "severity": finding.severity,
                    "message": finding.message,
                    "last_success_at": finding.last_success_at,
                    "last_ingested_at": finding.last_ingested_at,
                    "latest_observation_date": finding.latest_observation_date,
                    "checked_at": checked_at,
                },
            )


def persist_freshness_report(report: FreshnessReport, engine: Engine) -> None:
    with engine.begin() as connection:
        persist_freshness_report_connection(report, connection)
