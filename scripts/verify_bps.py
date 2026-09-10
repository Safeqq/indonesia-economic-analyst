from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.utils.bps_config import (  # noqa: E402
    load_bps_configuration,
    load_bps_provinces,
)
from pipelines.utils.database import get_engine  # noqa: E402


@dataclass(frozen=True)
class BPSVerification:
    observation_count: int
    province_count: int
    complete_series: dict[int, str]
    metadata_version_count: int


def verify_bps(engine: Engine | None = None) -> BPSVerification:
    configuration = load_bps_configuration()
    province_configuration = load_bps_provinces()
    expected_regions = set(province_configuration.provinces)
    engine = engine or get_engine()
    with engine.connect() as connection:
        observation_count = int(
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM fact_economic_indicator AS fact
                    INNER JOIN dim_source AS source
                        ON source.source_id = fact.source_id
                    WHERE source.source_code = 'bps'
                    """
                )
            ).scalar_one()
        )
        if observation_count == 0:
            raise RuntimeError("Database belum memiliki observasi produksi BPS")

        loaded_regions = set(
            connection.execute(
                text(
                    """
                    SELECT DISTINCT region.region_code
                    FROM fact_economic_indicator AS fact
                    INNER JOIN dim_source AS source
                        ON source.source_id = fact.source_id
                    INNER JOIN dim_region AS region
                        ON region.region_id = fact.region_id
                    WHERE source.source_code = 'bps'
                    """
                )
            ).scalars()
        )
        unexpected_regions = sorted(loaded_regions - expected_regions)
        if unexpected_regions:
            raise RuntimeError(
                "Database memiliki kode wilayah BPS tak terpetakan: "
                f"{unexpected_regions}"
            )

        complete_series: dict[int, str] = {}
        statement = text(
            """
            SELECT
                metadata.source_variable_id,
                indicator.indicator_code,
                fact.observation_date,
                COUNT(DISTINCT region.region_code) AS province_count
            FROM fact_economic_indicator AS fact
            INNER JOIN dim_source AS source
                ON source.source_id = fact.source_id
            INNER JOIN dim_indicator AS indicator
                ON indicator.indicator_id = fact.indicator_id
            INNER JOIN dim_region AS region
                ON region.region_id = fact.region_id
            INNER JOIN (
                SELECT DISTINCT indicator_id, source_id, source_variable_id
                FROM dim_indicator_metadata_history
            ) AS metadata
                ON metadata.indicator_id = fact.indicator_id
               AND metadata.source_id = fact.source_id
            WHERE source.source_code = 'bps'
              AND metadata.source_variable_id IN :variable_ids
            GROUP BY
                metadata.source_variable_id,
                indicator.indicator_code,
                fact.observation_date
            HAVING COUNT(DISTINCT region.region_code) = :expected_count
            ORDER BY fact.observation_date DESC, indicator.indicator_code
            """
        ).bindparams(bindparam("variable_ids", expanding=True))
        rows = connection.execute(
            statement,
            {
                "variable_ids": [str(item) for item in configuration.indicators],
                "expected_count": len(expected_regions),
            },
        ).mappings()
        for row in rows:
            variable_id = int(row["source_variable_id"])
            complete_series.setdefault(
                variable_id,
                f"{row['indicator_code']}@{row['observation_date']}",
            )
        missing_variables = sorted(
            set(configuration.indicators).difference(complete_series)
        )
        if missing_variables:
            raise RuntimeError(
                "Variabel BPS tanpa periode lengkap untuk seluruh provinsi: "
                f"{missing_variables}"
            )

        metadata_version_count = int(
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM dim_indicator_metadata_history AS history
                    INNER JOIN dim_source AS source
                        ON source.source_id = history.source_id
                    WHERE source.source_code = 'bps'
                    """
                )
            ).scalar_one()
        )
        if metadata_version_count < len(complete_series):
            raise RuntimeError("Riwayat metadata BPS tidak lengkap")

    return BPSVerification(
        observation_count=observation_count,
        province_count=len(loaded_regions),
        complete_series=complete_series,
        metadata_version_count=metadata_version_count,
    )


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        result = verify_bps()
    except Exception as error:
        print(f"[FAIL] Verifikasi BPS: {error}", file=sys.stderr)
        return 1
    print(f"[OK] Observasi BPS: {result.observation_count}")
    print(f"[OK] Provinsi BPS: {result.province_count}")
    print(f"[OK] Versi metadata BPS: {result.metadata_version_count}")
    for variable_id, series in result.complete_series.items():
        print(f"[OK] Variabel {variable_id}: {series}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
