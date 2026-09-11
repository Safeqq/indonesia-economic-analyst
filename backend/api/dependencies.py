from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.engine import Engine

from backend.repositories.economic import EconomicRepository
from backend.services.economic import EconomicService


def get_api_engine(request: Request) -> Engine:
    return request.app.state.engine


def get_economic_repository(
    engine: Annotated[Engine, Depends(get_api_engine)],
) -> EconomicRepository:
    return EconomicRepository(engine)


def get_economic_service(
    repository: Annotated[EconomicRepository, Depends(get_economic_repository)],
) -> EconomicService:
    return EconomicService(repository)
