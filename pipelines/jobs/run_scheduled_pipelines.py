from __future__ import annotations

import argparse
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

from pipelines.jobs.run_bank_indonesia_pipeline import (
    execute_bank_indonesia_pipeline,
    previous_complete_month_end,
)
from pipelines.jobs.run_bps_pipeline import execute_bps_pipeline
from pipelines.jobs.run_pipeline import execute_pipeline
from pipelines.utils.automation import (
    AutomationConfiguration,
    SourceAutomation,
    finish_scheduled_run,
    is_source_due,
    latest_successful_runs,
    load_automation_configuration,
    named_database_lock,
    run_with_retry,
    scheduled_period,
    start_scheduled_run,
)
from pipelines.utils.data_quality import run_quality_checks
from pipelines.utils.database import get_engine
from pipelines.utils.freshness import (
    assess_freshness,
    load_freshness_snapshots,
    persist_freshness_report,
)
from pipelines.utils.structured_logging import (
    configure_logging,
    log_event,
    redact_sensitive_text,
)
from scripts.build_marts import build_marts
from scripts.run_advanced_analytics import execute_and_persist_advanced_analytics

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)
COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class SourceExecutionResult:
    rows_loaded: int
    pipeline_run_ids: tuple[int, ...]


class SourceRunner(Protocol):
    def __call__(
        self,
        engine: Engine,
        source: SourceAutomation,
        now: datetime,
    ) -> SourceExecutionResult: ...


def _run_world_bank(
    engine: Engine, source: SourceAutomation, now: datetime
) -> SourceExecutionResult:
    options = source.pipeline_options or {}
    countries = options.get("countries", ["IDN"])
    start_year = options.get("start_year", 2000)
    if (
        not isinstance(countries, list)
        or not countries
        or any(
            not isinstance(country, str)
            or COUNTRY_CODE_PATTERN.fullmatch(country) is None
            for country in countries
        )
    ):
        raise ValueError("Daftar negara World Bank pada automation tidak valid")
    if (
        not isinstance(start_year, int)
        or isinstance(start_year, bool)
        or start_year < 1
    ):
        raise ValueError("start_year World Bank pada automation tidak valid")

    end_year = now.astimezone(UTC).year - 1
    results = [
        execute_pipeline(
            country=country,
            indicator_codes=None,
            start_year=start_year,
            end_year=end_year,
            engine=engine,
        )
        for country in countries
    ]
    return SourceExecutionResult(
        rows_loaded=sum(result.rows_loaded for result in results),
        pipeline_run_ids=tuple(result.run_id for result in results),
    )


def _run_bps(
    engine: Engine, _source: SourceAutomation, _now: datetime
) -> SourceExecutionResult:
    result = execute_bps_pipeline(engine=engine)
    return SourceExecutionResult(
        rows_loaded=result.rows_loaded,
        pipeline_run_ids=(result.run_id,),
    )


def _run_bank_indonesia(
    engine: Engine, _source: SourceAutomation, now: datetime
) -> SourceExecutionResult:
    end_date = previous_complete_month_end(
        now.astimezone(ZoneInfo("Asia/Jakarta")).date()
    )
    result = execute_bank_indonesia_pipeline(
        start_date=datetime(2016, 8, 1).date(),
        end_date=end_date,
        engine=engine,
    )
    return SourceExecutionResult(
        rows_loaded=result.rows_loaded,
        pipeline_run_ids=(result.run_id,),
    )


SOURCE_RUNNERS: dict[str, SourceRunner] = {
    "world_bank": _run_world_bank,
    "bps": _run_bps,
    "bank_indonesia": _run_bank_indonesia,
}


def _retry_log(source_code: str):
    def callback(attempt: int, delay: float, error: BaseException) -> None:
        log_event(
            LOGGER,
            logging.WARNING,
            "pipeline_retry_scheduled",
            "Kegagalan sementara; pipeline akan dicoba ulang",
            source_code=source_code,
            attempt=attempt,
            delay_seconds=delay,
            error_type=error.__class__.__name__,
        )

    return callback


def _check_credential(source: SourceAutomation) -> None:
    environment_name = source.credential_environment
    if environment_name and not os.getenv(environment_name):
        raise RuntimeError(
            f"{environment_name} belum dikonfigurasi untuk sumber {source.source_code}"
        )


def _run_source(
    engine: Engine,
    configuration: AutomationConfiguration,
    source: SourceAutomation,
    now: datetime,
) -> SourceExecutionResult:
    runner = SOURCE_RUNNERS.get(source.source_code)
    if runner is None:
        raise ValueError(f"Runner sumber belum tersedia: {source.source_code}")
    attempts = 0

    def operation() -> SourceExecutionResult:
        nonlocal attempts
        attempts += 1
        _check_credential(source)
        return runner(engine, source, now)

    period = scheduled_period(source, now, configuration.timezone)
    start_scheduled_run(engine, source.source_code, period, now)
    try:
        result = run_with_retry(
            operation,
            attempts=configuration.retry_attempts,
            base_delay_seconds=configuration.retry_base_delay_seconds,
            on_retry=_retry_log(source.source_code),
        )
    except Exception as error:
        finish_scheduled_run(
            engine,
            source.source_code,
            period,
            completed_at=datetime.now(UTC),
            status="failed",
            attempts=attempts,
            error_message=redact_sensitive_text(str(error)),
        )
        raise

    finish_scheduled_run(
        engine,
        source.source_code,
        period,
        completed_at=datetime.now(UTC),
        status="success",
        attempts=attempts,
        rows_loaded=result.rows_loaded,
    )
    return result


