from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

ANOMALY_COLUMNS = [
    "observation_date",
    "observed_value",
    "change",
    "score",
    "threshold",
    "anomaly_type",
    "method",
    "reason",
]


@dataclass(frozen=True)
class AnomalyDetectionResult:
    method: str
    window: int
    minimum_history: int
    threshold: float
    events: pd.DataFrame


def _normalize_revision_events(
    revision_events: Mapping[date | str | pd.Timestamp, str] | None,
) -> dict[pd.Timestamp, str]:
    normalized: dict[pd.Timestamp, str] = {}
    for raw_date, raw_reason in (revision_events or {}).items():
        timestamp = pd.Timestamp(raw_date).normalize()
        reason = str(raw_reason).strip()
        if not reason:
            raise ValueError(f"Alasan revisi sumber kosong untuk {timestamp.date()}")
        normalized[timestamp] = reason
    return normalized


def detect_rolling_mad_anomalies(
    frame: pd.DataFrame,
    *,
    date_column: str,
    value_column: str,
    frequency: str,
    window: int,
    minimum_history: int,
    threshold: float,
    revision_events: Mapping[date | str | pd.Timestamp, str] | None = None,
) -> AnomalyDetectionResult:
    if window < 1 or minimum_history < 1 or minimum_history > window:
        raise ValueError("Window anomaly tidak valid")
    if threshold <= 0:
        raise ValueError("Threshold anomaly harus positif")
    missing_columns = {date_column, value_column}.difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"Kolom anomaly detection tidak ditemukan: {sorted(missing_columns)}"
        )
    values = frame[[date_column, value_column]].copy()
    values[date_column] = pd.to_datetime(
        values[date_column], errors="raise"
    ).dt.normalize()
    values[value_column] = pd.to_numeric(values[value_column], errors="coerce")
    values = values.sort_values(date_column, ignore_index=True)
    if values.empty:
        raise ValueError("Time series anomaly detection kosong")
    if values[date_column].duplicated().any():
        raise ValueError("Time series anomaly detection memiliki periode duplikat")
    available_values = values[value_column].dropna()
    if not np.isfinite(available_values).all():
        raise ValueError("Time series anomaly detection memiliki nilai non-finite")
    expected_dates = pd.date_range(
        values[date_column].min(), values[date_column].max(), freq=frequency
    )
    actual_dates = pd.DatetimeIndex(values[date_column])
    unexpected_dates = actual_dates.difference(expected_dates)
    if len(unexpected_dates):
        raise ValueError(
            "Tanggal observasi tidak sesuai frekuensi: "
            f"{[item.date().isoformat() for item in unexpected_dates]}"
        )
    series = values.set_index(date_column)[value_column].reindex(expected_dates)
    revisions = _normalize_revision_events(revision_events)
    outside_range = sorted(set(revisions).difference(expected_dates))
    if outside_range:
        raise ValueError(
            "Tanggal revisi berada di luar rentang seri: "
            f"{[item.date().isoformat() for item in outside_range]}"
        )

    changes = series.diff()
    rows: list[dict[str, object]] = []
    revision_dates = set(revisions)
    for position, observation_date in enumerate(expected_dates):
        observed_value = series.iloc[position]
        change = changes.iloc[position]
        if pd.isna(observed_value):
            rows.append(
                {
                    "observation_date": observation_date,
                    "observed_value": None,
                    "change": None,
                    "score": None,
                    "threshold": threshold,
                    "anomaly_type": "missing_value",
                    "method": "calendar_continuity",
                    "reason": (
                        f"Periode {observation_date:%Y-%m-%d} tidak memiliki nilai "
                        f"pada frekuensi {frequency}."
                    ),
                }
            )
            continue
        if observation_date in revision_dates:
            revision_reason = revisions[observation_date]
            rows.append(
                {
                    "observation_date": observation_date,
                    "observed_value": float(observed_value),
                    "change": float(change) if pd.notna(change) else None,
                    "score": None,
                    "threshold": threshold,
                    "anomaly_type": "source_revision",
                    "method": "source_revision_metadata",
                    "reason": f"Revisi sumber terkonfirmasi: {revision_reason}",
                }
            )
            continue
        if pd.isna(change):
            continue

        history_start = max(1, position - window)
        history = changes.iloc[history_start:position].dropna()
        if revision_dates:
            history = history.loc[~history.index.isin(revision_dates)]
        if len(history) < minimum_history:
            continue
        historical_median = float(history.median())
        mad = float((history - historical_median).abs().median())
        deviation = float(change) - historical_median
        if mad == 0:
            if deviation == 0:
                continue
            score = None
            is_anomaly = True
            score_text = "tidak terdefinisi karena MAD historis nol"
        else:
            score = 0.67448975 * deviation / mad
            is_anomaly = abs(score) >= threshold
            score_text = f"{score:.3f}"
        if not is_anomaly:
            continue
        rows.append(
            {
                "observation_date": observation_date,
                "observed_value": float(observed_value),
                "change": float(change),
                "score": float(score) if score is not None else None,
                "threshold": threshold,
                "anomaly_type": "economic_anomaly",
                "method": "rolling_mad_first_difference",
                "reason": (
                    f"Perubahan {float(change):.6f} berbeda dari median historis "
                    f"{historical_median:.6f}; MAD={mad:.6f}; robust score "
                    f"{score_text}; threshold={threshold:.3f}. Ini kandidat "
                    "anomali ekonomi, bukan bukti kesalahan data."
                ),
            }
        )
    events = pd.DataFrame(rows, columns=ANOMALY_COLUMNS)
    return AnomalyDetectionResult(
        method="rolling_mad_first_difference",
        window=window,
        minimum_history=minimum_history,
        threshold=threshold,
        events=events,
    )
