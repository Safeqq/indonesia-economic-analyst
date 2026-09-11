from __future__ import annotations

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

CODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$"
REGION_CODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,49}$"
SOURCE_CODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$"
MIN_OBSERVATION_YEAR = 1900
MAX_OBSERVATION_YEAR = date.today().year


class QueryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaginatedQuery(QueryModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class IndicatorListParameters(PaginatedQuery):
    frequency: Literal["daily", "monthly", "quarterly", "annual"] | None = None
    source_code: str | None = Field(default=None, pattern=SOURCE_CODE_PATTERN)


class SeriesParameters(PaginatedQuery):
    region_code: str = Field(default="IDN", pattern=REGION_CODE_PATTERN)
    start_year: int | None = Field(
        default=None, ge=MIN_OBSERVATION_YEAR, le=MAX_OBSERVATION_YEAR
    )
    end_year: int | None = Field(
        default=None, ge=MIN_OBSERVATION_YEAR, le=MAX_OBSERVATION_YEAR
    )

    @model_validator(mode="after")
    def validate_year_range(self) -> Self:
        if (
            self.start_year is not None
            and self.end_year is not None
            and self.start_year > self.end_year
        ):
            raise ValueError("start_year tidak boleh melebihi end_year")
        return self


class RegionListParameters(PaginatedQuery):
    region_level: Literal["country", "province", "city"] | None = None


class RegionOverviewParameters(PaginatedQuery):
    year: int | None = Field(
        default=None, ge=MIN_OBSERVATION_YEAR, le=MAX_OBSERVATION_YEAR
    )


class ASEANComparisonParameters(QueryModel):
    indicator_code: str = Field(pattern=CODE_PATTERN)
    year: int | None = Field(
        default=None, ge=MIN_OBSERVATION_YEAR, le=MAX_OBSERVATION_YEAR
    )


class ForecastParameters(QueryModel):
    region_code: str = Field(default="IDN", pattern=REGION_CODE_PATTERN)


class PipelineRunParameters(PaginatedQuery):
    source_code: str | None = Field(default=None, pattern=SOURCE_CODE_PATTERN)
    status: Literal["running", "success", "failed"] | None = None