def _run_post_processing(
    engine: Engine,
    configuration: AutomationConfiguration,
    selected_sources: tuple[str, ...],
    updated_sources: set[str],
) -> bool:
    healthy = True
    if updated_sources:
        views = build_marts(engine)
        log_event(
            LOGGER,
            logging.INFO,
            "analytical_marts_rebuilt",
            "Analytical marts selesai dibangun ulang",
            view_count=len(views),
        )

    quality_results = run_quality_checks(engine)
    blocking_findings = sum(
        len(result.rows)
        for result in quality_results
        if result.blocking and result.rows
    )
    if blocking_findings:
        healthy = False
        log_event(
            LOGGER,
            logging.ERROR,
            "data_quality_failed",
            "Blocking data-quality check menemukan masalah",
            finding_count=blocking_findings,
        )
    else:
        log_event(
            LOGGER,
            logging.INFO,
            "data_quality_passed",
            "Seluruh blocking data-quality check lulus",
            check_count=len(quality_results),
        )

    if "bank_indonesia" in updated_sources:
        execution = execute_and_persist_advanced_analytics(engine)
        log_event(
            LOGGER,
            logging.INFO,
            "advanced_analytics_complete",
            "Advanced analytics selesai diperbarui",
            forecast_run_id=execution.persisted.forecast_run_id,
            forecast_rows=execution.persisted.forecast_rows,
            anomaly_rows=execution.persisted.anomaly_rows,
        )

    schedules = {code: configuration.sources[code] for code in selected_sources}
    snapshots = load_freshness_snapshots(engine, selected_sources)
    freshness = assess_freshness(snapshots, schedules)
    persist_freshness_report(freshness, engine)
    for finding in freshness.findings:
        healthy = False
        log_event(
            LOGGER,
            logging.WARNING,
            "data_freshness_alert",
            finding.message,
            source_code=finding.source_code,
            alert_type=finding.alert_type,
            severity=finding.severity,
        )
    if freshness.is_fresh:
        log_event(
            LOGGER,
            logging.INFO,
            "data_freshness_passed",
            "Seluruh sumber terpilih berada dalam ambang freshness",
            source_count=len(selected_sources),
        )
    return healthy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Jalankan pipeline yang jatuh tempo dan pemeriksaan operasional"
    )
    parser.add_argument(
        "--source",
        dest="sources",
        action="append",
        help="Kode sumber; ulangi untuk beberapa sumber",
    )
    parser.add_argument("--force", action="store_true", help="Abaikan keputusan jadwal")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tampilkan keputusan jadwal tanpa menjalankan pipeline",
    )
    parser.add_argument(
        "--skip-post-processing",
        action="store_true",
        help="Lewati mart, quality, analytics, dan freshness",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env")
    configure_logging()
    engine = None
    try:
        configuration = load_automation_configuration()
        selected = tuple(args.sources or configuration.sources)
        unknown = sorted(set(selected).difference(configuration.sources))
        if unknown:
            raise ValueError(f"Sumber automation tidak dikenal: {unknown}")
        if len(selected) != len(set(selected)):
            raise ValueError("Sumber automation tidak boleh duplikat")

        engine = get_engine()
        now = datetime.now(UTC)
        failures = False
        updated_sources: set[str] = set()
        with named_database_lock(
            engine,
            configuration.lock_name,
            configuration.lock_timeout_seconds,
        ):
            latest_runs = latest_successful_runs(engine)
            due_sources = tuple(
                code
                for code in selected
                if args.force
                or is_source_due(
                    configuration.sources[code],
                    latest_runs.get(code),
                    now,
                    configuration.timezone,
                )
            )
            for code in selected:
                log_event(
                    LOGGER,
                    logging.INFO,
                    "pipeline_schedule_decision",
                    "Keputusan jadwal pipeline dibuat",
                    source_code=code,
                    due=code in due_sources,
                    forced=args.force,
                    last_success_at=latest_runs.get(code),
                )
            if args.dry_run:
                return 0

            for source_code in due_sources:
                source = configuration.sources[source_code]
                log_event(
                    LOGGER,
                    logging.INFO,
                    "pipeline_started",
                    "Pipeline terjadwal dimulai",
                    source_code=source_code,
                )
                try:
                    result = _run_source(engine, configuration, source, now)
                except Exception as error:
                    failures = True
                    log_event(
                        LOGGER,
                        logging.ERROR,
                        "pipeline_failed",
                        "Pipeline terjadwal gagal",
                        source_code=source_code,
                        error_type=error.__class__.__name__,
                        error=str(error),
                    )
                    continue
                updated_sources.add(source_code)
                log_event(
                    LOGGER,
                    logging.INFO,
                    "pipeline_succeeded",
                    "Pipeline terjadwal selesai",
                    source_code=source_code,
                    rows_loaded=result.rows_loaded,
                    pipeline_run_ids=result.pipeline_run_ids,
                )

            if not args.skip_post_processing:
                try:
                    post_processing_healthy = _run_post_processing(
                        engine, configuration, selected, updated_sources
                    )
                except Exception as error:
                    failures = True
                    log_event(
                        LOGGER,
                        logging.ERROR,
                        "post_processing_failed",
                        "Post-processing terjadwal gagal",
                        error_type=error.__class__.__name__,
                        error=str(error),
                    )
                else:
                    failures = failures or not post_processing_healthy
    except Exception as error:
        log_event(
            LOGGER,
            logging.ERROR,
            "scheduler_failed",
            "Scheduler pipeline gagal dijalankan",
            error_type=error.__class__.__name__,
            error=str(error),
        )
        return 2
    finally:
        if engine is not None:
            engine.dispose()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
