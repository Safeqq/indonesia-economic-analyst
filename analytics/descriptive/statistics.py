from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd


def profile_frame(frame: pd.DataFrame) -> pd.DataFrame:
    row_count = len(frame)
    rows = []
    for column in frame.columns:
        series = frame[column]
        missing_count = int(series.isna().sum())
        rows.append(
            {
                "column": column,
                "dtype": str(series.dtype),
                "non_null_count": int(series.notna().sum()),
                "missing_count": missing_count,
                "missing_percent": (
                    100 * missing_count / row_count if row_count else np.nan
                ),
                "unique_count": int(series.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)


def descriptive_statistics(
    frame: pd.DataFrame, columns: Sequence[str] | None = None
) -> pd.DataFrame:
    selected = (
        list(columns)
        if columns is not None
        else list(frame.select_dtypes(include="number").columns)
    )
    missing = sorted(set(selected).difference(frame.columns))
    if missing:
        raise ValueError(f"Kolom statistik tidak ditemukan: {missing}")
    if not selected:
        return pd.DataFrame()
    result = frame[selected].describe(percentiles=[0.25, 0.5, 0.75]).transpose()
    result["missing_count"] = frame[selected].isna().sum()
    return result.reset_index(names="variable")


def add_growth_rates(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    date_column: str = "observation_date",
) -> pd.DataFrame:
    required = {date_column, *columns}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Kolom growth tidak ditemukan: {missing}")
    result = frame.sort_values(date_column).copy()
    if result[date_column].duplicated().any():
        raise ValueError("Growth rate memerlukan satu baris per periode")
    for column in columns:
        numeric = pd.to_numeric(result[column], errors="coerce")
        growth = numeric.pct_change(fill_method=None) * 100
        result[f"{column}_growth_percent"] = growth.replace([np.inf, -np.inf], np.nan)
    return result


def iqr_outliers(
    frame: pd.DataFrame,
    columns: Iterable[str],
    *,
    date_column: str = "observation_date",
) -> pd.DataFrame:
    output: list[dict[str, object]] = []
    for column in columns:
        if column not in frame:
            raise ValueError(f"Kolom outlier tidak ditemukan: {column}")
        numeric = pd.to_numeric(frame[column], errors="coerce")
        available = numeric.dropna()
        if available.empty:
            continue
        first_quartile = float(available.quantile(0.25))
        third_quartile = float(available.quantile(0.75))
        spread = third_quartile - first_quartile
        lower_bound = first_quartile - 1.5 * spread
        upper_bound = third_quartile + 1.5 * spread
        mask = numeric.lt(lower_bound) | numeric.gt(upper_bound)
        for index in frame.index[mask]:
            output.append(
                {
                    "variable": column,
                    "observation_date": frame.at[index, date_column]
                    if date_column in frame
                    else index,
                    "value": float(numeric.at[index]),
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "direction": "low" if numeric.at[index] < lower_bound else "high",
                }
            )
    return pd.DataFrame(
        output,
        columns=[
            "variable",
            "observation_date",
            "value",
            "lower_bound",
            "upper_bound",
            "direction",
        ],
    )


def monthly_seasonality(
    frame: pd.DataFrame,
    value_column: str,
    *,
    date_column: str = "observation_date",
) -> pd.DataFrame:
    missing = {date_column, value_column}.difference(frame.columns)
    if missing:
        raise ValueError(f"Kolom seasonality tidak ditemukan: {sorted(missing)}")
    values = frame[[date_column, value_column]].dropna().copy()
    values[date_column] = pd.to_datetime(values[date_column], errors="raise")
    values["calendar_month"] = values[date_column].dt.month
    return (
        values.groupby("calendar_month")[value_column]
        .agg(
            observation_count="count",
            mean="mean",
            median="median",
            min="min",
            max="max",
        )
        .reset_index()
    )


def annualize_monetary(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "observation_date",
        "observation_year",
        "bi_rate_percent",
        "jisdor_idr_per_usd",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Kolom moneter tidak ditemukan: {sorted(missing)}")
    return (
        frame.groupby("observation_year", as_index=False)
        .agg(
            bi_rate_annual_average=("bi_rate_percent", "mean"),
            jisdor_annual_average=("jisdor_idr_per_usd", "mean"),
            monetary_month_count=("observation_date", "count"),
        )
        .sort_values("observation_year", ignore_index=True)
    )


def build_correlation_dataset(
    national: pd.DataFrame, monetary: pd.DataFrame
) -> pd.DataFrame:
    national_columns = [
        "observation_date",
        "observation_year",
        "gdp_growth_percent",
        "inflation_percent",
        "unemployment_percent",
        "population",
        "gdp_per_capita_current_usd",
    ]
    missing = sorted(set(national_columns).difference(national.columns))
    if missing:
        raise ValueError(f"Kolom nasional tidak ditemukan: {missing}")
    return national[national_columns].merge(
        annualize_monetary(monetary),
        on="observation_year",
        how="left",
        validate="one_to_one",
    )


def correlation_with_overlap(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    method: str = "pearson",
    min_periods: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if method not in {"pearson", "spearman"}:
        raise ValueError("Metode korelasi harus pearson atau spearman")
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"Kolom korelasi tidak ditemukan: {missing}")
    values = frame[list(columns)].apply(pd.to_numeric, errors="coerce")
    correlations = values.corr(method=method, min_periods=min_periods)
    available = values.notna().astype(int)
    overlap = available.transpose().dot(available)
    return correlations, overlap


def lagged_correlation(
    frame: pd.DataFrame,
    target: str,
    feature: str,
    lags: Iterable[int],
    *,
    time_column: str = "observation_year",
    min_observations: int = 6,
) -> pd.DataFrame:
    required = {time_column, target, feature}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Kolom lagged correlation tidak ditemukan: {missing}")
    ordered = frame.sort_values(time_column)
    if ordered[time_column].duplicated().any():
        raise ValueError("Lagged correlation memerlukan satu baris per periode")
    target_values = pd.to_numeric(ordered[target], errors="coerce")
    feature_values = pd.to_numeric(ordered[feature], errors="coerce")
    rows = []
    for lag in lags:
        aligned = pd.concat([target_values, feature_values.shift(lag)], axis=1).dropna()
        correlation = (
            float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
            if len(aligned) >= min_observations
            else np.nan
        )
        rows.append(
            {
                "lag": int(lag),
                "correlation": correlation,
                "observation_count": len(aligned),
            }
        )
    return pd.DataFrame(rows)


def latest_asean_snapshot(frame: pd.DataFrame, indicator_code: str) -> pd.DataFrame:
    selected = frame.loc[frame["indicator_code"].eq(indicator_code)].copy()
    if selected.empty:
        raise ValueError(f"Indikator ASEAN tidak tersedia: {indicator_code}")
    latest_year = int(selected["observation_year"].max())
    return selected.loc[selected["observation_year"].eq(latest_year)].sort_values(
        ["value", "region_code"], ascending=[False, True], ignore_index=True
    )


def latest_indonesia_vs_asean(frame: pd.DataFrame) -> pd.DataFrame:
    indonesia = frame.loc[frame["region_code"].eq("IDN")].copy()
    if indonesia.empty:
        return indonesia
    latest_rows = indonesia.loc[
        indonesia.groupby("indicator_code")["observation_year"].idxmax()
    ]
    columns = [
        "indicator_code",
        "indicator_name",
        "unit",
        "observation_year",
        "value",
        "asean_average",
        "difference_from_asean_average",
        "country_coverage",
        "value_rank_desc",
    ]
    return latest_rows[columns].sort_values("indicator_code", ignore_index=True)
