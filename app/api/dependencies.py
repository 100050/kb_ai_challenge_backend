from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.clients.legal_dong import LegalDongClient
from app.clients.r_one import ROneClient
from app.clients.real_estate import RentTransactionClient
from app.core.config import settings
from app.repositories.analysis import AnalysisRepository
from app.repositories.evaluation import EvaluationRepository
from app.repositories.housing_plan import HousingPlanRepository
from app.services.analysis import AnalysisService
from app.services.evaluation import EvaluationService
from app.services.market_price import MarketPriceService


def get_analysis_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisService:
    return AnalysisService(
        AnalysisRepository(session),
        HousingPlanRepository(session),
        EvaluationRepository(session),
        max_housing_plans=settings.max_housing_plans,
    )


def get_evaluation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EvaluationService:
    data_go_key = (
        settings.data_go_kr_api_key.get_secret_value()
        if settings.data_go_kr_api_key is not None
        else ""
    )
    r_one_key = (
        settings.r_one_api_key.get_secret_value()
        if settings.r_one_api_key is not None
        else ""
    )
    market_price_service = MarketPriceService(
        LegalDongClient(
            data_go_key,
            timeout_seconds=settings.real_estate_api_timeout_seconds,
        ),
        RentTransactionClient(
            data_go_key,
            timeout_seconds=settings.real_estate_api_timeout_seconds,
        ),
        ROneClient(
            r_one_key,
            timeout_seconds=settings.real_estate_api_timeout_seconds,
        ),
        lookback_months=settings.real_estate_lookback_months,
        area_tolerance_percent=(
            settings.comparable_area_tolerance_percent
        ),
    )
    return EvaluationService(
        AnalysisRepository(session),
        HousingPlanRepository(session),
        EvaluationRepository(session),
        market_price_service,
    )
