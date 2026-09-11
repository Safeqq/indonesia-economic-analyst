from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

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
from pipelines.utils.database import get_engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 untuk integration test MariaDB",
    ),
]

GDP_CODE = "NY.GDP.MKTP.KD.ZG"
JISDOR_CODE = "BI.JISDOR.USD_IDR.MONTHLY_AVG"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_every_api_endpoint_reads_real_database() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    engine = get_engine()
    application = create_app(engine=engine)
    endpoints = {
        "/health": HealthResponse,
        "/api/v1/overview": OverviewResponse,
        "/api/v1/indicators?source_code=world_bank&page_size=100": (
            IndicatorListResponse
        ),
        (
            f"/api/v1/indicators/{GDP_CODE}/series"
            "?region_code=IDN&start_year=2024&end_year=2025"
        ): IndicatorSeriesResponse,
        "/api/v1/regions?page_size=100": RegionListResponse,
        "/api/v1/regions/IDN/overview": RegionOverviewResponse,
        f"/api/v1/asean/comparison?indicator_code={GDP_CODE}&year=2025": (
            ASEANComparisonResponse
        ),
        f"/api/v1/forecasts/{JISDOR_CODE}": ForecastResponse,
        "/api/v1/data-quality": DataQualityResponse,
        "/api/v1/pipeline-runs?page_size=100": PipelineRunListResponse,
    }

    transport = ASGITransport(app=application)
    try:
        async with application.router.lifespan_context(application):
            async with AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                payloads: dict[str, dict[str, object]] = {}
                for path, schema in endpoints.items():
                    response = await client.get(path)
                    assert response.status_code == 200, response.text
                    payloads[path] = response.json()
                    schema.model_validate(response.json())
    finally:
        engine.dispose()

    indicator_payload = payloads[
        "/api/v1/indicators?source_code=world_bank&page_size=100"
    ]
    assert indicator_payload["pagination"]["total_items"] >= 5
    series_path = (
        f"/api/v1/indicators/{GDP_CODE}/series"
        "?region_code=IDN&start_year=2024&end_year=2025"
    )
    assert len(payloads[series_path]["items"]) == 2
    forecast_payload = payloads[f"/api/v1/forecasts/{JISDOR_CODE}"]
    assert forecast_payload["quality_status"] == "passed"
    assert forecast_payload["is_estimate_not_fact"] is True
    assert len(forecast_payload["items"]) == forecast_payload["forecast_horizon"]
    assert payloads["/api/v1/data-quality"]["status"] == "healthy"
