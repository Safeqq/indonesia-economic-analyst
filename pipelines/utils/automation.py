from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, TypeVar
from zoneinfo import ZoneInfo

import requests
import yaml
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "automation.yml"
ScheduleFrequency = Literal["monthly", "annual"]
T = TypeVar("T")


@dataclass(frozen=True)
class SourceAutomation:
    source_code: str
    frequency: ScheduleFrequency
    run_after_day: int
    run_after_month: int | None
    max_ingestion_age_hours: int
    max_observation_lag_days: int
    credential_environment: str | None = None
    pipeline_options: dict[str, object] | None = None


@dataclass(frozen=True)
class AutomationConfiguration:
    timezone: str
    lock_name: str
    lock_timeout_seconds: int
    retry_attempts: int
    retry_base_delay_seconds: float
    sources: dict[str, SourceAutomation]


def _positive_integer(value: object, label: str, *, maximum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} harus berupa integer positif")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} tidak boleh lebih besar dari {maximum}")
    return value


def load_automation_configuration(
    path: Path = DEFAULT_CONFIG_PATH,
) -> AutomationConfiguration:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Konfigurasi automation harus berupa object YAML")

    timezone = str(payload.get("timezone", ""))
    try:
        ZoneInfo(timezone)
    except Exception as error:
        raise ValueError(f"Timezone automation tidak valid: {timezone!r}") from error

    lock = payload.get("lock")
    retry = payload.get("retry")
    source_payloads = payload.get("sources")
    if not isinstance(lock, dict) or not isinstance(retry, dict):
        raise ValueError("Konfigurasi lock dan retry wajib berupa object")
    if not isinstance(source_payloads, dict) or not source_payloads:
        raise ValueError("Minimal satu sumber automation wajib dikonfigurasi")

    lock_name = str(lock.get("name", "")).strip()
    if not lock_name or len(lock_name) > 64:
        raise ValueError("Nama database lock wajib berisi 1 sampai 64 karakter")
    lock_timeout = lock.get("timeout_seconds")
    if (
        not isinstance(lock_timeout, int)
        or isinstance(lock_timeout, bool)
        or lock_timeout < 0
    ):
        raise ValueError("lock.timeout_seconds harus berupa integer non-negatif")

    retry_attempts = _positive_integer(retry.get("attempts"), "retry.attempts")
    retry_delay = retry.get("base_delay_seconds")
    if (
        not isinstance(retry_delay, (int, float))
        or isinstance(retry_delay, bool)
        or retry_delay < 0
    ):
        raise ValueError("retry.base_delay_seconds harus berupa angka non-negatif")

    sources: dict[str, SourceAutomation] = {}
    for source_code, source_payload in source_payloads.items():
        if not isinstance(source_payload, dict):
            raise ValueError(f"Konfigurasi sumber {source_code} harus berupa object")
        frequency = source_payload.get("frequency")
        if frequency not in ("monthly", "annual"):
            raise ValueError(f"Frekuensi automation {source_code} tidak didukung")
        run_after = source_payload.get("run_after")
        if not isinstance(run_after, dict):
            raise ValueError(f"run_after untuk {source_code} wajib berupa object")
        day = _positive_integer(
            run_after.get("day"), f"{source_code}.run_after.day", maximum=28
        )
        month = None
        if frequency == "annual":
            month = _positive_integer(
                run_after.get("month"),
                f"{source_code}.run_after.month",
                maximum=12,
            )
        credential = source_payload.get("credential_environment")
        if credential is not None and not str(credential).strip():
            raise ValueError(f"credential_environment {source_code} tidak valid")
        pipeline_options = source_payload.get("pipeline_options", {})
        if not isinstance(pipeline_options, dict):
            raise ValueError(f"pipeline_options {source_code} harus berupa object")
        sources[str(source_code)] = SourceAutomation(
            source_code=str(source_code),
            frequency=frequency,
            run_after_day=day,
            run_after_month=month,
            max_ingestion_age_hours=_positive_integer(
                source_payload.get("max_ingestion_age_hours"),
                f"{source_code}.max_ingestion_age_hours",
            ),
            max_observation_lag_days=_positive_integer(
                source_payload.get("max_observation_lag_days"),
                f"{source_code}.max_observation_lag_days",
            ),
            credential_environment=(
                str(credential) if credential is not None else None
            ),
            pipeline_options=dict(pipeline_options),
        )

    return AutomationConfiguration(
        timezone=timezone,
        lock_name=lock_name,
        lock_timeout_seconds=lock_timeout,
        retry_attempts=retry_attempts,
        retry_base_delay_seconds=float(retry_delay),
        sources=sources,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_source_due(
    source: SourceAutomation,
    last_success_at: datetime | None,
    now: datetime,
    timezone: str,
) -> bool:
    local_now = _as_utc(now).astimezone(ZoneInfo(timezone))
    if source.frequency == "monthly":
        if local_now.day < source.run_after_day:
            return False
        if last_success_at is None:
            return True
        local_success = _as_utc(last_success_at).astimezone(ZoneInfo(timezone))
        return (local_success.year, local_success.month) < (
            local_now.year,
            local_now.month,
        )

    if source.run_after_month is None:
        raise ValueError(f"Bulan jadwal tahunan {source.source_code} belum diisi")
    boundary = local_now.replace(
        month=source.run_after_month,
        day=source.run_after_day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    if last_success_at is None:
        return local_now >= boundary
    local_success = _as_utc(last_success_at).astimezone(ZoneInfo(timezone))
    return local_now >= boundary and local_success < boundary


def latest_successful_runs(engine: Engine) -> dict[str, datetime]:
    # A direct pipeline run can cover only one country or indicator. Only a
    # completed scheduler run proves that the configured source scope finished.
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT source_code, MAX(completed_at) AS completed_at
                FROM pipeline_schedule_run
                WHERE status = 'success' AND completed_at IS NOT NULL
                GROUP BY source_code
                """
            )
        ).mappings()
        return {
            str(row["source_code"]): row["completed_at"]
            for row in rows
            if isinstance(row["completed_at"], datetime)
        }


def scheduled_period(source: SourceAutomation, now: datetime, timezone: str) -> date:
    local_now = _as_utc(now).astimezone(ZoneInfo(timezone))
    if source.frequency == "monthly":
        return local_now.date().replace(day=1)
    return local_now.date().replace(month=1, day=1)


def start_scheduled_run(
    engine: Engine,
    source_code: str,
    period: date,
    started_at: datetime,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO pipeline_schedule_run (
                    source_code, scheduled_period, started_at, completed_at,
                    status, attempts, rows_loaded, error_message
                ) VALUES (
                    :source_code, :scheduled_period, :started_at, NULL,
                    'running', 0, 0, NULL
                )
                ON DUPLICATE KEY UPDATE
                    started_at = VALUES(started_at),
                    completed_at = NULL,
                    status = 'running',
                    attempts = 0,
                    rows_loaded = 0,
                    error_message = NULL
                """
            ),
            {
                "source_code": source_code,
                "scheduled_period": period,
                "started_at": _as_utc(started_at).replace(tzinfo=None),
            },
        )


