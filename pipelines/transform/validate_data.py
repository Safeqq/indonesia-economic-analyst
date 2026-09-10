from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {
    "indicator_code",
    "indicator_name",
    "unit",
    "frequency",
    "region_code",
    "region_name",
    "region_level",
    "observation_date",
    "value",
    "source_code",
    "source_name",
    "source_url",
    "retrieved_at",
}
UNIQUE_COLUMNS = [
    "indicator_code",
    "region_code",
    "source_code",
    "observation_date",
]
TEXT_COLUMNS = [
    "indicator_code",
    "indicator_name",
    "unit",
    "frequency",
    "region_code",
    "region_name",
    "region_level",
    "source_code",
    "source_name",
    "source_url",
]
ALLOWED_FREQUENCIES = {"daily", "monthly", "quarterly", "annual"}
ALLOWED_REGION_LEVELS = {"country", "province", "city"}


def validate(frame: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak tersedia: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Dataset kosong; pipeline dihentikan")
    if frame[list(REQUIRED_COLUMNS)].isnull().any().any():
        raise ValueError("Dataset memiliki nilai null pada kolom wajib")

    empty_text = frame[TEXT_COLUMNS].apply(
        lambda column: column.astype(str).str.strip().eq("")
    )
    if empty_text.any().any():
        raise ValueError("Dataset memiliki teks kosong pada kolom wajib")
    if not set(frame["frequency"]).issubset(ALLOWED_FREQUENCIES):
        raise ValueError("Dataset memiliki frequency yang tidak didukung")
    if not set(frame["region_level"]).issubset(ALLOWED_REGION_LEVELS):
        raise ValueError("Dataset memiliki region_level yang tidak didukung")

    observation_dates = pd.to_datetime(frame["observation_date"], errors="coerce")
    retrieved_dates = pd.to_datetime(frame["retrieved_at"], errors="coerce", utc=True)
    if observation_dates.isnull().any() or retrieved_dates.isnull().any():
        raise ValueError("Dataset memiliki tanggal yang tidak valid")
    annual_rows = frame["frequency"].eq("annual")
    invalid_annual_date = annual_rows & (
        observation_dates.dt.month.ne(1) | observation_dates.dt.day.ne(1)
    )
    if invalid_annual_date.any():
        raise ValueError("Observasi annual harus menggunakan tanggal 1 Januari")

    numeric_values = pd.to_numeric(frame["value"], errors="coerce")
    if numeric_values.isnull().any() or not np.isfinite(
        numeric_values.to_numpy(dtype=float)
    ).all():
        raise ValueError("Dataset memiliki value non-numerik atau tidak finite")
    if frame.duplicated(UNIQUE_COLUMNS).any():
        raise ValueError("Dataset memiliki observasi duplikat")

    indicator_metadata = frame[
        ["indicator_code", "indicator_name", "unit", "frequency"]
    ].drop_duplicates()
    if indicator_metadata["indicator_code"].duplicated().any():
        raise ValueError("Metadata indikator tidak konsisten")
    region_metadata = frame[
        ["region_code", "region_name", "region_level"]
    ].drop_duplicates()
    if region_metadata["region_code"].duplicated().any():
        raise ValueError("Metadata wilayah tidak konsisten")
