from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

from pipelines.extract.bps_snapshot import (
    DEFAULT_BPS_RAW_DIRECTORY,
    save_bps_snapshot,
)
from pipelines.extract.extract_bps import SOURCE_CODE, BPSClient, extract_bps
from pipelines.load.load_to_mysql import (
    fail_pipeline_run,
    load_bps,
    start_pipeline_run,
)
from pipelines.transform.clean_bps_data import (
    clean_bps,
    validate_bps_coverage,
    validate_bps_metadata,
    validate_bps_value_ranges,
)
from pipelines.transform.validate_data import validate
from pipelines.utils.bps_config import (
    BPSConfiguration,
    load_bps_configuration,
    load_bps_provinces,
)
from pipelines.utils.database import get_engine
from pipelines.utils.structured_logging import configure_logging, log_event

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BPSPipelineResult:
    run_id: int
    rows_loaded: int
    raw_snapshot: Path
    complete_series: dict[int, str]


def _select_variables(
    configuration: BPSConfiguration, variable_ids: list[int] | None
) -> BPSConfiguration:
    if not variable_ids:
        return configuration
    duplicated = sorted({item for item in variable_ids if variable_ids.count(item) > 1})
    if duplicated:
        raise ValueError(f"Variabel BPS dipilih lebih dari sekali: {duplicated}")
    unknown = sorted(set(variable_ids).difference(configuration.indicators))
    if unknown:
        raise ValueError(f"Variabel BPS tidak ditemukan di config: {unknown}")
    return BPSConfiguration(
        source=configuration.source,
        indicators={item: configuration.indicators[item] for item in variable_ids},
    )


def execute_bps_pipeline(
    variable_ids: list[int] | None = None,
    *,
    raw_directory: Path = DEFAULT_BPS_RAW_DIRECTORY,
    engine: Engine | None = None,
    client: BPSClient | None = None,
    configuration: BPSConfiguration | None = None,
) -> BPSPipelineResult:
    configuration = _select_variables(
        configuration or load_bps_configuration(), variable_ids
    )
    province_configuration = load_bps_provinces()
    engine = engine or get_engine()
    engine, run_id = start_pipeline_run(SOURCE_CODE, engine)
    retrieved_at = datetime.now(UTC)

    try:
        client = client or BPSClient.from_environment(configuration.source.base_url)
        extraction = extract_bps(configuration, client)
        snapshot_path = save_bps_snapshot(extraction, retrieved_at, raw_directory)
        cleaned = clean_bps(
            extraction,
            configuration,
            province_configuration,
            retrieved_at,
        )
        validate(cleaned.frame)
        validate_bps_metadata(cleaned.metadata, cleaned.frame)
        validate_bps_value_ranges(cleaned.frame)
        complete_series = validate_bps_coverage(
            cleaned.frame, configuration, cleaned.provinces
        )
        rows_loaded = load_bps(cleaned.frame, cleaned.metadata, run_id, engine)
    except Exception as error:
        fail_pipeline_run(run_id, error, engine)
        raise

    return BPSPipelineResult(
        run_id=run_id,
        rows_loaded=rows_loaded,
        raw_snapshot=snapshot_path,
        complete_series=complete_series,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ambil indikator provinsi BPS dan muat ke MariaDB"
    )
    parser.add_argument(
        "--variable",
        dest="variables",
        action="append",
        type=int,
        help="ID variabel BPS; ulangi opsi untuk beberapa variabel",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env")
    configure_logging()
    try:
        result = execute_bps_pipeline(args.variables)
    except Exception as error:
        log_event(
            LOGGER,
            logging.ERROR,
            "pipeline_failed",
            "Pipeline BPS gagal",
            source_code=SOURCE_CODE,
            error_type=error.__class__.__name__,
            error=str(error),
        )
        return 1

    log_event(
        LOGGER,
        logging.INFO,
        "pipeline_succeeded",
        "Pipeline BPS selesai",
        source_code=SOURCE_CODE,
        rows_loaded=result.rows_loaded,
        run_id=result.run_id,
        raw_snapshot=result.raw_snapshot,
    )
    for variable_id, series in result.complete_series.items():
        log_event(
            LOGGER,
            logging.INFO,
            "pipeline_coverage_validated",
            "Cakupan provinsi BPS lengkap",
            source_code=SOURCE_CODE,
            variable_id=variable_id,
            series=series,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
