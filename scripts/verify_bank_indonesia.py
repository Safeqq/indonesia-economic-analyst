from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.jobs.run_bank_indonesia_pipeline import (  # noqa: E402
    previous_complete_month_end,
)
from pipelines.utils.bank_indonesia_config import (  # noqa: E402
    load_bank_indonesia_configuration,
)
from pipelines.utils.database import get_engine  # noqa: E402


def verify_bank_indonesia() -> None:
    configuration = load_bank_indonesia_configuration()
    expected_codes = {
        configuration.bi_rate.code,
        configuration.jisdor.code,
    }
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    i.indicator_code,
                    COUNT(*) AS observation_count,
                    MIN(f.observation_date) AS first_observation,
                    MAX(f.observation_date) AS last_observation
                FROM fact_economic_indicator AS f
                JOIN dim_indicator AS i ON i.indicator_id = f.indicator_id
                JOIN dim_source AS s ON s.source_id = f.source_id
                WHERE s.source_code = 'bank_indonesia'
                GROUP BY i.indicator_code
                ORDER BY i.indicator_code
                """
            )
        ).mappings()
        coverage = {row["indicator_code"]: dict(row) for row in rows}
        incomplete_months = connection.execute(
            text(
                """
                SELECT observation_date, COUNT(DISTINCT indicator_code)
                FROM stg_bank_indonesia
                GROUP BY observation_date
                HAVING COUNT(DISTINCT indicator_code) <> 2
                """
            )
        ).all()
        latest_run = connection.execute(
            text(
                """
                SELECT status, rows_loaded
                FROM fact_pipeline_run
                WHERE source_code = 'bank_indonesia'
                ORDER BY started_at DESC, run_id DESC
                LIMIT 1
                """
            )
        ).one_or_none()

    actual_codes = set(coverage)
    if actual_codes != expected_codes:
        raise RuntimeError(
            "Database belum memiliki dua indikator produksi BI: "
            f"expected={sorted(expected_codes)}, actual={sorted(actual_codes)}"
        )
    if incomplete_months:
        raise RuntimeError(
            f"Periode BI tidak sejajar pada {len(incomplete_months)} bulan"
        )
    latest_expected = previous_complete_month_end().replace(day=1)
    latest_dates = {row["last_observation"] for row in coverage.values()}
    if latest_dates != {latest_expected}:
        raise RuntimeError(
            "Observasi BI belum mencapai bulan lengkap terakhir: "
            f"expected={latest_expected}, actual={sorted(latest_dates)}"
        )
    if latest_run is None or latest_run.status != "success":
        raise RuntimeError("Pipeline run Bank Indonesia terbaru belum sukses")

    for code, row in coverage.items():
        print(
            f"[OK] {code}: {row['observation_count']} observasi, "
            f"{row['first_observation']} sampai {row['last_observation']}"
        )
    print(
        f"[OK] Pipeline BI terbaru sukses dengan {latest_run.rows_loaded} baris; "
        "seluruh bulan memiliki dua indikator"
    )


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        verify_bank_indonesia()
    except Exception as error:
        print(f"Verifikasi Bank Indonesia gagal: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
