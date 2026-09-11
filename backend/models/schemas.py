from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Frequency = Literal["daily", "monthly", "quarterly", "annual"]
RegionLevel = Literal["country", "province", "city"]
PipelineStatus = Literal["running", "success", "failed"]
QualityStatus = Literal["passed", "failed"]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ErrorResponse(APIModel):
    detail: str


class PaginationMetadata(APIModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class HealthResponse(APIModel):
    status: Literal["ok"]
    database: Literal["reachable"]


class IndicatorReference(APIModel):
    indicator_code: str
    indicator_name: str
    unit: str | None
    frequency: Frequency


class RegionReference(APIModel):
    region_code: str
    region_name: str
    region_level: RegionLevel
    parent_region_code: str | None


class NationalSnapshot(APIModel):
    source_code: Literal["world_bank"]
    observation_date: date
    observation_year: int
    gdp_growth_percent: float | None
    inflation_percent: float | None
    unemployment_percent: float | None
    population: float | None
    gdp_per_capita_current_usd: float | None
    indicator_coverage: int = Field(ge=0)
    last_ingested_at: datetime


class MonetarySnapshot(APIModel):
    source_code: Literal["bank_indonesia"]
    observation_date: date
    observation_year: int
    observation_quarter: int = Field(ge=1, le=4)
    observation_month: int = Field(ge=1, le=12)
    bi_rate_percent: float | None
    bi_rate_change_pp: float | None
    jisdor_idr_per_usd: float | None
    jisdor_mom_change: float | None
    jisdor_mom_percent_change: float | None
    jisdor_rolling_3_month_average: float | None
    indicator_coverage: int = Field(ge=0)
    ingested_at: datetime


class OverviewResponse(APIModel):
    region: RegionReference
    national: NationalSnapshot | None
    monetary: MonetarySnapshot | None


class IndicatorSummary(IndicatorReference):
    source_codes: list[str]
    observation_count: int = Field(ge=0)
    region_count: int = Field(ge=0)
    period_start: date | None
    period_end: date | None


class IndicatorListResponse(APIModel):
    items: list[IndicatorSummary]
    pagination: PaginationMetadata


class SeriesObservation(APIModel):
    observation_date: date
    value: float
    source_code: str
    ingested_at: datetime


class IndicatorSeriesResponse(APIModel):
    indicator: IndicatorReference
    region: RegionReference
    items: list[SeriesObservation]
    pagination: PaginationMetadata


class RegionSummary(RegionReference):
    indicator_count: int = Field(ge=0)
    observation_count: int = Field(ge=0)
    period_start: date | None
    period_end: date | None


class RegionListResponse(APIModel):
    items: list[RegionSummary]
    pagination: PaginationMetadata


class RegionIndicatorSnapshot(IndicatorReference):
    source_code: str
    observation_date: date
    value: float
    ingested_at: datetime


class RegionOverviewResponse(APIModel):
    region: RegionReference
    observation_year: int | None
    items: list[RegionIndicatorSnapshot]
    pagination: PaginationMetadata


class ASEANComparisonItem(APIModel):
    region_code: str
    region_name: str
    member_since: date
    was_member_during_period: bool
    observation_date: date
    value: float
    asean_average: float
    difference_from_asean_average: float
    country_coverage: int = Field(ge=0)
    value_rank_desc: int = Field(ge=1)
    value_percentile: float = Field(ge=0, le=1)


class ASEANComparisonResponse(APIModel):
    indicator: IndicatorReference
    observation_year: int
    source_code: Literal["world_bank"]
    items: list[ASEANComparisonItem]


class ForecastMetrics(APIModel):
    mae: float = Field(ge=0)
    rmse: float = Field(ge=0)
    mape_percent: float = Field(ge=0)


class ForecastPoint(APIModel):
    forecast_date: date
    point_forecast: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(APIModel):
    forecast_run_id: int = Field(ge=1)
    indicator: IndicatorReference
    region: RegionReference
    source_code: str
    generated_at: datetime
    data_start: date
    data_end: date
    test_start: date
    test_end: date
    selected_model_name: str
    selected_model_family: Literal["arima", "sarima"]
    baseline_model_name: str
    selected_metrics: ForecastMetrics
    baseline_metrics: ForecastMetrics
    mae_improvement_percent: float | None
    interval_coverage_percent: float | None
    forecast_horizon: int = Field(ge=1)
    confidence_level: float = Field(gt=0, lt=1)
    quality_status: QualityStatus
    quality_reasons: list[str]
    quality_thresholds: dict[str, float]
    anomaly_count: int = Field(ge=0)
    is_estimate_not_fact: Literal[True]
    items: list[ForecastPoint]


class DataQualityCheck(APIModel):
    name: str
    blocking: bool
    status: Literal["passed", "failed", "info"]
    finding_count: int = Field(ge=0)


class DataQualityResponse(APIModel):
    status: Literal["healthy", "degraded"]
    blocking_failures: int = Field(ge=0)
    informational_findings: int = Field(ge=0)
    checks: list[DataQualityCheck]


class PipelineRunItem(APIModel):
    run_id: int = Field(ge=1)
    source_code: str
    started_at: datetime
    completed_at: datetime | None
    status: PipelineStatus
    rows_loaded: int = Field(ge=0)
    has_error: bool


class PipelineRunListResponse(APIModel):
    items: list[PipelineRunItem]
    pagination: PaginationMetadata
