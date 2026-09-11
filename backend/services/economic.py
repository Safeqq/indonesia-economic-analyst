from __future__ import annotations

import json
from collections.abc import Mapping
from math import ceil

from backend.models.schemas import (
    ASEANComparisonItem,
    ASEANComparisonResponse,
    DataQualityCheck,
    DataQualityResponse,
    ForecastMetrics,
    ForecastPoint,
    ForecastResponse,
    HealthResponse,
    IndicatorListResponse,
    IndicatorReference,
    IndicatorSeriesResponse,
    IndicatorSummary,
    MonetarySnapshot,
    NationalSnapshot,
    OverviewResponse,
    PaginationMetadata,
    PipelineRunItem,
    PipelineRunListResponse,
    RegionIndicatorSnapshot,
    RegionListResponse,
    RegionOverviewResponse,
    RegionReference,
    RegionSummary,
    SeriesObservation,
)
from backend.repositories.economic import EconomicRepository, RepositoryPage
from backend.services.exceptions import DataIntegrityError, ResourceNotFoundError


def _pagination(page: int, page_size: int, total_items: int) -> PaginationMetadata:
    return PaginationMetadata(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=ceil(total_items / page_size) if total_items else 0,
    )


def _indicator_reference(row: Mapping[str, object]) -> IndicatorReference:
    return IndicatorReference.model_validate(dict(row))


def _region_reference(row: Mapping[str, object]) -> RegionReference:
    return RegionReference.model_validate(dict(row))


