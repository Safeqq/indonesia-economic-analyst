from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipelines.utils.data_quality import QualityResult, run_quality_checks


@dataclass(frozen=True)
class RepositoryPage:
    items: tuple[dict[str, object], ...]
    total_items: int


class EconomicRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def health_check(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()

    def get_region(self, region_code: str) -> dict[str, object] | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        """
                        SELECT region_code, region_name, region_level,
                               parent_region_code
                        FROM dim_region
                        WHERE region_code = :region_code
                        """
                    ),
                    {"region_code": region_code},
                )
                .mappings()
                .one_or_none()
            )
        return dict(row) if row is not None else None

    def get_indicator(self, indicator_code: str) -> dict[str, object] | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        """
                        SELECT indicator_code, indicator_name, unit, frequency
                        FROM dim_indicator
                        WHERE indicator_code = :indicator_code
                        """
                    ),
                    {"indicator_code": indicator_code},
                )
                .mappings()
                .one_or_none()
            )
        return dict(row) if row is not None else None

    def get_latest_overview(
        self,
    ) -> tuple[dict[str, object] | None, dict[str, object] | None]:
        with self.engine.connect() as connection:
            national = (
                connection.execute(
                    text(
                        """
                        SELECT observation_date, observation_year,
                               gdp_growth_percent, inflation_percent,
                               unemployment_percent, population,
                               gdp_per_capita_current_usd, indicator_coverage,
                               last_ingested_at
                        FROM mart_national_overview
                        ORDER BY observation_date DESC
                        LIMIT 1
                        """
                    )
                )
                .mappings()
                .one_or_none()
            )
            monetary = (
                connection.execute(
                    text(
                        """
                        SELECT observation_date, observation_year,
                               observation_quarter, observation_month,
                               bi_rate_percent, bi_rate_change_pp,
                               jisdor_idr_per_usd, jisdor_mom_change,
                               jisdor_mom_percent_change,
                               jisdor_rolling_3_month_average,
                               indicator_coverage, ingested_at
                        FROM mart_monetary_conditions
                        ORDER BY observation_date DESC
                        LIMIT 1
                        """
                    )
                )
                .mappings()
                .one_or_none()
            )
        return (
            dict(national) if national is not None else None,
            dict(monetary) if monetary is not None else None,
        )

    def list_indicators(
        self,
        *,
        frequency: str | None,
        source_code: str | None,
        limit: int,
        offset: int,
    ) -> RepositoryPage:
        parameters = {
            "frequency": frequency,
            "source_code": source_code,
            "limit": limit,
            "offset": offset,
        }
        filters = """
            (:frequency IS NULL OR i.frequency = :frequency)
            AND (:source_code IS NULL OR s.source_code = :source_code)
        """
        with self.engine.connect() as connection:
            total = connection.execute(
                text(
                    f"""
                    SELECT COUNT(DISTINCT i.indicator_id)
                    FROM dim_indicator AS i
                    LEFT JOIN fact_economic_indicator AS f
                        ON f.indicator_id = i.indicator_id
                    LEFT JOIN dim_source AS s ON s.source_id = f.source_id
                    WHERE {filters}
                    """
                ),
                parameters,
            ).scalar_one()
            rows = (
                connection.execute(
                    text(
                        f"""
                        SELECT
                            i.indicator_code,
                            i.indicator_name,
                            i.unit,
                            i.frequency,
                            GROUP_CONCAT(
                                DISTINCT s.source_code
                                ORDER BY s.source_code SEPARATOR ','
                            ) AS source_codes_csv,
                            COUNT(f.observation_id) AS observation_count,
                            COUNT(DISTINCT f.region_id) AS region_count,
                            MIN(f.observation_date) AS period_start,
                            MAX(f.observation_date) AS period_end
                        FROM dim_indicator AS i
                        LEFT JOIN fact_economic_indicator AS f
                            ON f.indicator_id = i.indicator_id
                        LEFT JOIN dim_source AS s ON s.source_id = f.source_id
                        WHERE {filters}
                        GROUP BY i.indicator_id, i.indicator_code,
                                 i.indicator_name, i.unit, i.frequency
                        ORDER BY i.indicator_code
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    parameters,
                )
                .mappings()
                .all()
            )
        return RepositoryPage(tuple(dict(row) for row in rows), int(total))

    def list_indicator_series(
        self,
        *,
        indicator_code: str,
        region_code: str,
        start_year: int | None,
        end_year: int | None,
        limit: int,
        offset: int,
    ) -> RepositoryPage:
        parameters = {
            "indicator_code": indicator_code,
            "region_code": region_code,
            "start_date": date(start_year, 1, 1) if start_year is not None else None,
            "end_date": date(end_year, 12, 31) if end_year is not None else None,
            "limit": limit,
            "offset": offset,
        }
        filters = """
            i.indicator_code = :indicator_code
            AND r.region_code = :region_code
            AND (:start_date IS NULL OR f.observation_date >= :start_date)
            AND (:end_date IS NULL OR f.observation_date <= :end_date)
        """
        with self.engine.connect() as connection:
            total = connection.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM fact_economic_indicator AS f
                    JOIN dim_indicator AS i ON i.indicator_id = f.indicator_id
                    JOIN dim_region AS r ON r.region_id = f.region_id
                    WHERE {filters}
                    """
                ),
                parameters,
            ).scalar_one()
            rows = (
                connection.execute(
                    text(
                        f"""
                        SELECT f.observation_date, f.value, s.source_code,
                               f.ingested_at
                        FROM fact_economic_indicator AS f
                        JOIN dim_indicator AS i ON i.indicator_id = f.indicator_id
                        JOIN dim_region AS r ON r.region_id = f.region_id
                        JOIN dim_source AS s ON s.source_id = f.source_id
                        WHERE {filters}
                        ORDER BY f.observation_date, s.source_code
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    parameters,
                )
                .mappings()
                .all()
            )
        return RepositoryPage(tuple(dict(row) for row in rows), int(total))

    def list_regions(
        self,
        *,
        region_level: str | None,
        limit: int,
        offset: int,
    ) -> RepositoryPage:
        parameters = {
            "region_level": region_level,
            "limit": limit,
            "offset": offset,
        }
        with self.engine.connect() as connection:
            total = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM dim_region
                    WHERE :region_level IS NULL OR region_level = :region_level
                    """
                ),
                parameters,
            ).scalar_one()
            rows = (
                connection.execute(
                    text(
                        """
                        SELECT
                            r.region_code,
                            r.region_name,
                            r.region_level,
                            r.parent_region_code,
                            COUNT(DISTINCT f.indicator_id) AS indicator_count,
                            COUNT(f.observation_id) AS observation_count,
                            MIN(f.observation_date) AS period_start,
                            MAX(f.observation_date) AS period_end
                        FROM dim_region AS r
                        LEFT JOIN fact_economic_indicator AS f
                            ON f.region_id = r.region_id
                        WHERE :region_level IS NULL
                           OR r.region_level = :region_level
                        GROUP BY r.region_id, r.region_code, r.region_name,
                                 r.region_level, r.parent_region_code
                        ORDER BY r.region_level, r.region_code
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    parameters,
                )
                .mappings()
                .all()
            )
        return RepositoryPage(tuple(dict(row) for row in rows), int(total))

    def list_region_overview(
        self,
        *,
        region_code: str,
        year: int | None,
        limit: int,
        offset: int,
    ) -> RepositoryPage:
        parameters = {
            "region_code": region_code,
            "start_date": date(year, 1, 1) if year is not None else None,
            "end_date": date(year, 12, 31) if year is not None else None,
            "limit": limit,
            "offset": offset,
        }
        filters = """
            r.region_code = :region_code
            AND (:start_date IS NULL OR f.observation_date >= :start_date)
            AND (:end_date IS NULL OR f.observation_date <= :end_date)
        """
        with self.engine.connect() as connection:
            total = connection.execute(
                text(
                    f"""
                    SELECT COUNT(DISTINCT f.indicator_id)
                    FROM fact_economic_indicator AS f
                    JOIN dim_region AS r ON r.region_id = f.region_id
                    WHERE {filters}
                    """
                ),
                parameters,
            ).scalar_one()
            rows = (
                connection.execute(
                    text(
                        f"""
                        WITH ranked AS (
                            SELECT
                                i.indicator_code,
                                i.indicator_name,
                                i.unit,
                                i.frequency,
                                s.source_code,
                                f.observation_date,
                                f.value,
                                f.ingested_at,
                                ROW_NUMBER() OVER (
                                    PARTITION BY f.indicator_id
                                    ORDER BY f.observation_date DESC,
                                             f.ingested_at DESC,
                                             s.source_code
                                ) AS recency_rank
                            FROM fact_economic_indicator AS f
                            JOIN dim_indicator AS i
                                ON i.indicator_id = f.indicator_id
                            JOIN dim_region AS r ON r.region_id = f.region_id
                            JOIN dim_source AS s ON s.source_id = f.source_id
                            WHERE {filters}
                        )
                        SELECT indicator_code, indicator_name, unit, frequency,
                               source_code, observation_date, value, ingested_at
                        FROM ranked
                        WHERE recency_rank = 1
                        ORDER BY indicator_code
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    parameters,
                )
                .mappings()
                .all()
            )
        return RepositoryPage(tuple(dict(row) for row in rows), int(total))

    def get_latest_asean_year(self, indicator_code: str) -> int | None:
        with self.engine.connect() as connection:
            value = connection.execute(
                text(
                    """
                    SELECT MAX(observation_year)
                    FROM mart_asean_comparison
                    WHERE indicator_code = :indicator_code
                    """
                ),
                {"indicator_code": indicator_code},
            ).scalar_one()
        return int(value) if value is not None else None

    def list_asean_comparison(
        self, indicator_code: str, observation_year: int
    ) -> tuple[dict[str, object], ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        """
                        SELECT region_code, region_name, member_since,
                               was_member_during_period, observation_date, value,
                               asean_average, difference_from_asean_average,
                               country_coverage, value_rank_desc, value_percentile
                        FROM mart_asean_comparison
                        WHERE indicator_code = :indicator_code
                          AND observation_year = :observation_year
                        ORDER BY value_rank_desc, region_code
                        """
                    ),
                    {
                        "indicator_code": indicator_code,
                        "observation_year": observation_year,
                    },
                )
                .mappings()
                .all()
            )
        return tuple(dict(row) for row in rows)

    def get_latest_forecast(
        self, indicator_code: str, region_code: str
    ) -> tuple[dict[str, object] | None, tuple[dict[str, object], ...]]:
        with self.engine.connect() as connection:
            run = (
                connection.execute(
                    text(
                        """
                        SELECT
                            fr.forecast_run_id,
                            fr.generated_at,
                            fr.data_start,
                            fr.data_end,
                            fr.test_start,
                            fr.test_end,
                            fr.selected_model_name,
                            fr.selected_model_family,
                            fr.baseline_model_name,
                            fr.selected_mae,
                            fr.selected_rmse,
                            fr.selected_mape_percent,
                            fr.baseline_mae,
                            fr.baseline_rmse,
                            fr.baseline_mape_percent,
                            fr.mae_improvement_percent,
                            fr.interval_coverage_percent,
                            fr.forecast_horizon,
                            fr.confidence_level,
                            fr.quality_status,
                            fr.quality_reasons_json,
                            s.source_code,
                            (
                                SELECT COUNT(*)
                                FROM fact_anomaly_event AS anomaly
                                WHERE anomaly.forecast_run_id = fr.forecast_run_id
                            ) AS anomaly_count
                        FROM fact_forecast_run AS fr
                        JOIN dim_indicator AS i
                            ON i.indicator_id = fr.indicator_id
                        JOIN dim_region AS r ON r.region_id = fr.region_id
                        JOIN dim_source AS s ON s.source_id = fr.source_id
                        WHERE i.indicator_code = :indicator_code
                          AND r.region_code = :region_code
                        ORDER BY fr.generated_at DESC, fr.forecast_run_id DESC
                        LIMIT 1
                        """
                    ),
                    {
                        "indicator_code": indicator_code,
                        "region_code": region_code,
                    },
                )
                .mappings()
                .one_or_none()
            )
            if run is None:
                return None, ()
            forecasts = (
                connection.execute(
                    text(
                        """
                        SELECT forecast_date, point_forecast,
                               lower_bound, upper_bound
                        FROM fact_forecast
                        WHERE forecast_run_id = :forecast_run_id
                          AND is_publishable = 1
                        ORDER BY forecast_date
                        """
                    ),
                    {"forecast_run_id": run["forecast_run_id"]},
                )
                .mappings()
                .all()
            )
        return dict(run), tuple(dict(row) for row in forecasts)

    def get_data_quality(self) -> tuple[QualityResult, ...]:
        return run_quality_checks(self.engine)

    def list_pipeline_runs(
        self,
        *,
        source_code: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> RepositoryPage:
        parameters = {
            "source_code": source_code,
            "status": status,
            "limit": limit,
            "offset": offset,
        }
        filters = """
            (:source_code IS NULL OR source_code = :source_code)
            AND (:status IS NULL OR status = :status)
        """
        with self.engine.connect() as connection:
            total = connection.execute(
                text(f"SELECT COUNT(*) FROM fact_pipeline_run WHERE {filters}"),
                parameters,
            ).scalar_one()
            rows = (
                connection.execute(
                    text(
                        f"""
                        SELECT run_id, source_code, started_at, completed_at,
                               status, rows_loaded, error_message
                        FROM fact_pipeline_run
                        WHERE {filters}
                        ORDER BY started_at DESC, run_id DESC
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    parameters,
                )
                .mappings()
                .all()
            )
        return RepositoryPage(tuple(dict(row) for row in rows), int(total))
