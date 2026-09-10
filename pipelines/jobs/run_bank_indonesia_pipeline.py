from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from sqlalchemy.engine import Engine

from pipelines.extract.bank_indonesia_snapshot import (
    DEFAULT_BANK_INDONESIA_RAW_DIRECTORY,
    BankIndonesiaSnapshot,
    save_bank_indonesia_snapshot,
)
from pipelines.extract.extract_bank_indonesia import (
    SOURCE_CODE,
    extract_bank_indonesia,
)
from pipelines.load.load_to_mysql import (
    fail_pipeline_run,
    load_bank_indonesia,
    start_pipeline_run,
)
from pipelines.transform.clean_bank_indonesia_data import (
    clean_bank_indonesia,
    validate_bank_indonesia_coverage,
    validate_bank_indonesia_value_ranges,
    validate_complete_month_range,
)
from pipelines.transform.validate_data import validate
from pipelines.utils.bank_indonesia_config import (
    BankIndonesiaConfiguration,
    load_bank_indonesia_configuration,
)
from pipelines.utils.database import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JAKARTA_TIMEZONE = ZoneInfo("Asia/Jakarta")


@dataclass(frozen=True)
class BankIndonesiaPipelineResult:
    run_id: int
    rows_loaded: int
    month_count: int
    bi_rate_event_count: int
    jisdor_daily_count: int
    raw_snapshot: BankIndonesiaSnapshot


def previous_complete_month_end(today: date | None = None) -> date:
    current = today or datetime.now(JAKARTA_TIMEZONE).date()
    return current.replace(day=1) - timedelta(days=1)


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Tanggal harus memakai format YYYY-MM-DD: {value!r}"
        ) from error


def execute_bank_indonesia_pipeline(
    start_date: date,
    end_date: date,
    *,
    raw_directory: Path = DEFAULT_BANK_INDONESIA_RAW_DIRECTORY,
    engine: Engine | None = None,
    session: requests.Session | None = None,
    configuration: BankIndonesiaConfiguration | None = None,
) -> BankIndonesiaPipelineResult:
    validate_complete_month_range(start_date, end_date)
    configuration = configuration or load_bank_indonesia_configuration()
    engine = engine or get_engine()
    engine, run_id = start_pipeline_run(SOURCE_CODE, engine)
    retrieved_at = datetime.now(UTC)

    try:
        extraction = extract_bank_indonesia(
            configuration, start_date, end_date, session=session
        )
        snapshot = save_bank_indonesia_snapshot(extraction, retrieved_at, raw_directory)
        cleaned = clean_bank_indonesia(
            extraction,
            configuration,
            retrieved_at,
            start_date,
            end_date,
        )
        validate(cleaned.frame)
        validate_bank_indonesia_coverage(cleaned.frame, configuration)
        validate_bank_indonesia_value_ranges(cleaned.frame, configuration)
        rows_loaded = load_bank_indonesia(cleaned.frame, run_id, engine)
    except Exception as error:
        fail_pipeline_run(run_id, error, engine)
        raise

    return BankIndonesiaPipelineResult(
        run_id=run_id,
        rows_loaded=rows_loaded,
        month_count=cleaned.month_count,
        bi_rate_event_count=cleaned.bi_rate_event_count,
        jisdor_daily_count=cleaned.jisdor_daily_count,
        raw_snapshot=snapshot,
    )


def build_parser(
    configuration: BankIndonesiaConfiguration,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ambil BI-Rate dan JISDOR resmi lalu muat seri bulanan ke MariaDB"
    )
    parser.add_argument(
        "--start-date",
        type=parse_iso_date,
        default=configuration.source.default_start_date,
        help="Awal periode; harus tanggal pertama bulan (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_iso_date,
        default=previous_complete_month_end(),
        help="Akhir periode; harus akhir bulan lengkap (YYYY-MM-DD)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        configuration = load_bank_indonesia_configuration()
        args = build_parser(configuration).parse_args(argv)
        result = execute_bank_indonesia_pipeline(
            args.start_date,
            args.end_date,
            configuration=configuration,
        )
    except Exception as error:
        print(f"Pipeline Bank Indonesia gagal: {error}", file=sys.stderr)
        return 1

    print(
        f"Pipeline Bank Indonesia selesai: {result.rows_loaded} observasi bulanan "
        f"dimuat (run_id={result.run_id})"
    )
    print(
        f"Rekonsiliasi: {result.bi_rate_event_count} keputusan BI-Rate, "
        f"{result.jisdor_daily_count} observasi JISDOR harian, "
        f"{result.month_count} bulan"
    )
    print(f"Raw manifest: {result.raw_snapshot.manifest_path}")
    print(f"Raw BI-Rate: {result.raw_snapshot.bi_rate_path}")
    print(f"Raw JISDOR: {result.raw_snapshot.jisdor_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