class EconomicService:
    def __init__(self, repository: EconomicRepository) -> None:
        self.repository = repository

    def health(self) -> HealthResponse:
        self.repository.health_check()
        return HealthResponse(status="ok", database="reachable")

    def overview(self) -> OverviewResponse:
        region = self.repository.get_region("IDN")
        if region is None:
            raise DataIntegrityError("Wilayah IDN tidak tersedia di dim_region")
        national, monetary = self.repository.get_latest_overview()
        if national is None and monetary is None:
            raise ResourceNotFoundError("Data overview belum tersedia")
        return OverviewResponse(
            region=_region_reference(region),
            national=(
                NationalSnapshot.model_validate(
                    {**national, "source_code": "world_bank"}
                )
                if national is not None
                else None
            ),
            monetary=(
                MonetarySnapshot.model_validate(
                    {**monetary, "source_code": "bank_indonesia"}
                )
                if monetary is not None
                else None
            ),
        )

    def indicators(
        self,
        *,
        frequency: str | None,
        source_code: str | None,
        page: int,
        page_size: int,
    ) -> IndicatorListResponse:
        result = self.repository.list_indicators(
            frequency=frequency,
            source_code=source_code,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        items: list[IndicatorSummary] = []
        for raw_row in result.items:
            row = dict(raw_row)
            sources = str(row.pop("source_codes_csv") or "")
            row["source_codes"] = [value for value in sources.split(",") if value]
            items.append(IndicatorSummary.model_validate(row))
        return IndicatorListResponse(
            items=items,
            pagination=_pagination(page, page_size, result.total_items),
        )

    def indicator_series(
        self,
        *,
        indicator_code: str,
        region_code: str,
        start_year: int | None,
        end_year: int | None,
        page: int,
        page_size: int,
    ) -> IndicatorSeriesResponse:
        indicator = self.repository.get_indicator(indicator_code)
        if indicator is None:
            raise ResourceNotFoundError(f"Indikator {indicator_code!r} tidak ditemukan")
        region = self.repository.get_region(region_code)
        if region is None:
            raise ResourceNotFoundError(f"Wilayah {region_code!r} tidak ditemukan")
        result = self.repository.list_indicator_series(
            indicator_code=indicator_code,
            region_code=region_code,
            start_year=start_year,
            end_year=end_year,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return IndicatorSeriesResponse(
            indicator=_indicator_reference(indicator),
            region=_region_reference(region),
            items=[SeriesObservation.model_validate(row) for row in result.items],
            pagination=_pagination(page, page_size, result.total_items),
        )

    def regions(
        self,
        *,
        region_level: str | None,
        page: int,
        page_size: int,
    ) -> RegionListResponse:
        result = self.repository.list_regions(
            region_level=region_level,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return RegionListResponse(
            items=[RegionSummary.model_validate(row) for row in result.items],
            pagination=_pagination(page, page_size, result.total_items),
        )

    def region_overview(
        self,
        *,
        region_code: str,
        year: int | None,
        page: int,
        page_size: int,
    ) -> RegionOverviewResponse:
        region = self.repository.get_region(region_code)
        if region is None:
            raise ResourceNotFoundError(f"Wilayah {region_code!r} tidak ditemukan")
        result = self.repository.list_region_overview(
            region_code=region_code,
            year=year,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return RegionOverviewResponse(
            region=_region_reference(region),
            observation_year=year,
            items=[RegionIndicatorSnapshot.model_validate(row) for row in result.items],
            pagination=_pagination(page, page_size, result.total_items),
        )

    def asean_comparison(
        self, *, indicator_code: str, year: int | None
    ) -> ASEANComparisonResponse:
        indicator = self.repository.get_indicator(indicator_code)
        if indicator is None:
            raise ResourceNotFoundError(f"Indikator {indicator_code!r} tidak ditemukan")
        observation_year = year
        if observation_year is None:
            observation_year = self.repository.get_latest_asean_year(indicator_code)
            if observation_year is None:
                raise ResourceNotFoundError(
                    f"Data ASEAN untuk indikator {indicator_code!r} belum tersedia"
                )
        rows = self.repository.list_asean_comparison(indicator_code, observation_year)
        return ASEANComparisonResponse(
            indicator=_indicator_reference(indicator),
            observation_year=observation_year,
            source_code="world_bank",
            items=[ASEANComparisonItem.model_validate(row) for row in rows],
        )

    def forecast(self, *, indicator_code: str, region_code: str) -> ForecastResponse:
        indicator = self.repository.get_indicator(indicator_code)
        if indicator is None:
            raise ResourceNotFoundError(f"Indikator {indicator_code!r} tidak ditemukan")
        region = self.repository.get_region(region_code)
        if region is None:
            raise ResourceNotFoundError(f"Wilayah {region_code!r} tidak ditemukan")
        run, raw_forecasts = self.repository.get_latest_forecast(
            indicator_code, region_code
        )
        if run is None:
            raise ResourceNotFoundError(
                f"Forecast untuk {indicator_code!r} dan {region_code!r} belum tersedia"
            )
        quality_metadata = self._quality_metadata(run["quality_reasons_json"])
        quality_status = str(run["quality_status"])
        forecasts = (
            [ForecastPoint.model_validate(row) for row in raw_forecasts]
            if quality_status == "passed"
            else []
        )
        if quality_status == "passed":
            horizon = int(run["forecast_horizon"])
            if len(forecasts) != horizon:
                raise DataIntegrityError(
                    "Jumlah forecast publishable tidak sesuai horizon run"
                )
            data_end = run["data_end"]
            if any(item.forecast_date <= data_end for item in forecasts):
                raise DataIntegrityError("Forecast tidak berada setelah data terakhir")
            if any(
                not item.lower_bound <= item.point_forecast <= item.upper_bound
                for item in forecasts
            ):
                raise DataIntegrityError("Forecast berada di luar intervalnya")
        return ForecastResponse(
            forecast_run_id=int(run["forecast_run_id"]),
            indicator=_indicator_reference(indicator),
            region=_region_reference(region),
            source_code=str(run["source_code"]),
            generated_at=run["generated_at"],
            data_start=run["data_start"],
            data_end=run["data_end"],
            test_start=run["test_start"],
            test_end=run["test_end"],
            selected_model_name=str(run["selected_model_name"]),
            selected_model_family=str(run["selected_model_family"]),
            baseline_model_name=str(run["baseline_model_name"]),
            selected_metrics=ForecastMetrics(
                mae=run["selected_mae"],
                rmse=run["selected_rmse"],
                mape_percent=run["selected_mape_percent"],
            ),
            baseline_metrics=ForecastMetrics(
                mae=run["baseline_mae"],
                rmse=run["baseline_rmse"],
                mape_percent=run["baseline_mape_percent"],
            ),
            mae_improvement_percent=run["mae_improvement_percent"],
            interval_coverage_percent=run["interval_coverage_percent"],
            forecast_horizon=run["forecast_horizon"],
            confidence_level=run["confidence_level"],
            quality_status=quality_status,
            quality_reasons=quality_metadata["reasons"],
            quality_thresholds=quality_metadata["thresholds"],
            anomaly_count=int(run["anomaly_count"]),
            is_estimate_not_fact=True,
            items=forecasts,
        )

    @staticmethod
    def _quality_metadata(raw_value: object) -> dict[str, object]:
        try:
            payload = json.loads(str(raw_value))
        except (TypeError, json.JSONDecodeError) as error:
            raise DataIntegrityError("Metadata quality gate tidak valid") from error
        if not isinstance(payload, dict):
            raise DataIntegrityError("Metadata quality gate bukan object")
        reasons = payload.get("reasons")
        thresholds = payload.get("thresholds")
        if not isinstance(reasons, list) or not all(
            isinstance(reason, str) for reason in reasons
        ):
            raise DataIntegrityError("Alasan quality gate tidak valid")
        if not isinstance(thresholds, dict):
            raise DataIntegrityError("Threshold quality gate tidak valid")
        try:
            normalized_thresholds = {
                str(key): float(value) for key, value in thresholds.items()
            }
        except (TypeError, ValueError) as error:
            raise DataIntegrityError(
                "Nilai threshold quality gate tidak valid"
            ) from error
        return {"reasons": reasons, "thresholds": normalized_thresholds}

    def data_quality(self) -> DataQualityResponse:
        results = self.repository.get_data_quality()
        checks: list[DataQualityCheck] = []
        blocking_failures = 0
        informational_findings = 0
        for result in results:
            finding_count = len(result.rows)
            if result.blocking:
                status = "failed" if finding_count else "passed"
                blocking_failures += finding_count
            else:
                status = "info"
                informational_findings += finding_count
            checks.append(
                DataQualityCheck(
                    name=result.name,
                    blocking=result.blocking,
                    status=status,
                    finding_count=finding_count,
                )
            )
        return DataQualityResponse(
            status="degraded" if blocking_failures else "healthy",
            blocking_failures=blocking_failures,
            informational_findings=informational_findings,
            checks=checks,
        )

    def pipeline_runs(
        self,
        *,
        source_code: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> PipelineRunListResponse:
        result: RepositoryPage = self.repository.list_pipeline_runs(
            source_code=source_code,
            status=status,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        items: list[PipelineRunItem] = []
        for raw_row in result.items:
            row = dict(raw_row)
            row["has_error"] = bool(row.pop("error_message", None))
            items.append(PipelineRunItem.model_validate(row))
        return PipelineRunListResponse(
            items=items,
            pagination=_pagination(page, page_size, result.total_items),
        )
