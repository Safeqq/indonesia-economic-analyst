from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from backend.api.dependencies import get_economic_service
from backend.main import create_app
from backend.models.schemas import (
    ASEANComparisonResponse,
    DataQualityResponse,
    ForecastResponse,
    HealthResponse,
    IndicatorListResponse,
    IndicatorSeriesResponse,
    OverviewResponse,
    PipelineRunListResponse,
    RegionListResponse,
    RegionOverviewResponse,
)
from backend.repositories.economic import EconomicRepository, RepositoryPage
from backend.services.economic import EconomicService
from pipelines.utils.data_quality import QualityResult

GDP_CODE = "NY.GDP.MKTP.KD.ZG"
JISDOR_CODE = "BI.JISDOR.USD_IDR.MONTHLY_AVG"
NOW = datetime(2026, 9, 10, 12, 0)


@pytest.fixture
def repository() -> Mock:
    result = Mock(spec=EconomicRepository)
    region = {
        "region_code": "IDN",
        "region_name": "Indonesia",
        "region_level": "country",
        "parent_region_code": None,
    }
    indicators = {
        GDP_CODE: {
            "indicator_code": GDP_CODE,
            "indicator_name": "GDP growth",
            "unit": "percent",
            "frequency": "annual",
        },
        JISDOR_CODE: {
            "indicator_code": JISDOR_CODE,
            "indicator_name": "JISDOR bulanan",
            "unit": "IDR per USD",
            "frequency": "monthly",
        },
    }
    result.health_check.return_value = None
    result.get_region.side_effect = lambda code: region if code == "IDN" else None
    result.get_indicator.side_effect = lambda code: indicators.get(code)
    result.get_latest_overview.return_value = (
        {
            "observation_date": date(2025, 1, 1),
            "observation_year": 2025,
            "gdp_growth_percent": 5.11,
            "inflation_percent": 1.91,
            "unemployment_percent": 3.24,
            "population": 285_000_000,
            "gdp_per_capita_current_usd": 5_000,
            "indicator_coverage": 5,
            "last_ingested_at": NOW,
        },
        {
            "observation_date": date(2026, 8, 1),
            "observation_year": 2026,
            "observation_quarter": 3,
            "observation_month": 8,
            "bi_rate_percent": 4.75,
            "bi_rate_change_pp": 0,
            "jisdor_idr_per_usd": 17_832.89,
            "jisdor_mom_change": -181.58,
            "jisdor_mom_percent_change": -1.01,
            "jisdor_rolling_3_month_average": 17_923.82,
            "indicator_coverage": 2,
            "ingested_at": NOW,
        },
    )
    result.list_indicators.return_value = RepositoryPage(
        items=(
            {
                **indicators[GDP_CODE],
                "source_codes_csv": "world_bank",
                "observation_count": 26,
                "region_count": 11,
                "period_start": date(2000, 1, 1),
                "period_end": date(2025, 1, 1),
            },
        ),
        total_items=1,
    )
    result.list_indicator_series.return_value = RepositoryPage(
        items=(
            {
                "observation_date": date(2025, 1, 1),
                "value": 5.11,
                "source_code": "world_bank",
                "ingested_at": NOW,
            },
        ),
        total_items=1,
    )
    result.list_regions.return_value = RepositoryPage(
        items=(
            {
                **region,
                "indicator_count": 7,
                "observation_count": 372,
                "period_start": date(2000, 1, 1),
                "period_end": date(2026, 8, 1),
            },
        ),
        total_items=1,
    )
    result.list_region_overview.return_value = RepositoryPage(
        items=(
            {
                **indicators[GDP_CODE],
                "source_code": "world_bank",
                "observation_date": date(2025, 1, 1),
                "value": 5.11,
                "ingested_at": NOW,
            },
        ),
        total_items=1,
    )
    result.get_latest_asean_year.return_value = 2025
    result.list_asean_comparison.return_value = (
        {
            "region_code": "IDN",
            "region_name": "Indonesia",
            "member_since": date(1967, 8, 8),
            "was_member_during_period": True,
            "observation_date": date(2025, 1, 1),
            "value": 5.11,
            "asean_average": 4.6,
            "difference_from_asean_average": 0.51,
            "country_coverage": 11,
            "value_rank_desc": 5,
            "value_percentile": 0.6,
        },
    )
    result.get_latest_forecast.return_value = (
        {
            "forecast_run_id": 1,
            "generated_at": NOW,
            "data_start": date(2016, 8, 1),
            "data_end": date(2026, 8, 1),
            "test_start": date(2024, 9, 1),
            "test_end": date(2026, 8, 1),
            "selected_model_name": "arima_011_drift",
            "selected_model_family": "arima",
            "baseline_model_name": "naive_lag_1",
            "selected_mae": 156.14,
            "selected_rmse": 200.81,
            "selected_mape_percent": 0.94,
            "baseline_mae": 183.49,
            "baseline_rmse": 226.08,
            "baseline_mape_percent": 1.11,
            "mae_improvement_percent": 14.91,
            "interval_coverage_percent": 95.83,
            "forecast_horizon": 1,
            "confidence_level": 0.95,
            "quality_status": "passed",
            "quality_reasons_json": json.dumps(
                {
                    "reasons": [],
                    "thresholds": {
                        "minimum_mae_improvement_percent": 5,
                        "maximum_mape_percent": 5,
                        "minimum_interval_coverage_percent": 70,
                    },
                }
            ),
            "source_code": "bank_indonesia",
            "anomaly_count": 8,
        },
        (
            {
                "forecast_date": date(2026, 9, 1),
                "point_forecast": 17_803.34,
                "lower_bound": 17_297.87,
                "upper_bound": 18_308.82,
            },
        ),
    )
    result.get_data_quality.return_value = (
        QualityResult(name="check_duplicates", blocking=True, rows=()),
        QualityResult(
            name="check_data_freshness",
            blocking=False,
            rows=({"source_code": "world_bank"},),
        ),
    )
    result.list_pipeline_runs.return_value = RepositoryPage(
        items=(
            {
                "run_id": 1,
                "source_code": "world_bank",
                "started_at": NOW,
                "completed_at": NOW,
                "status": "success",
                "rows_loaded": 100,
                "error_message": None,
            },
        ),
        total_items=1,
    )
    return result


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(repository: Mock):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    application = create_app(engine=engine)
    application.dependency_overrides[get_economic_service] = lambda: EconomicService(
        repository
    )
    transport = ASGITransport(app=application, raise_app_exceptions=False)
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as test_client:
            yield test_client
    engine.dispose()


