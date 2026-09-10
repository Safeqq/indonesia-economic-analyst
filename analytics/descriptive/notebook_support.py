from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MPL_CACHE_DIRECTORY = PROJECT_ROOT / "data" / "exports" / ".matplotlib"
MPL_CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIRECTORY))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from IPython.display import Markdown  # noqa: E402

from analytics.descriptive.data_access import EDADataBundle, load_eda_data  # noqa: E402

EDA_EXPORT_DIRECTORY = PROJECT_ROOT / "data" / "exports" / "eda"


def prepare_notebook() -> EDADataBundle:
    load_dotenv(PROJECT_ROOT / ".env")
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.float_format", lambda value: f"{value:,.4f}")
    plt.style.use("seaborn-v0_8-whitegrid")
    return load_eda_data()


def period_text(frame: pd.DataFrame, date_column: str = "observation_date") -> str:
    dates = pd.to_datetime(frame[date_column], errors="coerce").dropna()
    if dates.empty:
        return "tidak tersedia"
    return f"{dates.min():%Y-%m-%d} sampai {dates.max():%Y-%m-%d}"


def insight(
    finding: str,
    *,
    frame: pd.DataFrame,
    source: str,
    limitation: str,
    date_column: str = "observation_date",
) -> Markdown:
    return Markdown(
        f"**Hasil.** {finding}\n\n"
        f"**Periode dan sumber.** {period_text(frame, date_column)}; {source}.\n\n"
        f"**Interpretasi dan keterbatasan.** {limitation}"
    )


def save_figure(figure: plt.Figure, filename: str) -> Path:
    if not filename.endswith(".png"):
        raise ValueError("Nama figure EDA harus berakhiran .png")
    EDA_EXPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = EDA_EXPORT_DIRECTORY / filename
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    return destination
