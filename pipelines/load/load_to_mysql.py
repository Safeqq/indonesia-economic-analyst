from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection, Engine

from pipelines.utils.database import get_engine

UPSERT_SOURCE = text(
    """
    INSERT INTO dim_source (source_code, source_name, source_url)
    VALUES (:source_code, :source_name, :source_url)
    ON DUPLICATE KEY UPDATE
        source_name = VALUES(source_name),
        source_url = VALUES(source_url)
    """
)
UPSERT_INDICATOR = text(
    """
    INSERT INTO dim_indicator
        (indicator_code, indicator_name, unit, frequency)
    VALUES
        (:indicator_code, :indicator_name, :unit, :frequency)
    ON DUPLICATE KEY UPDATE
        indicator_name = VALUES(indicator_name),
        unit = VALUES(unit),
        frequency = VALUES(frequency)
    """
)
UPSERT_REGION = text(
    """
    INSERT INTO dim_region
        (region_code, region_name, region_level, parent_region_code)
    VALUES
        (:region_code, :region_name, :region_level, :parent_region_code)
    ON DUPLICATE KEY UPDATE
        region_name = VALUES(region_name),
        region_level = VALUES(region_level),
        parent_region_code = VALUES(parent_region_code)
    """
)
UPSERT_DATE = text(
    """
    INSERT INTO dim_date (date_id, full_date, year, quarter, month)
    VALUES (:date_id, :full_date, :year, :quarter, :month)
    ON DUPLICATE KEY UPDATE
        year = VALUES(year),
        quarter = VALUES(quarter),
        month = VALUES(month)
    """
)
UPSERT_FACT = text(
    """
    INSERT INTO fact_economic_indicator
        (indicator_id, region_id, source_id, observation_date, value, ingested_at)
    VALUES
        (:indicator_id, :region_id, :source_id, :observation_date, :value,
         :ingested_at)
    ON DUPLICATE KEY UPDATE
        value = VALUES(value),
        ingested_at = VALUES(ingested_at)
    """
)
UPSERT_INDICATOR_METADATA = text(
    """
    INSERT INTO dim_indicator_metadata_history
        (indicator_id, source_id, source_variable_id, derived_variable_id,
         derived_period_id, indicator_name, unit, definition_text, notes,
         metadata_hash, period_start, period_end, first_observed_at,
         last_observed_at)
    VALUES
        (:indicator_id, :source_id, :source_variable_id, :derived_variable_id,
         :derived_period_id, :indicator_name, :unit, :definition_text, :notes,
         :metadata_hash, :period_start, :period_end, :observed_at, :observed_at)
    ON DUPLICATE KEY UPDATE
        indicator_name = VALUES(indicator_name),
        unit = VALUES(unit),
        definition_text = VALUES(definition_text),
        notes = VALUES(notes),
        period_start = LEAST(period_start, VALUES(period_start)),
        period_end = GREATEST(period_end, VALUES(period_end)),
        last_observed_at = GREATEST(last_observed_at, VALUES(last_observed_at))
    """
)


def start_pipeline_run(
    source_code: str, engine: Engine | None = None
) -> tuple[Engine, int]:
    engine = engine or get_engine()
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO fact_pipeline_run (source_code, started_at, status)
                VALUES (:source_code, :started_at, 'running')
                """
            ),
            {"source_code": source_code, "started_at": datetime.now(UTC)},
        )
        run_id = result.lastrowid
    if run_id is None:
        raise RuntimeError("Database tidak mengembalikan ID pipeline run")
    return engine, int(run_id)


def fail_pipeline_run(run_id: int, error: Exception, engine: Engine) -> None:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE fact_pipeline_run
                SET completed_at = :completed_at,
                    status = 'failed',
                    error_message = :error_message
                WHERE run_id = :run_id AND status = 'running'
                """
            ),
            {
                "completed_at": datetime.now(UTC),
                "error_message": str(error),
                "run_id": run_id,
            },
        )
        if result.rowcount != 1:
            raise RuntimeError(f"Pipeline run {run_id} tidak dapat ditandai gagal")


def _select_id_map(
    connection: Connection,
    table: str,
    id_column: str,
    code_column: str,
    values: list[str],
) -> dict[str, int]:
    statement = text(
        f"SELECT {id_column}, {code_column} FROM {table} WHERE {code_column} IN :values"
    ).bindparams(bindparam("values", expanding=True))
    result = connection.execute(statement, {"values": values})
    return {row[1]: int(row[0]) for row in result}


def _to_utc_naive(value: object) -> datetime:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    return timestamp.to_pydatetime()


