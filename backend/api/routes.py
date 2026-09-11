from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.api.dependencies import get_economic_service
from backend.models.parameters import (
    CODE_PATTERN,
    REGION_CODE_PATTERN,
    ASEANComparisonParameters,
    ForecastParameters,
    IndicatorListParameters,
    PipelineRunParameters,
    RegionListParameters,
    RegionOverviewParameters,
    SeriesParameters,
)
from backend.models.schemas import (
    ASEANComparisonResponse,
    DataQualityResponse,
    ErrorResponse,
    ForecastResponse,
    HealthResponse,
    IndicatorListResponse,
    IndicatorSeriesResponse,
    OverviewResponse,
    PipelineRunListResponse,
    RegionListResponse,
    RegionOverviewResponse,
)
from backend.services.economic import EconomicService

router = APIRouter()
ServiceDependency = Annotated[EconomicService, Depends(get_economic_service)]
IndicatorCodePath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=100,
        pattern=CODE_PATTERN,
        description="Kode indikator resmi",
    ),
]
RegionCodePath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=50,
        pattern=REGION_CODE_PATTERN,
        description="Kode negara atau wilayah resmi",
    ),
]
ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Resource tidak ditemukan"},
    500: {"model": ErrorResponse, "description": "Integritas data tidak valid"},
    503: {"model": ErrorResponse, "description": "Database tidak tersedia"},
}


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    responses={503: ERROR_RESPONSES[503]},
)
def health(service: ServiceDependency) -> HealthResponse:
    return service.health()


api_router = APIRouter(prefix="/api/v1")


@api_router.get(
    "/overview",
    response_model=OverviewResponse,
    tags=["economy"],
    responses=ERROR_RESPONSES,
)
def overview(service: ServiceDependency) -> OverviewResponse:
    return service.overview()


@api_router.get(
    "/indicators",
    response_model=IndicatorListResponse,
    tags=["indicators"],
    responses={503: ERROR_RESPONSES[503]},
)
def indicators(
    parameters: Annotated[IndicatorListParameters, Query()],
    service: ServiceDependency,
) -> IndicatorListResponse:
    return service.indicators(
        frequency=parameters.frequency,
        source_code=parameters.source_code,
        page=parameters.page,
        page_size=parameters.page_size,
    )


@api_router.get(
    "/indicators/{code}/series",
    response_model=IndicatorSeriesResponse,
    tags=["indicators"],
    responses=ERROR_RESPONSES,
)
def indicator_series(
    code: IndicatorCodePath,
    parameters: Annotated[SeriesParameters, Query()],
    service: ServiceDependency,
) -> IndicatorSeriesResponse:
    return service.indicator_series(
        indicator_code=code,
        region_code=parameters.region_code,
        start_year=parameters.start_year,
        end_year=parameters.end_year,
        page=parameters.page,
        page_size=parameters.page_size,
    )


@api_router.get(
    "/regions",
    response_model=RegionListResponse,
    tags=["regions"],
    responses={503: ERROR_RESPONSES[503]},
)
def regions(
    parameters: Annotated[RegionListParameters, Query()],
    service: ServiceDependency,
) -> RegionListResponse:
    return service.regions(
        region_level=parameters.region_level,
        page=parameters.page,
        page_size=parameters.page_size,
    )


@api_router.get(
    "/regions/{code}/overview",
    response_model=RegionOverviewResponse,
    tags=["regions"],
    responses=ERROR_RESPONSES,
)
def region_overview(
    code: RegionCodePath,
    parameters: Annotated[RegionOverviewParameters, Query()],
    service: ServiceDependency,
) -> RegionOverviewResponse:
    return service.region_overview(
        region_code=code,
        year=parameters.year,
        page=parameters.page,
        page_size=parameters.page_size,
    )


@api_router.get(
    "/asean/comparison",
    response_model=ASEANComparisonResponse,
    tags=["economy"],
    responses=ERROR_RESPONSES,
)
def asean_comparison(
    parameters: Annotated[ASEANComparisonParameters, Query()],
    service: ServiceDependency,
) -> ASEANComparisonResponse:
    return service.asean_comparison(
        indicator_code=parameters.indicator_code,
        year=parameters.year,
    )


@api_router.get(
    "/forecasts/{indicator_code}",
    response_model=ForecastResponse,
    tags=["analytics"],
    responses=ERROR_RESPONSES,
)
def forecast(
    indicator_code: IndicatorCodePath,
    parameters: Annotated[ForecastParameters, Query()],
    service: ServiceDependency,
) -> ForecastResponse:
    return service.forecast(
        indicator_code=indicator_code,
        region_code=parameters.region_code,
    )


@api_router.get(
    "/data-quality",
    response_model=DataQualityResponse,
    tags=["operations"],
    responses={503: ERROR_RESPONSES[503]},
)
def data_quality(service: ServiceDependency) -> DataQualityResponse:
    return service.data_quality()


@api_router.get(
    "/pipeline-runs",
    response_model=PipelineRunListResponse,
    tags=["operations"],
    responses={503: ERROR_RESPONSES[503]},
)
def pipeline_runs(
    parameters: Annotated[PipelineRunParameters, Query()],
    service: ServiceDependency,
) -> PipelineRunListResponse:
    return service.pipeline_runs(
        source_code=parameters.source_code,
        status=parameters.status,
        page=parameters.page,
        page_size=parameters.page_size,
    )


router.include_router(api_router)
