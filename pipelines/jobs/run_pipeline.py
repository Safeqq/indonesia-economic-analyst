from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

from pipelines.extract.extract_world_bank import SOURCE_CODE, extract_indicator
from pipelines.extract.raw_snapshot import DEFAULT_RAW_DIRECTORY, save_snapshot
from pipelines.load.load_to_mysql import (
    fail_pipeline_run,
    load_world_bank,
    start_pipeline_run,
)
from pipelines.transform.clean_economic_data import clean_world_bank
from pipelines.transform.validate_data import validate
from pipelines.utils.config import IndicatorDefinition, load_indicator_definitions
from pipelines.utils.database import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_START_YEAR = 2000
DEFAULT_END_YEAR = datetime.now(UTC).year - 1


@dataclass(frozen=True)
class PipelineResult:
    run_id: int
    rows_loaded: int
    raw_snapshot: Path


def _select_definitions(
    indicator_codes: list[str] | None,
) -> dict[str, IndicatorDefinition]:
    catalog = load_indicator_definitions()
    selected_codes = indicator_codes or [
        code for code, item in catalog.items() if item.source == SOURCE_CODE
    ]
    if not selected_codes:
        raise ValueError("Tidak ada indikator World Bank yang dipilih")

    unknown = sorted(set(selected_codes).difference(catalog))
    if unknown:
        raise ValueError(f"Indikator tidak ditemukan di config: {unknown}")
    duplicated = sorted(
        {code for code in selected_codes if selected_codes.count(code) > 1}
    )
    if duplicated:
        raise ValueError(f"Indikator dipilih lebih dari sekali: {duplicated}")

    selected = {code: catalog[code] for code in selected_codes}
    invalid_sources = sorted(
        code for code, item in selected.items() if item.source != SOURCE_CODE
    )
    if invalid_sources:
        raise ValueError(f"Indikator bukan milik World Bank: {invalid_sources}")
    return selected


def execute_pipeline(
    country: str,
    indicator_codes: list[str] | None,
    start_year: int,
    end_year: int,
    *,
    raw_directory: Path = DEFAULT_RAW_DIRECTORY,
    engine: Engine | None = None,
) -> PipelineResult:
    definitions = _select_definitions(indicator_codes)
    engine = engine or get_engine()
    engine, run_id = start_pipeline_run(SOURCE_CODE, engine)
    retrieved_at = datetime.now(UTC)

    try:
        extractions = [
            extract_indicator(country, code, start_year, end_year)
            for code in definitions
        ]
        snapshot_path = save_snapshot(extractions, retrieved_at, raw_directory)
        records = [
            record for extraction in extractions for record in extraction.records
        ]
        frame = clean_world_bank(records, definitions, retrieved_at)
        validate(frame)
        rows_loaded = load_world_bank(frame, run_id, engine)
    except Exception as error:
        fail_pipeline_run(run_id, error, engine)
        raise

    return PipelineResult(
        run_id=run_id,
        rows_loaded=rows_loaded,
        raw_snapshot=snapshot_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ambil indikator World Bank dan muat ke MariaDB"
    )
    parser.add_argument("--country", default="IDN", help="Kode negara World Bank")
    parser.add_argument(
        "--indicator",
        dest="indicators",
        action="append",
        help="Kode indikator; ulangi opsi ini untuk beberapa indikator",
    )
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        result = execute_pipeline(
            country=args.country,
            indicator_codes=args.indicators,
            start_year=args.start_year,
            end_year=args.end_year,
        )
    except Exception as error:
        print(f"Pipeline World Bank gagal: {error}", file=sys.stderr)
        return 1

    print(
        f"Pipeline selesai: {result.rows_loaded} observasi dimuat "
        f"(run_id={result.run_id})"
    )
    print(f"Raw snapshot: {result.raw_snapshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