def _upsert_dimensions(connection: Connection, frame: pd.DataFrame) -> None:
    source_rows = frame[["source_code", "source_name", "source_url"]].drop_duplicates()
    connection.execute(UPSERT_SOURCE, source_rows.to_dict("records"))

    indicator_rows = frame[
        ["indicator_code", "indicator_name", "unit", "frequency"]
    ].drop_duplicates()
    connection.execute(UPSERT_INDICATOR, indicator_rows.to_dict("records"))

    region_columns = ["region_code", "region_name", "region_level"]
    if "parent_region_code" in frame.columns:
        region_columns.append("parent_region_code")
    region_rows = frame[region_columns].drop_duplicates()
    regions = []
    for row in region_rows.to_dict("records"):
        row.setdefault("parent_region_code", None)
        regions.append(row)
    connection.execute(UPSERT_REGION, regions)

    observation_dates = sorted(
        {pd.Timestamp(value).date() for value in frame["observation_date"]}
    )
    dates = [
        {
            "date_id": int(value.strftime("%Y%m%d")),
            "full_date": value,
            "year": value.year,
            "quarter": (value.month - 1) // 3 + 1,
            "month": value.month,
        }
        for value in observation_dates
    ]
    connection.execute(UPSERT_DATE, dates)


def _fact_rows(connection: Connection, frame: pd.DataFrame) -> list[dict[str, object]]:
    indicator_codes = frame["indicator_code"].drop_duplicates().tolist()
    region_codes = frame["region_code"].drop_duplicates().tolist()
    source_codes = frame["source_code"].drop_duplicates().tolist()
    indicator_ids = _select_id_map(
        connection,
        "dim_indicator",
        "indicator_id",
        "indicator_code",
        indicator_codes,
    )
    region_ids = _select_id_map(
        connection, "dim_region", "region_id", "region_code", region_codes
    )
    source_ids = _select_id_map(
        connection, "dim_source", "source_id", "source_code", source_codes
    )

    rows: list[dict[str, object]] = []
    for row in frame.itertuples(index=False):
        observation_date: date = pd.Timestamp(row.observation_date).date()
        rows.append(
            {
                "indicator_id": indicator_ids[row.indicator_code],
                "region_id": region_ids[row.region_code],
                "source_id": source_ids[row.source_code],
                "observation_date": observation_date,
                "value": Decimal(str(row.value)),
                "ingested_at": _to_utc_naive(row.retrieved_at),
            }
        )
    return rows


def _upsert_indicator_metadata(connection: Connection, metadata: pd.DataFrame) -> None:
    if metadata.empty:
        return
    indicator_codes = metadata["indicator_code"].drop_duplicates().tolist()
    source_codes = metadata["source_code"].drop_duplicates().tolist()
    indicator_ids = _select_id_map(
        connection,
        "dim_indicator",
        "indicator_id",
        "indicator_code",
        indicator_codes,
    )
    source_ids = _select_id_map(
        connection, "dim_source", "source_id", "source_code", source_codes
    )
    rows: list[dict[str, object]] = []
    for row in metadata.itertuples(index=False):
        rows.append(
            {
                "indicator_id": indicator_ids[row.indicator_code],
                "source_id": source_ids[row.source_code],
                "source_variable_id": row.source_variable_id,
                "derived_variable_id": row.derived_variable_id,
                "derived_period_id": row.derived_period_id,
                "indicator_name": row.indicator_name,
                "unit": row.unit,
                "definition_text": row.definition_text,
                "notes": row.notes,
                "metadata_hash": row.metadata_hash,
                "period_start": pd.Timestamp(row.period_start).date(),
                "period_end": pd.Timestamp(row.period_end).date(),
                "observed_at": _to_utc_naive(row.observed_at),
            }
        )
    connection.execute(UPSERT_INDICATOR_METADATA, rows)


def load_economic_data_connection(
    frame: pd.DataFrame,
    run_id: int,
    connection: Connection,
    metadata: pd.DataFrame | None = None,
) -> int:
    rows_loaded = len(frame)
    _upsert_dimensions(connection, frame)
    connection.execute(UPSERT_FACT, _fact_rows(connection, frame))
    if metadata is not None:
        _upsert_indicator_metadata(connection, metadata)
    result = connection.execute(
        text(
            """
            UPDATE fact_pipeline_run
            SET completed_at = :completed_at,
                status = 'success',
                rows_loaded = :rows_loaded,
                error_message = NULL
            WHERE run_id = :run_id AND status = 'running'
            """
        ),
        {
            "completed_at": datetime.now(UTC),
            "rows_loaded": rows_loaded,
            "run_id": run_id,
        },
    )
    if result.rowcount != 1:
        raise RuntimeError(f"Pipeline run {run_id} tidak dapat diselesaikan")
    return rows_loaded


def load_world_bank_connection(
    frame: pd.DataFrame, run_id: int, connection: Connection
) -> int:
    return load_economic_data_connection(frame, run_id, connection)


def load_bps_connection(
    frame: pd.DataFrame,
    metadata: pd.DataFrame,
    run_id: int,
    connection: Connection,
) -> int:
    return load_economic_data_connection(frame, run_id, connection, metadata)


def load_world_bank(frame: pd.DataFrame, run_id: int, engine: Engine) -> int:
    with engine.begin() as connection:
        return load_world_bank_connection(frame, run_id, connection)


def load_bps(
    frame: pd.DataFrame, metadata: pd.DataFrame, run_id: int, engine: Engine
) -> int:
    with engine.begin() as connection:
        return load_bps_connection(frame, metadata, run_id, connection)