def finish_scheduled_run(
    engine: Engine,
    source_code: str,
    period: date,
    *,
    completed_at: datetime,
    status: Literal["success", "failed"],
    attempts: int,
    rows_loaded: int = 0,
    error_message: str | None = None,
) -> None:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE pipeline_schedule_run
                SET completed_at = :completed_at,
                    status = :status,
                    attempts = :attempts,
                    rows_loaded = :rows_loaded,
                    error_message = :error_message
                WHERE source_code = :source_code
                  AND scheduled_period = :scheduled_period
                  AND status = 'running'
                """
            ),
            {
                "source_code": source_code,
                "scheduled_period": period,
                "completed_at": _as_utc(completed_at).replace(tzinfo=None),
                "status": status,
                "attempts": attempts,
                "rows_loaded": rows_loaded,
                "error_message": error_message,
            },
        )
        if result.rowcount != 1:
            raise RuntimeError(
                f"Schedule run {source_code}/{period.isoformat()} "
                "tidak dapat diselesaikan"
            )


def _error_chain(error: BaseException) -> Iterator[BaseException]:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def is_transient_error(error: BaseException) -> bool:
    for item in _error_chain(error):
        if isinstance(
            item, (OperationalError, requests.Timeout, requests.ConnectionError)
        ):
            return True
        if isinstance(item, requests.HTTPError):
            status_code = (
                item.response.status_code if item.response is not None else None
            )
            return status_code is None or status_code == 429 or status_code >= 500
    return False


def run_with_retry(
    operation: Callable[[], T],
    *,
    attempts: int,
    base_delay_seconds: float,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    if attempts < 1:
        raise ValueError("Jumlah attempt minimal satu")
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as error:
            if attempt == attempts or not is_transient_error(error):
                raise
            delay = base_delay_seconds * (2 ** (attempt - 1))
            if on_retry is not None:
                on_retry(attempt + 1, delay, error)
            sleep(delay)
    raise AssertionError("Retry loop selesai tanpa hasil")


@contextmanager
def named_database_lock(
    engine: Engine,
    lock_name: str,
    timeout_seconds: int,
) -> Iterator[None]:
    connection = engine.connect()
    acquired = False
    try:
        result = connection.execute(
            text("SELECT GET_LOCK(:lock_name, :timeout_seconds)"),
            {"lock_name": lock_name, "timeout_seconds": timeout_seconds},
        ).scalar_one()
        acquired = result == 1
        if not acquired:
            raise RuntimeError(
                "Scheduler lain masih memegang database lock; run dibatalkan"
            )
        yield
    finally:
        if acquired:
            connection.execute(
                text("SELECT RELEASE_LOCK(:lock_name)"), {"lock_name": lock_name}
            )
        connection.close()
