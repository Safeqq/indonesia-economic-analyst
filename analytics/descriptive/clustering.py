from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


class InsufficientRegionalData(ValueError):
    """Data BPS belum memadai untuk clustering regional yang sah."""


@dataclass(frozen=True)
class RegionalClusteringResult:
    observation_year: int
    feature_columns: tuple[str, ...]
    cluster_count: int
    silhouette: float
    assignments: pd.DataFrame


def prepare_regional_features(
    frame: pd.DataFrame,
    *,
    min_features: int = 2,
    min_regions: int = 4,
) -> tuple[int, pd.DataFrame]:
    if frame.empty:
        raise InsufficientRegionalData(
            "Mart regional BPS kosong; clustering menunggu pipeline BPS produksi"
        )
    required = {"observation_year", "indicator_code", "region_code", "value"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Kolom clustering regional tidak ditemukan: {missing}")
    duplicates = frame.duplicated(["observation_year", "indicator_code", "region_code"])
    if duplicates.any():
        raise ValueError(
            "Clustering menemukan lebih dari satu nilai per seri/wilayah/tahun"
        )

    for year in sorted(frame["observation_year"].dropna().unique(), reverse=True):
        selected = frame.loc[frame["observation_year"].eq(year)]
        pivot = selected.pivot(
            index="region_code", columns="indicator_code", values="value"
        )
        eligible_columns = pivot.columns[pivot.notna().sum().ge(min_regions)]
        complete = pivot[eligible_columns].dropna()
        if len(eligible_columns) >= min_features and len(complete) >= min_regions:
            numeric = complete.apply(pd.to_numeric, errors="raise")
            return int(year), numeric.sort_index()
    raise InsufficientRegionalData(
        "Belum ada tahun BPS dengan minimal dua indikator dan empat wilayah lengkap"
    )


def cluster_regional_features(
    observation_year: int,
    features: pd.DataFrame,
    *,
    max_clusters: int = 6,
    random_state: int = 42,
) -> RegionalClusteringResult:
    if features.isna().any().any():
        raise ValueError("Clustering regional tidak menerima missing value")
    if len(features) < 4 or features.shape[1] < 2:
        raise InsufficientRegionalData(
            "Clustering memerlukan minimal empat wilayah dan dua indikator"
        )
    scaled = StandardScaler().fit_transform(features)
    upper = min(max_clusters, len(features) - 1)
    candidates: list[tuple[float, int, KMeans]] = []
    for cluster_count in range(2, upper + 1):
        model = KMeans(
            n_clusters=cluster_count,
            random_state=random_state,
            n_init=20,
        )
        labels = model.fit_predict(scaled)
        if len(set(labels)) < 2:
            continue
        candidates.append(
            (float(silhouette_score(scaled, labels)), cluster_count, model)
        )
    if not candidates:
        raise InsufficientRegionalData("Tidak ada konfigurasi cluster yang valid")
    silhouette, cluster_count, model = max(
        candidates, key=lambda item: (item[0], -item[1])
    )
    labels = model.labels_
    coordinates = PCA(n_components=2).fit_transform(scaled)
    assignments = pd.DataFrame(
        {
            "region_code": features.index,
            "cluster": labels,
            "pca_1": coordinates[:, 0],
            "pca_2": coordinates[:, 1],
        }
    ).sort_values(["cluster", "region_code"], ignore_index=True)
    return RegionalClusteringResult(
        observation_year=observation_year,
        feature_columns=tuple(str(item) for item in features.columns),
        cluster_count=cluster_count,
        silhouette=silhouette,
        assignments=assignments,
    )
