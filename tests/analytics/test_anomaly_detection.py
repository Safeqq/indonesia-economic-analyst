import numpy as np
import pandas as pd

from analytics.anomaly_detection.statistical import detect_rolling_mad_anomalies


def test_missing_period_is_classified_separately() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-01", "2025-03-01"]),
            "value": [100.0, 101.0],
        }
    )

    result = detect_rolling_mad_anomalies(
        frame,
        date_column="date",
        value_column="value",
        frequency="MS",
        window=6,
        minimum_history=2,
        threshold=3.5,
    )

    event = result.events.loc[result.events["anomaly_type"].eq("missing_value")]
    assert len(event) == 1
    assert event.iloc[0]["observation_date"] == pd.Timestamp("2025-02-01")
    assert "tidak memiliki nilai" in event.iloc[0]["reason"]


def test_confirmed_revision_is_not_labeled_economic_anomaly() -> None:
    dates = pd.date_range("2024-01-01", periods=10, freq="MS")
    frame = pd.DataFrame({"date": dates, "value": np.arange(10, dtype=float)})
    revision_date = dates[7]

    result = detect_rolling_mad_anomalies(
        frame,
        date_column="date",
        value_column="value",
        frequency="MS",
        window=6,
        minimum_history=3,
        threshold=3.5,
        revision_events={revision_date: "Sumber menerbitkan angka revisi"},
    )

    event = result.events.loc[result.events["observation_date"].eq(revision_date)]
    assert len(event) == 1
    assert event.iloc[0]["anomaly_type"] == "source_revision"
    assert "terkonfirmasi" in event.iloc[0]["reason"]


def test_large_change_is_labeled_as_economic_candidate_with_reason() -> None:
    changes = [1, -1, 2, -2, 1, -1, 2, -2, 1, -1, 2, -2, 30]
    values = np.cumsum([100, *changes])
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(values), freq="MS"),
            "value": values,
        }
    )

    result = detect_rolling_mad_anomalies(
        frame,
        date_column="date",
        value_column="value",
        frequency="MS",
        window=12,
        minimum_history=8,
        threshold=3.5,
    )

    economic = result.events.loc[result.events["anomaly_type"].eq("economic_anomaly")]
    assert len(economic) == 1
    assert economic.iloc[0]["change"] == 30
    assert "kandidat anomali ekonomi" in economic.iloc[0]["reason"]