@pytest.mark.anyio
async def test_all_target_endpoints_return_documented_schema(
    client: AsyncClient,
) -> None:
    endpoints = {
        "/health": HealthResponse,
        "/api/v1/overview": OverviewResponse,
        "/api/v1/indicators": IndicatorListResponse,
        f"/api/v1/indicators/{GDP_CODE}/series": IndicatorSeriesResponse,
        "/api/v1/regions": RegionListResponse,
        "/api/v1/regions/IDN/overview": RegionOverviewResponse,
        f"/api/v1/asean/comparison?indicator_code={GDP_CODE}": (
            ASEANComparisonResponse
        ),
        f"/api/v1/forecasts/{JISDOR_CODE}": ForecastResponse,
        "/api/v1/data-quality": DataQualityResponse,
        "/api/v1/pipeline-runs": PipelineRunListResponse,
    }

    for path, schema in endpoints.items():
        response = await client.get(path)
        assert response.status_code == 200, response.text
        schema.model_validate(response.json())


@pytest.mark.anyio
async def test_paginated_empty_result_returns_empty_list(
    client: AsyncClient, repository: Mock
) -> None:
    repository.list_indicators.return_value = RepositoryPage(items=(), total_items=0)

    response = await client.get("/api/v1/indicators?page=2&page_size=5")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["pagination"] == {
        "page": 2,
        "page_size": 5,
        "total_items": 0,
        "total_pages": 0,
    }
    repository.list_indicators.assert_called_with(
        frequency=None,
        source_code=None,
        limit=5,
        offset=5,
    )


@pytest.mark.anyio
async def test_known_series_with_empty_year_filter_returns_200(
    client: AsyncClient, repository: Mock
) -> None:
    repository.list_indicator_series.return_value = RepositoryPage(
        items=(), total_items=0
    )

    response = await client.get(
        f"/api/v1/indicators/{GDP_CODE}/series?start_year=2020&end_year=2020"
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_unknown_indicator_returns_404(
    client: AsyncClient, repository: Mock
) -> None:
    repository.get_indicator.side_effect = None
    repository.get_indicator.return_value = None

    response = await client.get("/api/v1/indicators/UNKNOWN/series")

    assert response.status_code == 404
    assert response.json() == {"detail": "Indikator 'UNKNOWN' tidak ditemukan"}


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/indicators/{GDP_CODE}/series?start_year=2025&end_year=2024",
        f"/api/v1/indicators/{GDP_CODE}/series?start_year=1899",
        "/api/v1/indicators?page=0",
        "/api/v1/regions?page_size=101",
        f"/api/v1/forecasts/{JISDOR_CODE}?region_code=IDN!",
        "/api/v1/asean/comparison",
        "/api/v1/indicators/bad%20code/series",
    ],
)
@pytest.mark.anyio
async def test_invalid_input_returns_422(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_failed_quality_gate_never_exposes_forecast(
    client: AsyncClient, repository: Mock
) -> None:
    run, forecasts = repository.get_latest_forecast.return_value
    failed_run = dict(run)
    failed_run["quality_status"] = "failed"
    failed_run["quality_reasons_json"] = json.dumps(
        {"reasons": ["MAE tidak membaik"], "thresholds": {}}
    )
    repository.get_latest_forecast.return_value = failed_run, forecasts

    response = await client.get(f"/api/v1/forecasts/{JISDOR_CODE}")

    assert response.status_code == 200
    assert response.json()["quality_status"] == "failed"
    assert response.json()["quality_reasons"] == ["MAE tidak membaik"]
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_database_error_returns_sanitized_503(
    client: AsyncClient, repository: Mock
) -> None:
    repository.health_check.side_effect = OperationalError(
        "SELECT sensitive_value", {}, Exception("database password secret")
    )

    response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Layanan data sementara tidak tersedia"}
    assert "password" not in response.text


@pytest.mark.anyio
async def test_openapi_contains_every_target_endpoint(client: AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]

    assert set(paths) >= {
        "/health",
        "/api/v1/overview",
        "/api/v1/indicators",
        "/api/v1/indicators/{code}/series",
        "/api/v1/regions",
        "/api/v1/regions/{code}/overview",
        "/api/v1/asean/comparison",
        "/api/v1/forecasts/{indicator_code}",
        "/api/v1/data-quality",
        "/api/v1/pipeline-runs",
    }
