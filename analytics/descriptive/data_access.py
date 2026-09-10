from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipelines.utils.database import get_engine


@dataclass(frozen=True)
class EDADataBundle:
    national: pd.DataFrame
    asean: pd.DataFrame
    monetary: pd.DataFrame
    regional: pd.DataFrame


VIEW_QUERIES = {
    "national": "SELECT * FROM mart_national_overview ORDER BY observation_date",
    "asean": (
        "SELECT * FROM mart_asean_comparison "
        "ORDER BY indicator_code, observation_date, region_code"
    ),
    "monetary": "SELECT * FROM mart_monetary_conditions ORDER BY observation_date",
    "regional": (
        "SELECT * FROM mart_regional_analysis "
        "ORDER BY indicator_code, observation_date, region_code"
    ),
}

DATASET_SOURCES = {
    "national": "World Bank Indicators API v2",
    "asean": "World Bank Indicators API v2",
    "monetary": "Bank Indonesia (BI-Rate dan JISDOR)",
    "regional": "Badan Pusat Statistik Web API",
}


def _normalize_dates(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in (
        "observation_date",
        "previous_observation_date",
        "next_observation_date",
        "member_since",
    ):
        if column in result:
            result[column] = pd.to_datetime(result[column], errors="raise")
    return result


def load_eda_data(engine: Engine | None = None) -> EDADataBundle:
    owned_engine = engine is None
    active_engine = engine or get_engine()
    try:
        with active_engine.connect() as connection:
            frames = {
                name: _normalize_dates(pd.read_sql_query(text(statement), connection))
                for name, statement in VIEW_QUERIES.items()
            }
    finally:
        if owned_engine:
            active_engine.dispose()
    return EDADataBundle(**frames)


def dataset_inventory(bundle: EDADataBundle) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name in VIEW_QUERIES:
        frame = getattr(bundle, name)
        observation_dates = (
            frame["observation_date"].dropna()
            if "observation_date" in frame
            else pd.Series(dtype="datetime64[ns]")
        )
        rows.append(
            {
                "dataset": name,
                "source": DATASET_SOURCES[name],
                "row_count": len(frame),
                "column_count": len(frame.columns),
                "period_start": (
                    observation_dates.min().date()
                    if not observation_dates.empty
                    else None
                ),
                "period_end": (
                    observation_dates.max().date()
                    if not observation_dates.empty
                    else None
                ),
                "missing_cells": int(frame.isna().sum().sum()),
            }
        )
    return pd.DataFrame(rows)
